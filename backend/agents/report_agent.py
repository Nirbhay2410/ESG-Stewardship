"""
ReportAgent — assembles data from other agents into structured reports.
Does NOT call Gemini. Pure data aggregation and formatting.
"""
from datetime import datetime
from typing import Any, Dict
from .base_agent import BaseAgent
from .data_agent import DataAgent
from .compliance_agent import ComplianceAgent
from .efficiency_agent import EfficiencyAgent


class ReportAgent(BaseAgent):
    name = "report_agent"
    description = "Assembles structured reports from real DB data without AI"

    def __init__(self):
        self.data_agent = DataAgent()
        self.compliance_agent = ComplianceAgent()
        self.efficiency_agent = EfficiencyAgent()
        super().__init__()

    def register_tools(self):
        self._register("get_dashboard_report", self.get_dashboard_report, "Full dashboard data from DB")
        self._register("get_full_summary", self.get_full_summary, "Complete water stewardship summary")
        self._register("get_trends_report", self.get_trends_report, "12-month usage trends from utility bills")
        self._register("get_water_balance", self.get_water_balance, "Water flow breakdown by source and use")
        self._register("get_pollutant_levels", self.get_pollutant_levels, "Pollutant results from discharge reports")
        self._register("get_cost_analysis", self.get_cost_analysis, "Cost breakdown by facility and period")
        self._register("get_water_footprint", self.get_water_footprint, "Full water footprint: blue/grey/supply chain")
        self._register("get_industry_comparison", self.get_industry_comparison, "Compare footprint to industry benchmarks")
        self._register("get_reduction_targets", self.get_reduction_targets, "Water reduction target scenarios")
        self._register("get_footprint_hotspots", self.get_footprint_hotspots, "Top water usage hotspots by facility/use")

    async def get_dashboard_report(self, user_id: str = "demo") -> Dict:
        usage = await self.data_agent.get_usage_summary(user_id)
        compliance = await self.compliance_agent.get_compliance_summary(user_id)
        facilities = await self.data_agent.get_facilities(user_id)
        suppliers = await self.data_agent.get_suppliers(user_id)
        facility_comparison = await self.efficiency_agent.get_facility_comparison(user_id)

        total_volume = usage["total_volume_gallons"] or usage["total_meter_consumption"]
        total_cost = usage["total_cost_usd"]
        compliance_rate = compliance.get("overall_compliance_rate", 100) if compliance.get("has_data") else "N/A"
        total_tests = compliance.get("total_parameters_tested", 0)
        passed_tests = compliance.get("passed_parameters", 0)

        # Supplier risk
        supplier_count = 0
        high_risk_count = 0
        if suppliers and suppliers.get("suppliers"):
            supplier_list = suppliers["suppliers"]
            supplier_count = len(supplier_list)
            high_risk_count = sum(1 for s in supplier_list if s.get("water_intensity_factor", 0) > 200000)

        # Summary cards
        summary_cards = [
            {
                "title": "Total Water Usage",
                "value": f"{total_volume / 1_000_000:.2f}M" if total_volume >= 1_000_000 else f"{total_volume:,}",
                "unit": "gallons/month",
                "icon": "💧",
                "color": "blue",
                "raw": total_volume,
            },
            {
                "title": "Total Cost",
                "value": f"${total_cost / 1000:.1f}K" if total_cost >= 1000 else f"${total_cost:.0f}",
                "unit": "per month",
                "icon": "💰",
                "color": "green",
                "raw": total_cost,
            },
            {
                "title": "Facilities",
                "value": str(len(facilities)),
                "unit": "locations tracked",
                "icon": "🏭",
                "color": "purple",
                "raw": len(facilities),
            },
            {
                "title": "Compliance Rate",
                "value": f"{compliance_rate}%",
                "unit": f"{passed_tests}/{total_tests} tests" if total_tests else "No data",
                "icon": "✅",
                "color": "teal",
                "raw": compliance_rate,
            },
        ]

        # Insights from real data
        insights = []
        if compliance.get("has_data") and compliance_rate == 100:
            insights.append({"type": "success", "message": f"100% compliance rate on discharge permits", "priority": "low"})
        elif compliance.get("has_data") and isinstance(compliance_rate, float) and compliance_rate < 100:
            insights.append({"type": "warning", "message": f"Compliance at {compliance_rate}% — action needed", "priority": "high"})

        if supplier_count > 0:
            insights.append({"type": "info", "message": f"{supplier_count} suppliers with {high_risk_count} in high water-risk areas", "priority": "medium"})

        if facility_comparison:
            top = facility_comparison[0]
            if top["percentage"] > 70:
                insights.append({"type": "warning", "message": f"{top['facility']} uses {top['percentage']}% of total water", "priority": "high"})

        expiring = compliance.get("expiring_soon", [])
        if expiring:
            insights.append({"type": "warning", "message": f"{len(expiring)} permit(s) expiring within 90 days", "priority": "high"})

        # Recommendations based on real data
        recommendations = []
        if facility_comparison and facility_comparison[0]["percentage"] > 70:
            recommendations.append({
                "title": f"Optimize {facility_comparison[0]['facility']}",
                "impact": "High",
                "savings": "15-25%",
            })
        if high_risk_count > 0:
            recommendations.append({
                "title": f"Monitor {high_risk_count} High-Risk Supplier(s)",
                "impact": "Medium",
                "savings": "N/A",
            })
        if compliance.get("violation_count", 0) > 0:
            recommendations.append({
                "title": "Resolve Compliance Violations",
                "impact": "High",
                "savings": "Avoid fines",
            })
        if expiring:
            recommendations.append({
                "title": f"Renew {len(expiring)} Expiring Permit(s)",
                "impact": "High",
                "savings": "Avoid shutdown",
            })
        # Always add smart meters as a baseline recommendation
        recommendations.append({
            "title": "Install Smart Meters",
            "impact": "Medium",
            "savings": "10-15%",
        })

        return {
            "source": "mongodb",
            "generated_at": datetime.utcnow().isoformat(),
            "has_data": usage["has_data"],
            "summary_cards": summary_cards,
            "facility_breakdown": facility_comparison,
            "insights": insights,
            "recommendations": recommendations,
            "compliance": {
                "rate": compliance_rate,
                "tests": f"{passed_tests}/{total_tests}",
                "violations": compliance.get("violation_count", 0),
                "expiring_permits": len(expiring),
            },
            "suppliers": {
                "total": supplier_count,
                "high_risk": high_risk_count,
            },
        }

    async def get_full_summary(self, user_id: str = "demo") -> Dict:
        dashboard = await self.get_dashboard_report(user_id)
        efficiency = await self.efficiency_agent.get_opportunities(user_id)
        return {
            "dashboard": dashboard,
            "efficiency": efficiency,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def get_trends_report(self, user_id: str = "demo") -> Dict:
        bills = await self.data_agent.get_utility_bills(user_id)
        meters = await self.data_agent.get_meter_data(user_id)

        # Group bills by month
        monthly: Dict[str, Dict] = {}
        for b in bills:
            period = b.get("billing_period_start") or b.get("period_start") or b.get("date", "")
            if period:
                month = str(period)[:7]  # "YYYY-MM"
            else:
                month = "Unknown"
            if month not in monthly:
                monthly[month] = {"volume": 0, "cost": 0, "facility": b.get("facility_name", "")}
            monthly[month]["volume"] += b.get("water_volume_gallons", 0)
            monthly[month]["cost"] += b.get("total_cost", 0)

        sorted_months = sorted(monthly.items())
        volumes = [v["volume"] for _, v in sorted_months]
        avg = round(sum(volumes) / len(volumes), 0) if volumes else 0
        peak_month, peak_val = max(sorted_months, key=lambda x: x[1]["volume"], default=("N/A", {"volume": 0}))
        low_month, low_val = min(sorted_months, key=lambda x: x[1]["volume"], default=("N/A", {"volume": 0}))

        trend_data = [
            {"month": m, "volume_gallons": v["volume"], "cost_usd": round(v["cost"], 2)}
            for m, v in sorted_months
        ]

        # Also include meter readings grouped by month
        meter_monthly: Dict[str, float] = {}
        for m in meters:
            date = str(m.get("reading_date") or m.get("date", ""))[:7]
            if date:
                meter_monthly[date] = meter_monthly.get(date, 0) + m.get("consumption", 0)

        return {
            "has_data": len(trend_data) > 0,
            "monthly_trends": trend_data,
            "meter_monthly": [{"month": k, "consumption": v} for k, v in sorted(meter_monthly.items())],
            "stats": {
                "average_monthly_gallons": avg,
                "peak_month": peak_month,
                "peak_volume": peak_val["volume"],
                "lowest_month": low_month,
                "lowest_volume": low_val["volume"],
                "months_tracked": len(sorted_months),
            },
            "summary": f"Tracked {len(sorted_months)} months. Average: {avg:,.0f} gal/month. Peak: {peak_month} ({peak_val['volume']:,} gal).",
        }

    async def get_water_balance(self, user_id: str = "demo") -> Dict:
        bills = await self.data_agent.get_utility_bills(user_id)
        meters = await self.data_agent.get_meter_data(user_id)

        total_withdrawal = sum(b.get("water_volume_gallons", 0) for b in bills)
        total_discharge = sum(b.get("wastewater_volume_gallons", b.get("discharge_volume_gallons", 0)) for b in bills)
        total_consumption = total_withdrawal - total_discharge if total_withdrawal > total_discharge else 0

        # Source breakdown from bills
        sources: Dict[str, float] = {}
        for b in bills:
            src = b.get("water_source", "Municipal")
            sources[src] = sources.get(src, 0) + b.get("water_volume_gallons", 0)

        # Use breakdown from meters
        uses: Dict[str, float] = {}
        for m in meters:
            loc = m.get("location", m.get("meter_id", "General"))
            uses[loc] = uses.get(loc, 0) + m.get("consumption", 0)

        source_list = [
            {"source": k, "volume": v, "percentage": round(v / total_withdrawal * 100, 1) if total_withdrawal else 0}
            for k, v in sources.items()
        ]
        use_list = [
            {"use": k, "volume": v, "percentage": round(v / total_withdrawal * 100, 1) if total_withdrawal else 0}
            for k, v in sorted(uses.items(), key=lambda x: -x[1])
        ]

        return {
            "has_data": total_withdrawal > 0,
            "total_withdrawal_gallons": total_withdrawal,
            "total_discharge_gallons": total_discharge,
            "total_consumption_gallons": total_consumption,
            "consumption_rate_pct": round(total_consumption / total_withdrawal * 100, 1) if total_withdrawal else 0,
            "sources": source_list,
            "uses": use_list,
            "summary": f"Total withdrawal: {total_withdrawal:,} gal. Consumption: {total_consumption:,} gal ({round(total_consumption/total_withdrawal*100,1) if total_withdrawal else 0}%). Discharge: {total_discharge:,} gal.",
        }

    async def get_pollutant_levels(self, user_id: str = "demo") -> Dict:
        reports = await self.data_agent.get_discharge_reports(user_id)

        all_results = []
        permits_checked = []
        for report in reports:
            for permit in report.get("permits", []):
                permit_id = permit.get("permit_id", permit.get("permit_number", ""))
                permits_checked.append(permit_id)
                for param in permit.get("parameters", []):
                    all_results.append({
                        "permit": permit_id,
                        "parameter": param.get("parameter", param.get("parameter_name", param.get("name", ""))),
                        "value": param.get("sample_value", param.get("measured_value", param.get("value", ""))),
                        "limit": param.get("limit_value", param.get("limit", "")),
                        "unit": param.get("limit_unit", param.get("unit", "mg/L")),
                        "status": param.get("compliance_status", "pass"),
                        "date": param.get("sample_date", report.get("report_date", "")),
                    })

        passed = sum(1 for r in all_results if r["status"] == "pass")
        failed = sum(1 for r in all_results if r["status"] != "pass")

        return {
            "has_data": len(all_results) > 0,
            "permits_checked": list(set(permits_checked)),
            "total_parameters": len(all_results),
            "passed": passed,
            "failed": failed,
            "compliance_rate": round(passed / len(all_results) * 100, 1) if all_results else 100,
            "results": all_results,
            "summary": f"{len(all_results)} parameters tested across {len(set(permits_checked))} permit(s). {passed} passed, {failed} failed.",
        }

    async def get_cost_analysis(self, user_id: str = "demo") -> Dict:
        bills = await self.data_agent.get_utility_bills(user_id)

        total_cost = sum(b.get("total_cost", 0) for b in bills)
        total_volume = sum(b.get("water_volume_gallons", 0) for b in bills)

        # Cost by facility
        by_facility: Dict[str, Dict] = {}
        for b in bills:
            name = b.get("facility_name", b.get("facility_id", "Unknown"))
            if name not in by_facility:
                by_facility[name] = {"cost": 0, "volume": 0}
            by_facility[name]["cost"] += b.get("total_cost", 0)
            by_facility[name]["volume"] += b.get("water_volume_gallons", 0)

        facility_costs = sorted(
            [
                {
                    "facility": k,
                    "cost_usd": round(v["cost"], 2),
                    "volume_gallons": v["volume"],
                    "cost_per_1000_gal": round(v["cost"] / v["volume"] * 1000, 2) if v["volume"] else 0,
                    "percentage": round(v["cost"] / total_cost * 100, 1) if total_cost else 0,
                }
                for k, v in by_facility.items()
            ],
            key=lambda x: -x["cost_usd"],
        )

        # Cost by month
        monthly_cost: Dict[str, float] = {}
        for b in bills:
            period = str(b.get("billing_period_start") or b.get("date", ""))[:7]
            if period:
                monthly_cost[period] = monthly_cost.get(period, 0) + b.get("total_cost", 0)

        return {
            "has_data": total_cost > 0,
            "total_cost_usd": round(total_cost, 2),
            "total_volume_gallons": total_volume,
            "avg_cost_per_1000_gal": round(total_cost / total_volume * 1000, 2) if total_volume else 0,
            "by_facility": facility_costs,
            "monthly_cost": [{"month": k, "cost_usd": round(v, 2)} for k, v in sorted(monthly_cost.items())],
            "summary": f"Total cost: ${total_cost:,.0f}. Average rate: ${round(total_cost/total_volume*1000,2) if total_volume else 0}/1,000 gal.",
        }

    async def get_water_footprint(self, user_id: str = "demo") -> Dict:
        """Calculate full water footprint: blue (freshwater), grey (pollution), supply chain."""
        from database import get_db
        db = get_db()

        bills = await self.data_agent.get_utility_bills(user_id)
        meters = await self.data_agent.get_meter_data(user_id)
        discharge_reports = await self.data_agent.get_discharge_reports(user_id)
        suppliers = await self.data_agent.get_suppliers(user_id)
        facilities = await self.data_agent.get_facilities(user_id)

        # --- Blue water (freshwater withdrawal) ---
        total_withdrawal = sum(b.get("water_volume_gallons", 0) for b in bills)

        # Discharge volume from reports
        total_discharge = 0
        for report in discharge_reports:
            for permit in report.get("permits", []):
                # Estimate discharge from parameters if no explicit volume
                pass
        # Fallback: estimate discharge as 60% of withdrawal (industry average)
        if total_discharge == 0 and total_withdrawal > 0:
            total_discharge = round(total_withdrawal * 0.60)

        blue_consumption = total_withdrawal - total_discharge  # consumed (evap + product)

        # By facility
        facility_footprint = {}
        for b in bills:
            name = b.get("facility_name", b.get("facility_id", "Unknown"))
            facility_footprint[name] = facility_footprint.get(name, 0) + b.get("water_volume_gallons", 0)

        # By source
        source_breakdown: Dict[str, float] = {}
        for b in bills:
            src = b.get("water_source", "Municipal")
            source_breakdown[src] = source_breakdown.get(src, 0) + b.get("water_volume_gallons", 0)

        # By use (from meters)
        use_breakdown: Dict[str, float] = {}
        for m in meters:
            mtype = m.get("meter_type", m.get("location", "General"))
            use_breakdown[mtype] = use_breakdown.get(mtype, 0) + m.get("consumption", 0)

        # --- Grey water (pollution dilution equivalent) ---
        # Estimate: 8% of withdrawal as grey water equivalent (standard WFN method)
        grey_water = round(total_withdrawal * 0.08)

        # --- Supply chain (indirect) footprint ---
        supply_chain_gal = 0
        supply_chain_breakdown = []
        if suppliers and suppliers.get("suppliers"):
            for s in suppliers["suppliers"]:
                intensity = s.get("water_intensity_factor", 0)  # gal per $1M spend
                spend = s.get("annual_spend_usd", 0)
                footprint = round(intensity * spend / 1_000_000)
                supply_chain_gal += footprint
                if footprint > 0:
                    supply_chain_breakdown.append({
                        "supplier": s.get("supplier_name", ""),
                        "category": s.get("material_category", s.get("product_category", "")),
                        "footprint_gallons": footprint,
                    })
            supply_chain_breakdown.sort(key=lambda x: -x["footprint_gallons"])

        total_footprint = total_withdrawal + supply_chain_gal

        # Water intensity metrics
        total_revenue = sum(f.get("annual_revenue_usd", 0) for f in facilities)
        total_employees = sum(f.get("employees", 0) for f in facilities)
        intensity_per_revenue = round(total_withdrawal / (total_revenue / 1_000_000), 0) if total_revenue else 0
        intensity_per_employee = round(total_withdrawal / total_employees, 0) if total_employees else 0

        return {
            "has_data": total_withdrawal > 0,
            "direct": {
                "total_withdrawal_gallons": total_withdrawal,
                "blue_water_gallons": total_withdrawal,
                "grey_water_gallons": grey_water,
                "consumption_gallons": blue_consumption,
                "discharge_gallons": total_discharge,
                "consumption_rate_pct": round(blue_consumption / total_withdrawal * 100, 1) if total_withdrawal else 0,
            },
            "by_facility": [
                {
                    "facility": k,
                    "gallons": v,
                    "percentage": round(v / total_withdrawal * 100, 1) if total_withdrawal else 0,
                }
                for k, v in sorted(facility_footprint.items(), key=lambda x: -x[1])
            ],
            "by_source": [
                {"source": k, "gallons": v, "percentage": round(v / total_withdrawal * 100, 1) if total_withdrawal else 0}
                for k, v in source_breakdown.items()
            ],
            "by_use": [
                {"use": k, "gallons": v, "percentage": round(v / total_withdrawal * 100, 1) if total_withdrawal else 0}
                for k, v in sorted(use_breakdown.items(), key=lambda x: -x[1])
            ],
            "supply_chain": {
                "total_gallons": supply_chain_gal,
                "breakdown": supply_chain_breakdown[:5],
            },
            "total_footprint_gallons": total_footprint,
            "intensity": {
                "per_million_revenue_gal": intensity_per_revenue,
                "per_employee_gal": intensity_per_employee,
            },
            "summary": (
                f"Direct footprint: {total_withdrawal:,} gal withdrawal, {blue_consumption:,} gal consumed. "
                f"Supply chain: {supply_chain_gal:,} gal. Total: {total_footprint:,} gal."
            ),
        }

    async def get_industry_comparison(self, user_id: str = "demo") -> Dict:
        """Compare water intensity to industry benchmarks by facility type."""
        footprint = await self.get_water_footprint(user_id)
        facilities = await self.data_agent.get_facilities(user_id)

        total_withdrawal = footprint["direct"]["total_withdrawal_gallons"]
        total_revenue = sum(f.get("annual_revenue_usd", 0) for f in facilities)
        total_employees = sum(f.get("employees", 0) for f in facilities)

        your_intensity = round(total_withdrawal / (total_revenue / 1_000_000), 0) if total_revenue else 0

        # Industry benchmarks (gal per $1M revenue) by facility type
        BENCHMARKS = {
            "Factory": {"average": 180000, "best_in_class": 90000, "label": "Manufacturing"},
            "Data Center": {"average": 120000, "best_in_class": 60000, "label": "Data Centers"},
            "Hotel": {"average": 95000, "best_in_class": 45000, "label": "Hospitality"},
            "Office": {"average": 40000, "best_in_class": 18000, "label": "Commercial Office"},
            "default": {"average": 150000, "best_in_class": 75000, "label": "Mixed Portfolio"},
        }

        # Pick benchmark based on dominant facility type
        types = [f.get("facility_type", "default") for f in facilities]
        dominant = max(set(types), key=types.count) if types else "default"
        bench = BENCHMARKS.get(dominant, BENCHMARKS["default"])

        vs_average = round((your_intensity - bench["average"]) / bench["average"] * 100, 1) if bench["average"] else 0
        vs_best = round((your_intensity - bench["best_in_class"]) / bench["best_in_class"] * 100, 1) if bench["best_in_class"] else 0

        # Per-facility breakdown
        bills = await self.data_agent.get_utility_bills(user_id)
        facility_volumes: Dict[str, float] = {}
        for b in bills:
            name = b.get("facility_name", b.get("facility_id", "Unknown"))
            facility_volumes[name] = facility_volumes.get(name, 0) + b.get("water_volume_gallons", 0)

        facility_comparisons = []
        for f in facilities:
            name = f.get("facility_name", f.get("facility_id", ""))
            rev = f.get("annual_revenue_usd", 0)
            vol = facility_volumes.get(name, 0)
            ftype = f.get("facility_type", "default")
            fb = BENCHMARKS.get(ftype, BENCHMARKS["default"])
            intensity = round(vol / (rev / 1_000_000), 0) if rev else 0
            facility_comparisons.append({
                "facility": name,
                "type": ftype,
                "intensity_gal_per_m_revenue": intensity,
                "benchmark_average": fb["average"],
                "benchmark_best": fb["best_in_class"],
                "vs_average_pct": round((intensity - fb["average"]) / fb["average"] * 100, 1) if fb["average"] else 0,
                "status": "above_average" if intensity > fb["average"] else ("below_average" if intensity < fb["best_in_class"] else "average"),
            })

        return {
            "has_data": total_withdrawal > 0,
            "your_intensity": your_intensity,
            "benchmark_label": bench["label"],
            "industry_average": bench["average"],
            "best_in_class": bench["best_in_class"],
            "vs_average_pct": vs_average,
            "vs_best_pct": vs_best,
            "performance": "above_average" if vs_average > 0 else ("best_in_class" if vs_best <= 0 else "below_average"),
            "gap_to_best_gallons": max(0, round((your_intensity - bench["best_in_class"]) * (total_revenue / 1_000_000), 0)) if total_revenue else 0,
            "facility_comparisons": facility_comparisons,
            "summary": f"Your intensity: {your_intensity:,.0f} gal/$1M vs industry avg {bench['average']:,.0f}. You are {abs(vs_average)}% {'above' if vs_average > 0 else 'below'} average.",
        }

    async def get_reduction_targets(self, user_id: str = "demo") -> Dict:
        """Generate 3 reduction target scenarios (20%, 30%, 40%) with initiative roadmaps."""
        footprint = await self.get_water_footprint(user_id)
        efficiency = await self.efficiency_agent.get_opportunities(user_id)

        baseline = footprint["direct"]["total_withdrawal_gallons"]
        total_cost = (await self.data_agent.get_usage_summary(user_id))["total_cost_usd"]
        cost_per_gal = total_cost / baseline if baseline else 0.003

        scenarios = []
        for pct, years, label in [(20, 2, "Basic"), (30, 3, "Moderate"), (40, 5, "Aggressive")]:
            target_gal = round(baseline * (1 - pct / 100))
            reduction_gal = baseline - target_gal
            cost_savings = round(reduction_gal * cost_per_gal, 0)

            # Pick initiatives that together hit the target
            initiatives = []
            cumulative = 0
            for opp in (efficiency.get("opportunities") or []):
                if cumulative >= reduction_gal:
                    break
                initiatives.append({
                    "name": opp["name"],
                    "savings_gal": opp["savings_gallons_year"],
                    "cost_usd": opp["implementation_cost"],
                    "payback_months": opp["payback_months"],
                })
                cumulative += opp["savings_gallons_year"]

            scenarios.append({
                "label": label,
                "reduction_pct": pct,
                "target_year": 2026 + years,
                "baseline_gallons": baseline,
                "target_gallons": target_gal,
                "reduction_gallons": reduction_gal,
                "annual_cost_savings_usd": cost_savings,
                "initiatives": initiatives,
                "achievable": cumulative >= reduction_gal,
            })

        return {
            "has_data": baseline > 0,
            "baseline_gallons": baseline,
            "baseline_cost_usd": total_cost,
            "scenarios": scenarios,
            "summary": f"Baseline: {baseline:,} gal. Three reduction scenarios: 20%, 30%, 40%.",
        }

    async def get_footprint_hotspots(self, user_id: str = "demo") -> Dict:
        """Identify top water usage hotspots by facility, source, and use type."""
        footprint = await self.get_water_footprint(user_id)
        facilities = await self.data_agent.get_facilities(user_id)

        total = footprint["direct"]["total_withdrawal_gallons"]

        # Enrich by_facility with risk context
        facility_map = {f.get("facility_name", ""): f for f in facilities}
        hotspot_facilities = []
        for item in footprint.get("by_facility", []):
            f = facility_map.get(item["facility"], {})
            hotspot_facilities.append({
                **item,
                "facility_type": f.get("facility_type", ""),
                "city": f.get("address", {}).get("city", ""),
                "state": f.get("address", {}).get("state", ""),
                "is_hotspot": item["percentage"] > 50,
                "employees": f.get("employees", 0),
                "intensity_gal_per_employee": round(item["gallons"] / f.get("employees", 1), 0) if f.get("employees") else 0,
            })

        # Supply chain hotspots
        sc_hotspots = sorted(
            footprint.get("supply_chain", {}).get("breakdown", []),
            key=lambda x: -x["footprint_gallons"]
        )[:3]

        # Insights
        insights = []
        if hotspot_facilities:
            top = hotspot_facilities[0]
            if top["percentage"] > 70:
                insights.append({"type": "critical", "message": f"{top['facility']} accounts for {top['percentage']}% of total withdrawal — primary reduction target"})
            elif top["percentage"] > 50:
                insights.append({"type": "warning", "message": f"{top['facility']} uses over half ({top['percentage']}%) of total water"})

        if sc_hotspots:
            insights.append({"type": "info", "message": f"Top supply chain hotspot: {sc_hotspots[0]['supplier']} ({sc_hotspots[0]['category']}) — {sc_hotspots[0]['footprint_gallons']:,} gal"})

        grey = footprint["direct"]["grey_water_gallons"]
        if grey > total * 0.1:
            insights.append({"type": "warning", "message": f"Grey water equivalent {grey:,} gal — consider wastewater treatment upgrades"})

        return {
            "has_data": total > 0,
            "total_gallons": total,
            "by_facility": hotspot_facilities,
            "by_source": footprint.get("by_source", []),
            "supply_chain_hotspots": sc_hotspots,
            "insights": insights,
            "summary": f"Top hotspot: {hotspot_facilities[0]['facility']} ({hotspot_facilities[0]['percentage']}% of total)" if hotspot_facilities else "No hotspot data.",
        }

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = task.get("tool", "get_dashboard_report")
        params = task.get("params", {})
        return await self.run_tool(tool_name, **params)
