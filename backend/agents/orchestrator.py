"""
OrchestratorAgent — the brain of the system.
Routes user intent to the right agent(s), decides when Gemini is needed,
and assembles the final response.

Intent routing (no Gemini needed):
  dashboard / overview      → ReportAgent.get_dashboard_report
  risk / water stress       → RiskAgent.assess_all_facilities
  compliance / permits      → ComplianceAgent.get_compliance_summary
  efficiency / savings      → EfficiencyAgent.get_opportunities
  meters / anomalies        → EfficiencyAgent.get_meter_anomalies
  facilities / compare      → EfficiencyAgent.get_facility_comparison
  suppliers                 → DataAgent.get_suppliers

Gemini is called ONLY for:
  - Free-text questions that need natural language answers
  - Mitigation plan generation (needs narrative)
  - Strategy building (needs narrative)
"""
import re
from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from .data_agent import DataAgent
from .risk_agent import RiskAgent
from .compliance_agent import ComplianceAgent
from .efficiency_agent import EfficiencyAgent
from .report_agent import ReportAgent

# Accept either OpenRouterService or GeminiService — both have generate_content()
try:
    from services.openrouter_service import OpenRouterService as _DefaultAI
except Exception:
    _DefaultAI = None


# Intent patterns → (agent, tool)
INTENT_MAP = [
    (r"dashboard|overview|summary|water usage|total usage|how much water|view dashboard", ("report", "get_dashboard_report")),
    (r"risk|water stress|drought|flood|aqueduct|wri|stress score|risk assessment", ("risk", "assess_all_facilities")),
    (r"compliance|permit|discharge|violation|npdes|dmr|compliance.*permit", ("compliance", "get_compliance_summary")),
    (r"efficien|saving|opportunit|reduce|leak|fixture|cooling tower|recycl|efficiency opportunit", ("efficiency", "get_opportunities")),
    (r"meter|anomal|spike|unusual|reading", ("efficiency", "get_meter_anomalies")),
    (r"facilit|compar|location|plant|site", ("efficiency", "get_facility_comparison")),
    (r"supplier|supply chain|vendor|material", ("data", "get_suppliers")),
]


