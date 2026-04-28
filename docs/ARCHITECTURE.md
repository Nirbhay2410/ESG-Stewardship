# Architecture Deep Dive

## System Design Principles

The platform is built around three core principles:

1. **Data-first, AI-second** — every metric is calculated from real MongoDB data. The LLM is called only when natural language narrative adds value (recommendations, summaries, strategy text). It never invents numbers.
2. **Agent specialization** — each agent owns a single domain. The orchestrator routes but does not compute.
3. **Typed responses** — every backend response carries a `type` field. The frontend renders the appropriate component based on type, keeping presentation logic out of the backend.

---

## Backend Layer Breakdown

### Entry Point (`main.py`)

FastAPI application with four route groups. Environment is loaded via `config.load_env()` before any service imports to ensure `OPENROUTER_API_KEY` is available when `OpenRouterService` initializes.

```
startup → init_db() → create MongoDB indexes
```

CORS is configured to allow `localhost:3000` and `localhost:5173` (Vite dev server).

### Configuration (`config.py`)

Single source of truth for environment loading. Uses `python-dotenv` to load `backend/.env`. Normalizes API keys (strips quotes, BOM, whitespace) to handle common copy-paste issues.

### Database (`database.py`)

Motor async client. Indexes created at startup:

- `facilities.location` — 2dsphere index for geospatial queries
- `conversations.session_id` — lookup by session
- `utility_bills`, `meter_data`, `discharge_reports` — indexed by `user_id`
- `wri_baseline_annual` — indexed by `aqid`, `name_0`, `name_1`
- `wri_future_projections` — indexed by `BasinID`

---

## Agent Architecture

### BaseAgent

```python
class BaseAgent:
    _tools: Dict[str, Tool]

    def _register(name, fn, description)
    async def run_tool(tool_name, **kwargs)
```

Tools are registered in `register_tools()` which is called from `__init__`. Each tool is an async function. `run_tool` dispatches by name and handles both sync and async callables.

### OrchestratorAgent

The orchestrator is the only agent that the route layer calls directly. It holds references to all other agents and the AI service.

**Intent detection** uses a priority-ordered list of `(regex_pattern, (agent, tool))` tuples. The first match wins. Patterns are tested against the lowercased user message.

```python
INTENT_MAP = [
    (r"dashboard|overview|summary", ("report", "get_dashboard_report")),
    (r"risk|water stress|aqueduct",  ("risk",   "assess_all_facilities")),
    (r"compliance|permit|npdes",     ("compliance", "get_compliance_summary")),
    ...
]
```

For messages that don't match any pattern, the orchestrator falls back to `OpenRouterService.process_chat_message()` for a general conversational response.

**Special flows** handled directly in the orchestrator (not delegated to agents):
- Upload type selection
- Supplier risk assessment (requires cross-agent data + AI recommendations)
- Mitigation plan generation (requires risk data + AI narrative)
- DMR report generation (requires discharge + billing data)
- Stewardship strategy building (requires all data sources + AI)

### RiskAgent — WRI Scoring

The risk scoring pipeline:

```
1. Load facility coordinates from MongoDB
2. query_wri_near(lat, lon) → find nearest WRI record
   a. Try MongoDB $near geospatial query (requires 2dsphere index)
   b. Fallback: load 5,000 records, sort by haversine distance
   c. Fallback: match by country/state name from bounding box lookup
   d. Last resort: return any record
3. Map WRI category fields to 1–5 scores
4. Weighted average → overall_risk_score
5. (Optional) Call AI with real scores for narrative recommendations
```

WRI category → score mapping:

| Category value | Score |
|---|---|
| -1 (Arid & Low Use) | 1.0 |
| 0 (Low) | 1.0 |
| 1 (Low-Medium) | 2.0 |
| 2 (Medium-High) | 3.0 |
| 3 (High) | 4.0 |
| 4 (Extremely High) | 5.0 |

### EfficiencyAgent — Opportunity Calculation

Opportunities are calculated as percentages of actual total volume from utility bills and meter data:

| Opportunity | Savings % | Trigger |
|---|---|---|
| Leak Detection | 5% | Meter anomaly detected |
| Low-Flow Fixtures | 12% | Always |
| Cooling Tower Optimization | 15% | Volume > 500,000 gal |
| Process Water Recycling | 20% | Always |

Payback period = `implementation_cost / (annual_savings_usd / 12)` months.

Anomaly detection: a meter is flagged if its consumption exceeds 2× the fleet average. Severity is `high` if >3× average.

---

## AI Integration

### OpenRouterService

Drop-in replacement for any OpenAI-compatible service. Uses the OpenAI Python SDK pointed at `https://openrouter.ai/api/v1`.

- Primary model: `nvidia/nemotron-3-super-120b-a12b:free`
- Fallback model: `meta-llama/llama-3.3-70b-instruct:free`
- Rate limit handling: 10-second backoff on 429 responses
- Model unavailability: automatic fallback to secondary model

All AI calls follow the same pattern:
1. Build a structured prompt with real data embedded as JSON
2. Instruct the model to return only valid JSON
3. Strip markdown code fences from response
4. Parse JSON; fall back to hardcoded defaults on parse failure

This ensures the UI never breaks due to AI unavailability.

---

## Frontend Architecture

`ChatInterface.jsx` is a single-component application (~3,200 lines). It maintains:

- `messages` — array of message objects, each with `role`, `content`, typed data fields, and `options`
- `currentUploadType` — tracks which upload flow is active

On each assistant message, the component inspects the `type` field and renders the appropriate inline component. All chart data, tables, and cards are rendered directly in the message thread rather than in a separate panel.

**Download generation** is entirely client-side. When a user clicks a download button, the component finds the relevant data in the message history, generates a self-contained HTML document with inline CSS, and triggers a browser download via `URL.createObjectURL`.

---

## Data Flow: File Upload

```
User selects file
    → POST /api/upload/ (multipart)
    → process_uploaded_file() dispatches by file_type
    → pandas reads CSV / pdfplumber reads PDF
    → data normalized and upserted to MongoDB
    → extracted_data returned to frontend
    → frontend renders confirmation with key metrics
```

All uploads use `upsert=True` with a natural key (e.g., `bill_id`, `meter_id`, `facility_id`) to prevent duplicates on re-upload.

---

## Data Flow: Risk Assessment

```
User: "Water Risk Assessment"
    → OrchestratorAgent detects "risk" intent
    → RiskAgent.assess_all_facilities(user_id)
        → DataAgent.get_facilities()
        → for each facility:
            → RiskAgent.query_wri_near(lat, lon)
            → RiskAgent.score_facility()
        → aggregate portfolio score
        → (if AI available) generate recommendations narrative
    → return typed response {type: "risk_assessment", data: {...}}
    → frontend renders risk table + score breakdown
```

---

## Security Considerations

- API keys are loaded from `backend/.env` and never exposed to the frontend
- File uploads are stored in `backend/uploads/` with UUID filenames (original names preserved in DB only)
- All MongoDB queries are scoped by `user_id` — currently defaults to `"demo"` for single-user mode
- CORS is restricted to localhost origins in development
- No authentication layer is implemented in the current version — add JWT middleware before production deployment
