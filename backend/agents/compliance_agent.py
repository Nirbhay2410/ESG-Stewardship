"""
ComplianceAgent — reads discharge_reports from MongoDB and tracks permits,
compliance rates, upcoming deadlines, and violations.
"""
from datetime import datetime
from typing import Any, Dict, List
from database import get_db
from .base_agent import BaseAgent


class ComplianceAgent(BaseAgent):
    name = "compliance_agent"
    description = "Tracks permits, compliance rates, deadlines and violations from real DB data"

    def register_tools(self):
        self._register("get_compliance_summary", self.get_compliance_summary, "Overall compliance status from DB")
        self._register("get_expiring_permits", self.get_expiring_permits, "Permits expiring within N days")
        self._register("get_violations", self.get_violations, "List of failed compliance parameters")

    async def get_compliance_summary(self, user_id: str = "demo") -> Dict:
        db = get_db()
        docs = await db.discharge_reports.find({"user_id": user_id}, {"_id": 0}).to_list(length=None)

        if not docs:
            return {"has_data": False, "message": "No discharge reports uploaded yet."}

        all_permits = [p for doc in docs for p in doc.get("permits", [])]
        total_params = sum(p.get("total_parameters", 0) for p in all_permits)
        passed_params = sum(p.get("passed_parameters", 0) for p in all_permits)
        compliance_rate = round(passed_params / total_params * 100, 1) if total_params else 100

        violations = []
        for p in all_permits:
            for param in p.get("parameters", []):
                if param.get("compliance_status", "").lower() != "pass":
                    violations.append({
                        "permit_id": p.get("permit_id"),
                        "parameter": param.get("parameter"),
                        "sample_value": param.get("sample_value"),
                        "limit_value": param.get("limit_value"),
                        "sample_date": param.get("sample_date"),
                    })

        expiring = await self.get_expiring_permits(user_id=user_id, days_ahead=90)

        return {
            "has_data": True,
            "total_permits": len(all_permits),
            "total_parameters_tested": total_params,
            "passed_parameters": passed_params,
            "overall_compliance_rate": compliance_rate,
            "violations": violations,
            "violation_count": len(violations),
            "expiring_soon": expiring,
            "status": "Compliant" if compliance_rate == 100 else "Action Required",
            "permits": [
                {
                    "permit_id": p.get("permit_id"),
                    "permit_type": p.get("permit_type"),
                    "issuing_authority": p.get("issuing_authority"),
                    "outfall_id": p.get("outfall_id"),
                    "lab_name": p.get("lab_name"),
                    "effective_date": p.get("effective_date"),
                    "expiration_date": p.get("expiration_date"),
                    "total_parameters": p.get("total_parameters", 0),
                    "passed_parameters": p.get("passed_parameters", 0),
                    "compliance_rate": p.get("compliance_rate", 100),
                }
                for p in all_permits
            ],
        }

    async def get_expiring_permits(self, user_id: str = "demo", days_ahead: int = 90) -> List[Dict]:
        db = get_db()
        docs = await db.discharge_reports.find({"user_id": user_id}, {"_id": 0}).to_list(length=None)
        all_permits = [p for doc in docs for p in doc.get("permits", [])]

        expiring = []
        today = datetime.utcnow()
        for p in all_permits:
            exp_str = p.get("expiration_date", "")
            if not exp_str or exp_str == "nan":
                continue
            try:
                exp_date = datetime.strptime(str(exp_str)[:10], "%Y-%m-%d")
                days_left = (exp_date - today).days
                if 0 <= days_left <= days_ahead:
                    expiring.append({
                        "permit_id": p.get("permit_id"),
                        "permit_type": p.get("permit_type"),
                        "expiration_date": exp_str,
                        "days_until_expiry": days_left,
                        "priority": "high" if days_left <= 30 else "medium",
                    })
            except (ValueError, TypeError):
                continue

        return sorted(expiring, key=lambda x: x["days_until_expiry"])

    async def get_violations(self, user_id: str = "demo") -> List[Dict]:
        summary = await self.get_compliance_summary(user_id)
        return summary.get("violations", [])

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = task.get("tool", "get_compliance_summary")
        params = task.get("params", {})
        return await self.run_tool(tool_name, **params)
