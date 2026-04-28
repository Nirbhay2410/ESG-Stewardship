# Water Stewardship AI Platform

An enterprise-grade, AI-powered water stewardship platform that enables organizations to track water usage, assess basin-level risk using WRI Aqueduct data, identify efficiency opportunities, monitor regulatory compliance, and build data-driven stewardship strategies — all through a conversational chat interface.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Agent System](#agent-system)
- [Data Ingestion](#data-ingestion)
- [Frontend](#frontend)
- [Data Models](#data-models)
- [Contributing](#contributing)

---

## Overview

The platform is built around a multi-agent backend that routes user intent to specialized agents. Each agent queries real data from MongoDB and optionally enriches responses with AI-generated narrative via OpenRouter (LLM gateway). The frontend is a React chat interface that renders structured responses — dashboards, risk maps, compliance tables, DMR reports, and stewardship strategy documents — inline in the conversation.

**Core capabilities:**

| Capability | Description |
|---|---|
| Data Ingestion | Upload utility bills, meter logs, facility info, supplier lists, discharge reports (CSV/PDF) |
| Water Risk Assessment | Basin-level risk scoring using WRI Aqueduct 3.0 baseline and future projection data |
| Efficiency Analysis | ROI-ranked water-saving opportunities derived from real usage data |
| Compliance Tracking | Permit registry, violation detection, expiry alerts, DMR report generation |
| Water Footprint | Blue/grey water calculation, supply chain footprint, industry benchmarking |
| Stewardship Strategy | AI-generated reduction targets, KPI roadmaps, initiative portfolios |
| Supply Chain Risk | Supplier water intensity scoring and engagement plan generation |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        React Frontend                        │
│   ChatInterface → renders structured message types inline    │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP (REST + WebSocket)
┌────────────────────────────▼────────────────────────────────┐
│                     FastAPI Backend                          │
│                                                              │
│  Routes: /api/chat  /api/upload  /api/analysis  /api/wri    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               OrchestratorAgent                      │   │
│  │  Intent detection → routes to specialized agents     │   │
│  │                                                      │   │
│  │  DataAgent   RiskAgent   ComplianceAgent             │   │
│  │  EfficiencyAgent   ReportAgent                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  OpenRouterService (LLM)    OCRService (file extraction)     │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                        MongoDB                               │
│                                                              │
│  Collections: utility_bills, meter_data, facilities,        │
│  discharge_reports, suppliers, conversations,               │
│  wri_baseline_annual, wri_future_projections                │
└─────────────────────────────────────────────────────────────┘
```

### Request Flow

1. User sends a message via `POST /api/chat/message`
2. `OrchestratorAgent.handle()` runs regex-based intent detection
3. The matched agent fetches real data from MongoDB via `DataAgent`
4. If narrative is needed, the agent calls `OpenRouterService.generate_content()` with structured data as context
5. A typed response object is returned to the frontend
6. The frontend renders the appropriate component (dashboard cards, risk table, map markers, etc.)

---

## Tech Stack

**Backend**
- Python 3.11+
- FastAPI + Uvicorn
- Motor (async MongoDB driver)
- OpenAI SDK (pointed at OpenRouter)
- pandas, pdfplumber, pytesseract (file processing)
- geopy (distance calculations)

**Frontend**
- React 18
- Recharts (charts)
-  CSS
- react-dropzone, react-hot-toast

**Database**
- MongoDB 6+ (local or Atlas)

**AI**
- OpenRouter gateway — default model: `nvidia/nemotron-3-super-120b-a12b:free`
- Fallback model: `meta-llama/llama-3.3-70b-instruct:free`

**Data**
- WRI Aqueduct 3.0 (baseline annual + future projections CSV)

---

## Project Structure

```
.
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Env loading, API key helpers
│   ├── database.py              # Motor client, collection models, indexes
│   ├── requirements.txt
│   ├── .env                     # Local secrets (not committed)
│   ├── agents/
│   │   ├── base_agent.py        # Tool registration, run_tool dispatcher
│   │   ├── orchestrator.py      # Intent routing, response assembly
│   │   ├── data_agent.py        # All MongoDB read queries
│   │   ├── risk_agent.py        # WRI scoring, climate scenarios
│   │   ├── compliance_agent.py  # Permit tracking, violation detection
│   │   ├── efficiency_agent.py  # Savings opportunities, anomaly detection
│   │   └── report_agent.py      # Dashboard, footprint, trends, DMR
│   ├── routes/
│   │   ├── chat.py              # /api/chat — message handling, WebSocket
│   │   ├── upload.py            # /api/upload — file ingestion to MongoDB
│   │   ├── analysis.py          # /api/analysis — dashboard, trends, compliance
│   │   └── wri.py               # /api/wri — WRI data queries
│   └── services/
│       ├── openrouter_service.py  # LLM client (OpenRouter / OpenAI-compatible)
│       └── ocr_service.py         # Text extraction (PDF, image, CSV)
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── ChatInterface.jsx  # Main chat UI, all response renderers
│   │   │   ├── Dashboard.jsx
│   │   │   ├── RiskMap.jsx
│   │   │   ├── MessageBubble.jsx
│   │   │   └── UploadWidget.jsx
│   │   └── index.js
│   └── package.json
├── scripts/
│   └── ingest_wri.py            # One-time WRI CSV → MongoDB loader
├── test_data/
│   ├── utility_bills.csv
│   ├── meter_log.csv
│   ├── facility_info.csv
│   ├── supplier_list.csv
│   └── discharge_report.csv
└── Y2019M07D12_Aqueduct30_V01/  # WRI Aqueduct 3.0 source data
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB 6+ running locally (or a MongoDB Atlas URI)
- An [OpenRouter](https://openrouter.ai) API key (free tier available)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copy and edit the environment file:

```bash
cp .env           #  edit backend/.env directly
```

Start the API server:

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/api/docs`.

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

The app will open at `http://localhost:3000`.

### Load WRI Aqueduct Data

This is a one-time step. Download the WRI Aqueduct 3.0 CSV files and run:

```bash
python scripts/ingest_wri.py \
  --baseline path/to/baseline_annual.csv \
  --future   path/to/future_projections.csv \
  --drop
```

Options:

| Flag | Default | Description |
|---|---|---|
| `--mongo-uri` | `mongodb://localhost:27017` | MongoDB connection string |
| `--db` | `water_stewardship` | Database name |
| `--baseline-collection` | `wri_baseline_annual` | Target collection |
| `--future-collection` | `wri_future_projections` | Target collection |
| `--chunk-size` | `5000` | Rows per insert batch |
| `--drop` | false | Drop existing collections before loading |

### Load Test Data

Upload the sample CSVs through the chat interface or directly via the API:

```bash
curl -X POST http://localhost:8000/api/upload/ \
  -F "file=@test_data/utility_bills.csv" \
  -F "file_type=utility_bill" \
  -F "user_id=demo"
```

Repeat for `meter_log.csv` (`meter_data`), `facility_info.csv` (`facility_info`), `supplier_list.csv` (`supplier_list`), and `discharge_report.csv` (`discharge_report`).

---

## Environment Variables

All variables live in `backend/.env`.

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key — get one at openrouter.ai |
| `MONGO_URI` | Yes | MongoDB connection URI |
| `DATABASE_NAME` | No | Database name (default: `water_stewardship`) |
| `GEMINI_API_KEY` | No | Optional Gemini fallback (unused by default) |
| `API_HOST` | No | Bind host (default: `0.0.0.0`) |
| `API_PORT` | No | Bind port (default: `8000`) |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |

---

## API Reference

### Chat

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/chat/message` | Send a message, receive a typed agent response |
| `GET` | `/api/chat/history/{conversation_id}` | Retrieve conversation history |
| `POST` | `/api/chat/start` | Create a new conversation |
| `WS` | `/api/chat/ws/{session_id}` | WebSocket connection for real-time chat |

**POST /api/chat/message**

```json
{
  "session_id": "session_1234567890",
  "message": "Show me the water risk assessment",
  "user_id": "demo"
}
```

Response types include: `dashboard`, `risk_assessment`, `compliance`, `efficiency`, `water_footprint`, `dmr_report`, `stewardship_strategy`, `suppliers`, `risk_map`, `climate_scenarios`, `upload_options`, `upload_prompt`, `text`.

### Upload

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/upload/` | Upload and process a data file |
| `GET` | `/api/upload/{file_id}` | Get file metadata |
| `GET` | `/api/upload/user/{user_id}` | List all files for a user |
| `DELETE` | `/api/upload/{file_id}` | Delete a file |

**POST /api/upload/** (multipart/form-data)

| Field | Type | Values |
|---|---|---|
| `file` | File | CSV, XLSX, PDF, PNG, JPG |
| `file_type` | string | `utility_bill`, `meter_data`, `discharge_report`, `facility_info`, `supplier_list` |
| `user_id` | string | User identifier |

### Analysis

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/analysis/dashboard` | Dashboard summary cards |
| `GET` | `/api/analysis/trends` | Monthly usage trends |
| `GET` | `/api/analysis/water-balance` | Water flow breakdown |
| `GET` | `/api/analysis/efficiency-opportunities` | ROI-ranked savings opportunities |
| `GET` | `/api/analysis/compliance-status` | Permit and compliance overview |

### WRI Data

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/wri/baseline/search` | Find WRI records near lat/lon |
| `GET` | `/api/wri/baseline/{aqid}` | Get record by Aqueduct ID |
| `GET` | `/api/wri/baseline/country/{code}` | Get records by country code |
| `GET` | `/api/wri/future/{basin_id}` | Get future projections by basin |
| `GET` | `/api/wri/risk-assessment` | Full risk assessment for a coordinate |
| `GET` | `/api/wri/compare` | Compare risk across multiple locations |
| `GET` | `/api/wri/stats` | WRI dataset statistics |

---

## Agent System

All agents extend `BaseAgent`, which provides a tool registration and dispatch mechanism.

```python
class BaseAgent:
    def _register(name, fn, description)   # register a tool
    async def run_tool(tool_name, **kwargs) # dispatch to tool
    def list_tools() -> List[str]
```

### OrchestratorAgent

The central router. Receives every user message and uses regex pattern matching (`INTENT_MAP`) to decide which agent and tool to invoke. Falls back to `OpenRouterService` for free-text questions that require natural language answers.

Intent patterns are defined as `(regex, (agent_name, tool_name))` tuples. The orchestrator also handles multi-step flows (upload selection, DMR generation, strategy building) directly.

### DataAgent

Owns all MongoDB read operations. Other agents call `DataAgent` methods rather than querying the database directly.

| Tool | Description |
|---|---|
| `get_facilities` | All facilities for a user |
| `get_utility_bills` | Utility bill records |
| `get_meter_data` | Meter reading records |
| `get_discharge_reports` | Discharge/permit reports |
| `get_suppliers` | Supplier list with water intensity |
| `get_usage_summary` | Aggregated totals and facility breakdown |

### RiskAgent

Calculates water risk scores from WRI Aqueduct data. Uses haversine distance to find the nearest WRI record to each facility's coordinates. Scores five risk dimensions and computes a weighted overall score.

| Dimension | Weight |
|---|---|
| Baseline Water Stress | 35% |
| Water Depletion | 25% |
| Drought Risk | 20% |
| Riverine Flood | 10% |
| Coastal Flood | 10% |

Score scale: 1.0 (Very Low) → 5.0 (Extremely High). AI is called only to generate narrative recommendations after scores are calculated from real data.

### ComplianceAgent

Reads `discharge_reports` collection and tracks permit status, compliance rates, upcoming expirations, and parameter violations.

### EfficiencyAgent

Analyzes utility bill and meter data to generate ROI-ranked efficiency opportunities. Detects meter anomalies by comparing individual meter consumption against the fleet average (flags >2× average as anomalies).

### ReportAgent

Assembles structured reports from multiple data sources without calling the LLM. Handles dashboard, trends, water balance, pollutant levels, cost analysis, water footprint, industry benchmarking, reduction targets, and hotspot identification.

---

## Data Ingestion

### Supported File Formats

| Data Type | Formats | Key CSV Columns |
|---|---|---|
| Utility Bills | CSV, XLSX, PDF | `Bill_ID`, `Facility_ID`, `Facility_Name`, `Usage_Volume_(gal)`, `Total_Bill_($)`, `Water_Source`, `Billing_Period_Start` |
| Meter Data | CSV, XLSX | `Meter_ID`, `Facility_ID`, `Meter_Location`, `Meter_Type`, `Reading_Value`, `Flow_Rate_GPM`, `Timestamp`, `Status` |
| Facility Info | CSV, XLSX | `Facility_ID`, `Facility_Name`, `Latitude`, `Longitude`, `Industry_Type`, `Facility_Type`, `Annual_Revenue_USD`, `Number_of_Employees` |
| Supplier List | CSV, XLSX | `Supplier_ID`, `Supplier_Name`, `City`, `Country`, `Material_Category`, `Annual_Spend_USD`, `Water_Intensity_Factor_(est)` |
| Discharge Reports | CSV, XLSX, PDF | `Permit_ID`, `Permit_Type`, `Issuing_Authority`, `Parameter`, `Sample_Value`, `Limit_Value`, `Compliance_Status`, `Expiration_Date` |

PDF and image files are processed via `OCRService` (pdfplumber + pytesseract). CSV/XLSX files are parsed directly with pandas and stored to MongoDB with upsert semantics.

---

## Frontend

The entire UI lives in `ChatInterface.jsx`. It renders different response types as inline components within the chat thread:

| Response Type | Rendered As |
|---|---|
| `dashboard` | Summary cards + facility breakdown + insights |
| `risk_assessment` | Risk score table + breakdown by dimension |
| `risk_map` | Facility markers with color-coded risk levels |
| `compliance` | Permit registry + violation list + expiry alerts |
| `efficiency` | ROI-ranked opportunity cards |
| `water_footprint` | Blue/grey/supply chain breakdown |
| `dmr_report` | Permit-by-permit parameter table |
| `stewardship_strategy` | Priorities + KPIs + implementation timeline |
| `suppliers` | Risk-ranked supplier table + recommendations |
| `climate_scenarios` | 2030/2040 projections per facility |
| `upload_options` | File type selection buttons |
| `upload_prompt` | File drop zone |

Download buttons (DMR report, mitigation plan, stewardship strategy, footprint report) generate self-contained HTML files client-side and trigger a browser download.

---

## Data Models

### MongoDB Collections

**utility_bills**
```json
{
  "user_id": "demo",
  "bill_id": "BILL-001",
  "facility_id": "FAC-001",
  "facility_name": "Plant A",
  "water_volume_gallons": 150000,
  "total_cost": 4500.00,
  "water_source": "Municipal",
  "billing_period_start": "2026-01-01",
  "cost_per_1000_gal": 30.00
}
```

**meter_data**
```json
{
  "user_id": "demo",
  "meter_id": "M-001",
  "facility_id": "FAC-001",
  "location": "Main Supply",
  "meter_type": "Flow",
  "consumption": 45230,
  "avg_flow_rate_gpm": 12.5,
  "status": "normal"
}
```

**facilities**
```json
{
  "user_id": "demo",
  "facility_id": "FAC-001",
  "facility_name": "Plant A",
  "address": { "city": "San Francisco", "state": "CA", "country": "US" },
  "location": { "type": "Point", "coordinates": [-122.4194, 37.7749] },
  "facility_type": "Factory",
  "annual_revenue_usd": 10000000,
  "employees": 250
}
```

**discharge_reports**
```json
{
  "user_id": "demo",
  "permits": [{
    "permit_id": "NPDES-CA0001234",
    "permit_type": "NPDES",
    "issuing_authority": "State Water Board",
    "expiration_date": "2027-03-15",
    "parameters": [{
      "parameter": "BOD",
      "sample_value": "25",
      "limit_value": "30",
      "limit_unit": "mg/L",
      "compliance_status": "pass"
    }],
    "total_parameters": 5,
    "passed_parameters": 5,
    "compliance_rate": 100
  }]
}
```

**suppliers**
```json
{
  "user_id": "demo",
  "suppliers": [{
    "supplier_id": "SUP-001",
    "supplier_name": "Acme Ingredients",
    "location": { "city": "Punjab", "country": "India" },
    "material_category": "Agricultural",
    "annual_spend_usd": 500000,
    "water_intensity_factor": 350000
  }]
}
```

**wri_baseline_annual** (ingested from WRI Aqueduct CSV)

Key fields: `aqid`, `lat`, `lon`, `name_0` (country), `name_1` (state/province), `bws_cat` (baseline water stress), `bwd_cat` (depletion), `drr_cat` (drought), `rfr_cat` (riverine flood), `cfr_cat` (coastal flood).

**wri_future_projections** (ingested from WRI Aqueduct CSV)

Key fields: `BasinID`, `ws3024tl` (2030 BAU water stress label), `ws4024tl` (2040 BAU), scenario suffixes: `2` = optimistic (RCP2.6), `4` = BAU (RCP4.5), `u` = pessimistic (RCP8.5).

---

## DEMO VIDEO

https://drive.google.com/file/d/133T472RAeDSLaS2ynkQK-EUd0peEwNGy/view?usp=sharing

---
## Further Reading

- `docs/ARCHITECTURE.md` — detailed system architecture, multi-agent data flows, and component interactions
- `docs/DEPLOYMENT.md` — deployment guide covering backend, frontend, and MongoDB setup