class OrchestratorAgent(BaseAgent):
    name = "orchestrator"
    description = "Routes user requests to the right agent and assembles responses"

    def __init__(self, gemini_service=None):
        self.gemini = gemini_service
        self.data_agent = DataAgent()
        self.risk_agent = RiskAgent(ai_service=gemini_service)
        self.compliance_agent = ComplianceAgent()
        self.efficiency_agent = EfficiencyAgent()
        self.report_agent = ReportAgent()
        super().__init__()

    def _detect_intent(self, message: str) -> Optional[tuple]:
        """Return (agent_name, tool_name) or None if no match."""
        msg = message.lower()
        for pattern, target in INTENT_MAP:
            if re.search(pattern, msg):
                return target
        return None

    async def handle(self, message: str, user_id: str = "demo", session_id: str = None) -> Dict[str, Any]:
        """
        Main entry point. Takes a user message, routes it, returns structured response.
        """
        msg_lower = message.lower()

        # Upload flow — return upload type options
        if re.search(r"upload|add data|upload water data", msg_lower) and not re.search(
            r"utility|meter|facility|supplier|discharge", msg_lower
        ):
            return {
                "type": "upload_options",
                "content": "I need 5 types of documents for complete water insights. Which one would you like to upload?",
                "options": [
                    {"id": "utility_bills", "label": "💵 Utility Bills", "icon": "💵", "description": "Water bills (PDF/Excel/CSV)"},
                    {"id": "meter_readings", "label": "📟 Meter Readings", "icon": "📟", "description": "IoT/meter logs"},
                    {"id": "facility_info", "label": "🏭 Facility Info", "icon": "🏭", "description": "Location & operational details"},
                    {"id": "supplier_list", "label": "📦 Supplier List", "icon": "📦", "description": "Supply chain data"},
                    {"id": "discharge_reports", "label": "🧪 Discharge Reports", "icon": "🧪", "description": "Permits & pollutant data"},
                ],
                "source": "orchestrator",
            }

        # Dashboard sub-views
        if re.search(r"view trends|12 months|monthly trend|usage trend", msg_lower):
            result = await self.report_agent.run_tool("get_trends_report", user_id=user_id)
            return {
                "type": "trends",
                "content": result.get("summary", "Here's your 12-month water usage trend."),
                "data": result,
                "options": [
                    {"id": "water_balance", "label": "💧 Water Balance Details", "icon": "💧"},
                    {"id": "cost_analysis", "label": "💰 Cost Analysis", "icon": "💰"},
                    {"id": "dashboard", "label": "📊 Back to Dashboard", "icon": "📊"},
                ],
                "source": "agents",
            }

        if re.search(r"water balance|balance detail|sankey|withdrawal|consumption breakdown", msg_lower):
            result = await self.report_agent.run_tool("get_water_balance", user_id=user_id)
            return {
                "type": "water_balance",
                "content": result.get("summary", "Here's your water flow breakdown."),
                "data": result,
                "options": [
                    {"id": "trends", "label": "📈 View Trends (12 months)", "icon": "📈"},
                    {"id": "cost_analysis", "label": "💰 Cost Analysis", "icon": "💰"},
                    {"id": "dashboard", "label": "📊 Back to Dashboard", "icon": "📊"},
                ],
                "source": "agents",
            }

        if re.search(r"pollutant|pollutant level|discharge level|bod|cod|tss|water quality", msg_lower):
            result = await self.report_agent.run_tool("get_pollutant_levels", user_id=user_id)
            return {
                "type": "pollutant_levels",
                "content": result.get("summary", "Here are your pollutant levels from discharge reports."),
                "data": result,
                "options": [
                    {"id": "compliance", "label": "📋 Compliance & Permits", "icon": "📋"},
                    {"id": "dashboard", "label": "📊 Back to Dashboard", "icon": "📊"},
                ],
                "source": "agents",
            }

        if re.search(r"cost analysis|cost breakdown|spending|cost per|water cost", msg_lower):
            result = await self.report_agent.run_tool("get_cost_analysis", user_id=user_id)
            return {
                "type": "cost_analysis",
                "content": result.get("summary", "Here's your water cost breakdown."),
                "data": result,
                "options": [
                    {"id": "efficiency", "label": "📈 Efficiency Opportunities", "icon": "📈"},
                    {"id": "trends", "label": "📈 View Trends (12 months)", "icon": "📈"},
                    {"id": "dashboard", "label": "📊 Back to Dashboard", "icon": "📊"},
                ],
                "source": "agents",
            }

        # Risk sub-views
        if re.search(r"compare all facilit|compare facilit|facility comparison|side.by.side", msg_lower):
            result = await self.risk_agent.run_tool("compare_facilities", user_id=user_id)
            return {
                "type": "facility_risk_comparison",
                "content": result.get("summary", "Here's the side-by-side risk comparison of your facilities."),
                "data": result,
                "options": [
                    {"id": "risk_map", "label": "🗺️ View Risk Map", "icon": "🗺️"},
                    {"id": "mitigation", "label": "💡 Get Risk Mitigation Strategies", "icon": "💡"},
                    {"id": "risk", "label": "🗺️ Back to Risk Assessment", "icon": "🗺️"},
                ],
                "source": "agents",
            }

        if re.search(r"view risk map|risk map|map.*facilit|facilit.*map", msg_lower):
            result = await self.risk_agent.run_tool("get_risk_map_data", user_id=user_id)
            return {
                "type": "risk_map",
                "content": result.get("summary", "Here's your facility water risk map."),
                "data": result,
                "options": [
                    {"id": "compare_facilities", "label": "📊 Compare All Facilities", "icon": "📊"},
                    {"id": "climate_scenarios", "label": "📈 See Climate Scenarios", "icon": "📈"},
                    {"id": "risk", "label": "🗺️ Back to Risk Assessment", "icon": "🗺️"},
                ],
                "source": "agents",
            }

        if re.search(r"climate scenario|climate projection|future.*water|water.*future|see climate", msg_lower):
            result = await self.risk_agent.run_tool("get_climate_scenarios", user_id=user_id)
            return {
                "type": "climate_scenarios",
                "content": result.get("summary", "Here are the climate projections for your facilities."),
                "data": result,
                "options": [
                    {"id": "mitigation", "label": "💡 Get Risk Mitigation Strategies", "icon": "💡"},
                    {"id": "risk", "label": "🗺️ Back to Risk Assessment", "icon": "🗺️"},
                    {"id": "strategy", "label": "🎯 Build Stewardship Strategy", "icon": "🎯"},
                ],
                "source": "agents",
            }

        if re.search(r"assess supplier risk|supplier risk|supply chain risk|supply chain water|🌍", msg_lower):
            raw = await self.data_agent.run_tool("get_suppliers", user_id=user_id)
            supplier_list = (raw or {}).get("suppliers", [])

            # Classify risk by water_intensity_factor (gal per $1M spend)
            HIGH_THRESHOLD = 200000
            MED_THRESHOLD = 100000

            high_risk = [s for s in supplier_list if s.get("water_intensity_factor", 0) > HIGH_THRESHOLD]
            med_risk  = [s for s in supplier_list if MED_THRESHOLD < s.get("water_intensity_factor", 0) <= HIGH_THRESHOLD]
            low_risk  = [s for s in supplier_list if s.get("water_intensity_factor", 0) <= MED_THRESHOLD]

            total = len(supplier_list)
            high_pct = round(len(high_risk) / total * 100, 1) if total else 0

            # Build key insights from real data
            key_insights = []
            if high_risk:
                key_insights.append({
                    "type": "critical",
                    "message": f"{len(high_risk)} supplier(s) have extremely high water intensity (>{HIGH_THRESHOLD:,} gal/$1M spend)"
                })
            if med_risk:
                key_insights.append({
                    "type": "warning",
                    "message": f"{len(med_risk)} supplier(s) have medium water intensity — monitor closely"
                })
            if low_risk:
                key_insights.append({
                    "type": "info",
                    "message": f"{len(low_risk)} supplier(s) are low risk based on water intensity"
                })
            total_spend = sum(s.get("annual_spend_usd", 0) for s in supplier_list)
            if total_spend:
                key_insights.append({
                    "type": "info",
                    "message": f"Total annual supplier spend: ${total_spend:,.0f} across {total} supplier(s)"
                })

            # Top risk suppliers sorted by intensity
            top_risk = sorted(supplier_list, key=lambda s: -s.get("water_intensity_factor", 0))[:5]
            top_risk_shaped = []
            for s in top_risk:
                loc = s.get("location", {})
                if isinstance(loc, str):
                    loc = {"city": loc, "country": ""}
                top_risk_shaped.append({
                    "supplier_name": s.get("supplier_name", s.get("name", "")),
                    "water_intensity_factor": s.get("water_intensity_factor", 0),
                    "material_category": s.get("material_category", s.get("product_category", "")),
                    "location": {
                        "city": loc.get("city", loc.get("state", "")),
                        "country": loc.get("country", "US"),
                    },
                    "annual_spend_usd": s.get("annual_spend_usd", 0),
                })

            # AI-generated recommendations using real supplier data
            recommendations = []
            if self.gemini:
                try:
                    import json as _json
                    supplier_summary = [
                        {
                            "name": s.get("supplier_name", ""),
                            "category": s.get("material_category", ""),
                            "water_intensity": s.get("water_intensity_factor", 0),
                            "annual_spend_usd": s.get("annual_spend_usd", 0),
                            "city": s.get("location", {}).get("city", "") if isinstance(s.get("location"), dict) else "",
                        }
                        for s in sorted(supplier_list, key=lambda x: -x.get("water_intensity_factor", 0))[:6]
                    ]
                    prompt = f"""You are a supply chain water risk expert. Generate 4 specific, actionable recommendations based on this real supplier data.

SUPPLIER DATA:
- Total suppliers: {total}
- High risk (>{HIGH_THRESHOLD:,} gal/$1M): {[s['name'] for s in supplier_summary if s['water_intensity'] > HIGH_THRESHOLD]}
- Medium risk: {[s['name'] for s in supplier_summary if MED_THRESHOLD < s['water_intensity'] <= HIGH_THRESHOLD]}
- Top suppliers by water intensity: {_json.dumps(supplier_summary[:4])}
- Total annual spend: ${total_spend:,.0f}

Return ONLY valid JSON array with exactly 4 items:
[
  {{"priority": "High", "action": "specific action mentioning real supplier names and categories", "impact": "quantified expected impact"}},
  {{"priority": "High", "action": "...", "impact": "..."}},
  {{"priority": "Medium", "action": "...", "impact": "..."}},
  {{"priority": "Medium", "action": "...", "impact": "..."}}
]"""
                    resp = await self.gemini.generate_content(prompt)
                    clean = resp.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    recommendations = _json.loads(clean)
                except Exception as e:
                    print(f"Supplier AI recommendations error (non-fatal): {e}")

            # Fallback if AI fails or unavailable
            if not recommendations:
                if high_risk:
                    recommendations.append({
                        "priority": "High",
                        "action": f"Engage {high_risk[0].get('supplier_name', 'top supplier')} ({high_risk[0].get('material_category','')}) on water reduction targets and request annual stewardship disclosure",
                        "impact": "Reduce supply chain water risk by 20-30%",
                    })
                if len(high_risk) > 1:
                    recommendations.append({
                        "priority": "High",
                        "action": f"Require water intensity reporting from {', '.join(s.get('supplier_name','') for s in high_risk)} as procurement criteria",
                        "impact": "Improve supply chain transparency and accountability",
                    })
                if med_risk:
                    recommendations.append({
                        "priority": "Medium",
                        "action": f"Set water reduction targets for {med_risk[0].get('supplier_name','')} and {len(med_risk)-1} other medium-risk suppliers",
                        "impact": "Prevent escalation to high-risk category",
                    })
                recommendations.append({
                    "priority": "Medium",
                    "action": "Diversify supply base by sourcing from suppliers in lower water-stress regions",
                    "impact": "Reduce geographic concentration of water risk",
                })

            shaped = {
                "total_suppliers": total,
                "high_risk_count": len(high_risk),
                "high_risk_percentage": high_pct,
                "medium_risk_count": len(med_risk),
                "low_risk_count": len(low_risk),
                "key_insights": key_insights,
                "top_risk_suppliers": top_risk_shaped,
                "recommendations": recommendations,
            }

            return {
                "type": "suppliers",
                "content": f"Supply chain risk assessed for {total} supplier(s). {len(high_risk)} high-risk, {len(med_risk)} medium-risk.",
                "data": shaped,
                "supplier_risk_data": shaped,
                "options": [
                    {"id": "risk", "label": "🗺️ Back to Risk Assessment", "icon": "🗺️"},
                    {"id": "strategy", "label": "🎯 Build Stewardship Strategy", "icon": "🎯"},
                    {"id": "footprint", "label": "💧 Water Footprint", "icon": "💧"},
                ],
                "source": "agents",
            }

        # Mitigation plan request
        if re.search(r"mitigation strateg|get risk mitigation|mitigation plan|build.*mitigation", msg_lower):
            if self.gemini:
                try:
                    # Get real facility + risk data to pass to AI
                    scored = await self.risk_agent.run_tool("assess_all_facilities", user_id=user_id)
                    facilities = scored.get("facilities", [])
                    result = await self.gemini.generate_mitigation_plan(
                        {"facilities": facilities},
                        {"overall_risk_score": scored.get("overall_portfolio_risk"), "facilities": facilities}
                    )
                    plan = result.get("mitigation_plan", {})
                    return {
                        "type": "mitigation_plan",
                        "content": "Here's your water risk mitigation plan based on your facility data.",
                        "mitigation_plan": plan,
                        "options": [
                            {"id": "download_plan", "label": "💾 Download Plan", "icon": "💾"},
                            {"id": "strategy", "label": "🎯 Build Stewardship Strategy", "icon": "🎯"},
                            {"id": "efficiency", "label": "📈 Efficiency Opportunities", "icon": "📈"},
                        ],
                        "source": "ai",
                    }
                except Exception as e:
                    print(f"Mitigation plan error: {e}")

        # DMR Report generation
        if re.search(r"generate dmr|dmr report|discharge monitoring report|generate.*dmr", msg_lower):
            try:
                from database import get_db
                import json as _json
                from datetime import datetime as _dt

                db = get_db()
                # Fetch raw discharge reports directly
                docs = await db.discharge_reports.find({"user_id": user_id}, {"_id": 0}).to_list(length=None)
                # Fetch utility bills for discharge volume estimation
                bills = await db.utility_bills.find({"user_id": user_id}, {"_id": 0}).to_list(length=None)

                # Estimate total discharge volume from bills (wastewater field or 60% of withdrawal)
                total_discharge_gal = sum(
                    b.get("wastewater_volume_gallons", b.get("discharge_volume_gallons", 0)) for b in bills
                )
                total_withdrawal_gal = sum(b.get("water_volume_gallons", 0) for b in bills)
                if total_discharge_gal == 0 and total_withdrawal_gal > 0:
                    total_discharge_gal = round(total_withdrawal_gal * 0.60)

                if not docs:
                    return {
                        "type": "text",
                        "content": "No discharge reports found. Please upload discharge report data first.",
                        "options": [
                            {"id": "upload", "label": "📤 Upload Discharge Reports", "icon": "📤"},
                            {"id": "compliance", "label": "📋 Back to Compliance", "icon": "📋"},
                        ],
                        "source": "error",
                    }

                # Build permit structures directly from real DB data
                all_permits_raw = [p for doc in docs for p in doc.get("permits", [])]
                permit_count = len(all_permits_raw)
                # Distribute discharge volume evenly across permits
                discharge_per_permit = round(total_discharge_gal / permit_count) if permit_count else 0

                built_permits = []
                for p in all_permits_raw:
                    params_raw = p.get("parameters", [])
                    built_params = []
                    for param in params_raw:
                        val = param.get("sample_value", param.get("measured_value", ""))
                        limit = param.get("limit_value", param.get("limit", ""))
                        unit = param.get("limit_unit", param.get("unit", "mg/L"))
                        status = param.get("compliance_status", "pass")
                        name = param.get("parameter", param.get("parameter_name", param.get("name", "")))
                        built_params.append({
                            "name": name,
                            "average_value": str(val),
                            "max_value": str(val),  # use same value if no separate max
                            "limit": str(limit),
                            "unit": unit,
                            "status": "pass" if str(status).lower() == "pass" else "fail",
                        })

                    total_params = len(built_params)
                    passed_params = sum(1 for x in built_params if x["status"] == "pass")
                    compliance_rate = round(passed_params / total_params * 100, 1) if total_params else 100
                    avg_daily = round(discharge_per_permit / 365) if discharge_per_permit else 0

                    built_permits.append({
                        "permit_id": p.get("permit_id", ""),
                        "permit_type": p.get("permit_type", "Discharge"),
                        "issuing_authority": p.get("issuing_authority", ""),
                        "outfall_id": p.get("outfall_id", ""),
                        "lab_name": p.get("lab_name", ""),
                        "effective_date": p.get("effective_date", ""),
                        "expiration_date": p.get("expiration_date", ""),
                        "compliance_rate": compliance_rate,
                        "discharge_volume_gallons": discharge_per_permit,
                        "avg_daily_flow_gallons": avg_daily,
                        "parameters": built_params,
                        "overall_status": "Compliant" if compliance_rate == 100 else "Violation",
                    })

                # Determine reporting period from bills or use current year
                if bills:
                    dates = sorted([str(b.get("billing_period_start") or b.get("date", ""))[:7] for b in bills if b.get("billing_period_start") or b.get("date")])
                    period = f"{dates[0]}-01 to {dates[-1]}-28" if dates else "2025-01-01 to 2025-12-31"
                else:
                    period = "2025-01-01 to 2025-12-31"

                # Use AI only for summary text and recommendations (not for data values)
                ai_summary = "All monitored parameters are within permitted limits. Continue current monitoring practices."
                ai_recommendations = ["Continue current monitoring and operational practices to maintain compliance."]

                if self.gemini:
                    try:
                        violations = [x for p in built_permits for x in p["parameters"] if x["status"] == "fail"]
                        prompt = f"""You are a water compliance expert. Write a brief DMR summary and 2-3 recommendations.

REAL DATA:
- Permits: {len(built_permits)}
- Total discharge: {total_discharge_gal:,} gallons
- Compliance rate: {round(sum(p['compliance_rate'] for p in built_permits)/len(built_permits),1) if built_permits else 100}%
- Violations: {len(violations)}
- Reporting period: {period}

Return ONLY valid JSON: {{"summary": "...", "recommendations": ["...", "..."]}}"""
                        resp = await self.gemini.generate_content(prompt)
                        clean = resp.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                        ai_out = _json.loads(clean)
                        ai_summary = ai_out.get("summary", ai_summary)
                        ai_recommendations = ai_out.get("recommendations", ai_recommendations)
                    except Exception as e:
                        print(f"DMR AI summary error (non-fatal): {e}")

                dmr = {
                    "report_title": "Discharge Monitoring Report",
                    "reporting_period": period,
                    "generated_date": _dt.utcnow().strftime("%Y-%m-%d"),
                    "permits": built_permits,
                    "summary": ai_summary,
                    "certification": "I certify under penalty of law that this document and all attachments were prepared under my direction or supervision in accordance with a system designed to assure that qualified personnel properly gather and evaluate the information submitted.",
                    "violations": [x for p in built_permits for x in p["parameters"] if x["status"] == "fail"],
                    "recommendations": ai_recommendations,
                }

                return {
                    "type": "dmr_report",
                    "content": f"💧 DMR Report generated for {len(built_permits)} permit(s).",
                    "dmr_data": dmr,
                    "options": [
                        {"id": "download_dmr", "label": "💾 Download DMR Report", "icon": "💾"},
                        {"id": "compliance", "label": "📋 Back to Compliance", "icon": "📋"},
                        {"id": "dashboard", "label": "📊 View Dashboard", "icon": "📊"},
                    ],
                    "source": "agents",
                }
            except Exception as e:
                print(f"DMR generation error: {e}")
                return {
                    "type": "text",
                    "content": "Failed to generate DMR report. Please try again.",
                    "options": [{"id": "compliance", "label": "📋 Back to Compliance", "icon": "📋"}],
                    "source": "error",
                }


        if re.search(r"strategy|stewardship|build.*plan|stewardship strategy", msg_lower):
            # Pull real data
            usage = await self.data_agent.get_usage_summary(user_id)
            compliance = await self.compliance_agent.get_compliance_summary(user_id)
            efficiency = await self.efficiency_agent.get_opportunities(user_id)
            suppliers = await self.data_agent.get_suppliers(user_id)

            total_gal = usage.get("total_volume_gallons", 0)
            total_cost = usage.get("total_cost_usd", 0)
            compliance_rate = compliance.get("overall_compliance_rate", 100) if compliance.get("has_data") else 100
            opp_count = efficiency.get("opportunity_count", 0)
            potential_savings = efficiency.get("total_potential_savings_usd", 0)
            opportunities = efficiency.get("opportunities", [])
            supplier_list = (suppliers or {}).get("suppliers", [])
            high_risk_suppliers = [s for s in supplier_list if s.get("water_intensity_factor", 0) > 200000]

            # Ask AI for structured strategy JSON
            import json as _json
            from datetime import datetime as _dt

            strategy_data = None
            if self.gemini:
                try:
                    prompt = f"""You are a water stewardship advisor. Generate a professional water stewardship strategy based on this real data.

REAL DATA:
- Total water usage: {total_gal:,} gallons/year
- Total water cost: ${total_cost:,.0f}/year
- Compliance rate: {compliance_rate}%
- Efficiency opportunities: {opp_count} worth ${potential_savings:,.0f}/year savings
- High-risk suppliers: {[s.get('supplier_name','') for s in high_risk_suppliers]}
- Top opportunities: {[o.get('name','') for o in opportunities[:3]]}

Return ONLY valid JSON:
{{
  "target_reduction_pct": 30,
  "target_year": 2027,
  "executive_summary": "2-3 sentence plain text summary of the strategy",
  "priorities": [
    {{"rank": 1, "title": "short title", "description": "one sentence action", "impact": "quantified impact", "timeline": "Q1 2026"}},
    {{"rank": 2, "title": "...", "description": "...", "impact": "...", "timeline": "..."}},
    {{"rank": 3, "title": "...", "description": "...", "impact": "...", "timeline": "..."}}
  ],
  "kpis": [
    {{"metric": "Total Water Usage", "baseline": "{total_gal:,} gal", "target": "...", "frequency": "Monthly"}},
    {{"metric": "Water Cost", "baseline": "${total_cost:,.0f}", "target": "...", "frequency": "Monthly"}},
    {{"metric": "Compliance Rate", "baseline": "{compliance_rate}%", "target": "100%", "frequency": "Quarterly"}},
    {{"metric": "Supplier Risk Score", "baseline": "{len(high_risk_suppliers)} high-risk", "target": "0 high-risk", "frequency": "Annually"}}
  ],
  "timeline": [
    {{"phase": "Phase 1", "period": "Months 1-3", "actions": ["action 1", "action 2"]}},
    {{"phase": "Phase 2", "period": "Months 4-6", "actions": ["action 1", "action 2"]}},
    {{"phase": "Phase 3", "period": "Months 7-12", "actions": ["action 1", "action 2"]}}
  ]
}}"""
                    resp = await self.gemini.generate_content(prompt)
                    clean = resp.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    strategy_data = _json.loads(clean)
                except Exception as e:
                    print(f"Strategy AI error (non-fatal): {e}")

            # Fallback structure if AI fails
            if not strategy_data:
                strategy_data = {
                    "target_reduction_pct": 30,
                    "target_year": 2027,
                    "executive_summary": f"Your portfolio uses {total_gal:,} gallons at ${total_cost:,.0f}/year. A 30% reduction target by 2027 is achievable through efficiency upgrades, supplier engagement, and compliance maintenance.",
                    "priorities": [
                        {"rank": 1, "title": "Efficiency Upgrades", "description": f"Implement {opp_count} identified opportunities", "impact": f"${potential_savings:,.0f}/year savings", "timeline": "Q1-Q2 2026"},
                        {"rank": 2, "title": "Supplier Engagement", "description": f"Engage {len(high_risk_suppliers)} high-risk suppliers on reduction targets", "impact": "Reduce supply chain risk by 20-30%", "timeline": "Q1 2026"},
                        {"rank": 3, "title": "Compliance Monitoring", "description": "Maintain 100% compliance across all permits", "impact": "Avoid fines and operational disruption", "timeline": "Ongoing"},
                    ],
                    "kpis": [
                        {"metric": "Total Water Usage", "baseline": f"{total_gal:,} gal", "target": f"{round(total_gal*0.7):,} gal", "frequency": "Monthly"},
                        {"metric": "Water Cost", "baseline": f"${total_cost:,.0f}", "target": f"${round(total_cost*0.7):,.0f}", "frequency": "Monthly"},
                        {"metric": "Compliance Rate", "baseline": f"{compliance_rate}%", "target": "100%", "frequency": "Quarterly"},
                        {"metric": "Supplier Risk", "baseline": f"{len(high_risk_suppliers)} high-risk", "target": "0 high-risk", "frequency": "Annually"},
                    ],
                    "timeline": [
                        {"phase": "Phase 1", "period": "Months 1-3", "actions": ["Baseline audit", "Supplier outreach", "Metering install"]},
                        {"phase": "Phase 2", "period": "Months 4-6", "actions": ["Efficiency upgrades", "Supplier targets set", "KPI dashboard live"]},
                        {"phase": "Phase 3", "period": "Months 7-12", "actions": ["Progress review", "Adjust targets", "Annual report"]},
                    ],
                }

            strategy_data["generated_date"] = _dt.utcnow().strftime("%Y-%m-%d")
            strategy_data["total_gal"] = total_gal
            strategy_data["total_cost"] = total_cost

            return {
                "type": "stewardship_strategy",
                "content": strategy_data.get("executive_summary", "Your stewardship strategy is ready."),
                "strategy_data": strategy_data,
                "options": [
                    {"id": "download_strategy", "label": "💾 Download Strategy", "icon": "💾"},
                    {"id": "dashboard", "label": "📊 View Dashboard", "icon": "📊"},
                ],
                "source": "ai",
            }

        # Footprint sub-views (must come BEFORE the main footprint handler)
        if re.search(r"compare to industry|industry benchmark|compare.*industry", msg_lower):
            result = await self.report_agent.run_tool("get_industry_comparison", user_id=user_id)
            return {
                "type": "industry_comparison",
                "content": result.get("summary", "Here's how you compare to industry benchmarks."),
                "data": result,
                "options": [
                    {"id": "set_reduction_target", "label": "🎯 Set Reduction Target", "icon": "🎯"},
                    {"id": "identify_hotspots", "label": "📈 Identify Hotspots", "icon": "📈"},
                    {"id": "footprint", "label": "💧 Back to Footprint", "icon": "💧"},
                ],
                "source": "agents",
            }

        if re.search(r"set reduction target|reduction target|set.*target|water.*target", msg_lower):
            result = await self.report_agent.run_tool("get_reduction_targets", user_id=user_id)
            return {
                "type": "reduction_targets",
                "content": result.get("summary", "Here are your water reduction target options."),
                "data": result,
                "options": [
                    {"id": "efficiency", "label": "📈 Efficiency Opportunities", "icon": "📈"},
                    {"id": "strategy", "label": "🎯 Build Stewardship Strategy", "icon": "🎯"},
                    {"id": "footprint", "label": "💧 Back to Footprint", "icon": "💧"},
                ],
                "source": "agents",
            }

        if re.search(r"identify hotspot|hotspot|highest.*usage|top.*consumer", msg_lower):
            result = await self.report_agent.run_tool("get_footprint_hotspots", user_id=user_id)
            return {
                "type": "footprint_hotspots",
                "content": result.get("summary", "Here are your top water usage hotspots."),
                "data": result,
                "options": [
                    {"id": "efficiency", "label": "📈 Efficiency Opportunities", "icon": "📈"},
                    {"id": "compare_industry", "label": "📊 Compare to Industry", "icon": "📊"},
                    {"id": "footprint", "label": "💧 Back to Footprint", "icon": "💧"},
                ],
                "source": "agents",
            }

        if re.search(r"generate footprint report|footprint.*report|generate.*footprint", msg_lower):
            result = await self.report_agent.run_tool("get_water_footprint", user_id=user_id)
            industry = await self.report_agent.run_tool("get_industry_comparison", user_id=user_id)
            hotspots = await self.report_agent.run_tool("get_footprint_hotspots", user_id=user_id)
            return {
                "type": "footprint_report",
                "content": "Your water footprint report is ready.",
                "data": {"footprint": result, "industry": industry, "hotspots": hotspots},
                "options": [
                    {"id": "download_footprint_report", "label": "💾 Download Report", "icon": "💾"},
                    {"id": "set_reduction_target", "label": "🎯 Set Reduction Target", "icon": "🎯"},
                    {"id": "footprint", "label": "💧 Back to Footprint", "icon": "💧"},
                ],
                "source": "agents",
            }

        # Footprint calculation (main — must be AFTER sub-views)
        if re.search(r"footprint|calculate.*water|water.*footprint", msg_lower):
            result = await self.report_agent.run_tool("get_water_footprint", user_id=user_id)
            return {
                "type": "water_footprint",
                "content": result.get("summary", "Here's your water footprint breakdown."),
                "data": result,
                "options": [
                    {"id": "compare_industry", "label": "📊 Compare to Industry", "icon": "📊"},
                    {"id": "set_reduction_target", "label": "🎯 Set Reduction Target", "icon": "🎯"},
                    {"id": "identify_hotspots", "label": "📈 Identify Hotspots", "icon": "📈"},
                    {"id": "generate_footprint_report", "label": "📋 Generate Report", "icon": "📋"},
                ],
                "source": "agents",
            }

        # Ask me anything / general
        if re.search(r"ask|anything|help|what can you|how do", msg_lower):
            return {
                "type": "text",
                "content": "I can help you with water usage tracking, risk assessment, efficiency opportunities, compliance monitoring, and stewardship strategy. What would you like to explore?",
                "options": [
                    {"id": "dashboard", "label": "📊 View Dashboard", "icon": "📊"},
                    {"id": "risk", "label": "🗺️ Water Risk Assessment", "icon": "🗺️"},
                    {"id": "efficiency", "label": "📈 Efficiency Opportunities", "icon": "📈"},
                    {"id": "compliance", "label": "📋 Compliance & Permits", "icon": "📋"},
                ],
                "source": "orchestrator",
            }

        intent = self._detect_intent(message)

        if intent:
            agent_name, tool_name = intent
            result = await self._dispatch(agent_name, tool_name, user_id)
            return self._format_response(agent_name, tool_name, result)

        # No structured intent — use AI for free-text
        if self.gemini:
            context = await self._build_context(user_id)
            enriched_prompt = self._build_prompt(message, context)
            gemini_result = await self.gemini.generate_content(enriched_prompt)
            return {
                "type": "text",
                "content": gemini_result,
                "source": "gemini",
                "options": [
                    {"id": "dashboard", "label": "📊 View Dashboard", "icon": "📊"},
                    {"id": "risk", "label": "🗺️ Water Risk Assessment", "icon": "🗺️"},
                    {"id": "efficiency", "label": "📈 Efficiency Opportunities", "icon": "📈"},
                ],
            }

        return {
            "type": "text",
            "content": "I can help with: dashboard, risk assessment, compliance, efficiency opportunities, meter analysis, facility comparison, and supplier risk. What would you like to know?",
            "source": "fallback",
            "options": [
                {"id": "dashboard", "label": "📊 View Dashboard", "icon": "📊"},
                {"id": "risk", "label": "🗺️ Water Risk Assessment", "icon": "🗺️"},
                {"id": "efficiency", "label": "📈 Efficiency Opportunities", "icon": "📈"},
                {"id": "compliance", "label": "📋 Compliance & Permits", "icon": "📋"},
            ],
        }

    async def _dispatch(self, agent_name: str, tool_name: str, user_id: str) -> Any:
        agents = {
            "report": self.report_agent,
            "risk": self.risk_agent,
            "compliance": self.compliance_agent,
            "efficiency": self.efficiency_agent,
            "data": self.data_agent,
        }
        agent = agents.get(agent_name)
        if not agent:
            return {"error": f"Unknown agent: {agent_name}"}
        return await agent.run_tool(tool_name, user_id=user_id)

    # Follow-up options per response type — matches chatbotflow.txt
    FOLLOW_UP_OPTIONS = {
        "dashboard": [
            {"id": "trends", "label": "📈 View Trends (12 months)", "icon": "📈"},
            {"id": "water_balance", "label": "💧 Water Balance Details", "icon": "💧"},
            {"id": "pollutant_levels", "label": "🧪 Pollutant Levels", "icon": "🧪"},
            {"id": "cost_analysis", "label": "💰 Cost Analysis", "icon": "💰"},
        ],
        "risk_assessment": [
            {"id": "mitigation", "label": "💡 Get Risk Mitigation Strategies", "icon": "💡"},
            {"id": "compare_facilities", "label": "📊 Compare All Facilities", "icon": "📊"},
            {"id": "risk_map", "label": "🗺️ View Risk Map", "icon": "🗺️"},
            {"id": "supplier_risk", "label": "🌍 Assess Supplier Risks", "icon": "🌍"},
            {"id": "climate_scenarios", "label": "📈 See Climate Scenarios", "icon": "📈"},
        ],
        "compliance": [
            {"id": "generate_dmr", "label": "📋 Generate DMR Report", "icon": "📋"},
            {"id": "dashboard", "label": "📊 View Dashboard", "icon": "📊"},
            {"id": "upload", "label": "📤 Upload More Data", "icon": "📤"},
        ],
        "efficiency": [
            {"id": "strategy", "label": "🎯 Add to Stewardship Strategy", "icon": "🎯"},
            {"id": "risk", "label": "🗺️ Water Risk Assessment", "icon": "🗺️"},
            {"id": "dashboard", "label": "📊 View Dashboard", "icon": "📊"},
        ],
        "meter_anomalies": [
            {"id": "efficiency", "label": "📈 View All Opportunities", "icon": "📈"},
            {"id": "dashboard", "label": "📊 View Dashboard", "icon": "📊"},
        ],
        "facility_comparison": [
            {"id": "efficiency", "label": "📈 Efficiency Opportunities", "icon": "📈"},
            {"id": "risk", "label": "🗺️ Water Risk Assessment", "icon": "🗺️"},
            {"id": "dashboard", "label": "📊 View Dashboard", "icon": "📊"},
        ],
        "suppliers": [
            {"id": "supply_chain", "label": "🌊 Supply Chain Water Risk", "icon": "🌊"},
            {"id": "strategy", "label": "🎯 Build Stewardship Strategy", "icon": "🎯"},
            {"id": "dashboard", "label": "📊 View Dashboard", "icon": "📊"},
        ],
    }

    def _format_response(self, agent_name: str, tool_name: str, result: Any) -> Dict[str, Any]:
        """Wrap agent result in a typed response envelope."""
        type_map = {
            ("report", "get_dashboard_report"): "dashboard",
            ("risk", "assess_all_facilities"): "risk_assessment",
            ("compliance", "get_compliance_summary"): "compliance",
            ("efficiency", "get_opportunities"): "efficiency",
            ("efficiency", "get_meter_anomalies"): "meter_anomalies",
            ("efficiency", "get_facility_comparison"): "facility_comparison",
            ("data", "get_suppliers"): "suppliers",
        }
        response_type = type_map.get((agent_name, tool_name), "data")

        # Generate a human-readable summary line
        content = self._summarize(response_type, result)

        return {
            "type": response_type,
            "content": content,
            "data": result,
            "source": "agents",
            "agent": agent_name,
            "options": self.FOLLOW_UP_OPTIONS.get(response_type, []),
        }

    def _summarize(self, response_type: str, result: Any) -> str:
        if not isinstance(result, dict):
            return "Here are the results:"

        if response_type == "dashboard":
            if not result.get("has_data"):
                return "No data uploaded yet. Upload utility bills, meter data, or facility info to see your dashboard."
            cards = result.get("summary_cards", [])
            usage = next((c for c in cards if "Usage" in c.get("title", "")), None)
            return f"Here's your water dashboard. {usage['value'] + ' ' + usage['unit'] if usage else ''}"

        if response_type == "risk_assessment":
            if result.get("error"):
                return result["error"]
            level = result.get("overall_risk_level", "Unknown")
            count = result.get("facility_count", 0)
            high = result.get("high_risk_count", 0)
            return f"Risk assessment complete for {count} facilities. Overall: {level}. {high} high-risk facilities."

        if response_type == "compliance":
            if not result.get("has_data"):
                return result.get("message", "No compliance data available.")
            rate = result.get("overall_compliance_rate", "N/A")
            violations = result.get("violation_count", 0)
            return f"Compliance rate: {rate}%. {violations} violation(s) found."

        if response_type == "efficiency":
            if not result.get("has_data"):
                return result.get("message", "No usage data available.")
            count = result.get("opportunity_count", 0)
            savings = result.get("total_potential_savings_usd", 0)
            return f"Found {count} efficiency opportunities with ${savings:,.0f}/year potential savings."

        if response_type == "meter_anomalies":
            if not result:
                return "No meter anomalies detected."
            return f"Detected {len(result)} meter anomaly/anomalies requiring attention."

        return "Here are the results:"

    async def _build_context(self, user_id: str) -> Dict:
        """Build a compact context snapshot from real DB data for Gemini prompts."""
        try:
            usage = await self.data_agent.get_usage_summary(user_id)
            compliance = await self.compliance_agent.get_compliance_summary(user_id)
            return {"usage": usage, "compliance": compliance}
        except Exception:
            return {}

    def _build_prompt(self, user_message: str, context: Dict) -> str:
        usage = context.get("usage", {})
        compliance = context.get("compliance", {})

        ctx_lines = []
        if usage.get("has_data"):
            ctx_lines.append(f"- Total water usage: {usage.get('total_volume_gallons', 0):,} gallons")
            ctx_lines.append(f"- Total cost: ${usage.get('total_cost_usd', 0):,.2f}")
            ctx_lines.append(f"- Facilities: {', '.join(usage.get('facility_breakdown', {}).keys())}")
        if compliance.get("has_data"):
            ctx_lines.append(f"- Compliance rate: {compliance.get('overall_compliance_rate')}%")
            ctx_lines.append(f"- Violations: {compliance.get('violation_count', 0)}")

        context_block = "\n".join(ctx_lines) if ctx_lines else "No data uploaded yet."

        return f"""You are a Water Stewardship AI Assistant. Answer the user's question using the real data context below.

REAL DATA FROM DATABASE:
{context_block}

USER QUESTION: {user_message}

Provide a concise, helpful answer. Reference the actual numbers above when relevant."""
