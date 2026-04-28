"""
DataAgent — owns all MongoDB queries.
Provides tools for fetching and aggregating real data from the DB.
"""
from typing import Any, Dict, List, Optional
from database import get_db
from .base_agent import BaseAgent


class DataAgent(BaseAgent):
    name = "data_agent"
    description = "Fetches and aggregates real water data from MongoDB"

    def register_tools(self):
        self._register("get_facilities", self.get_facilities, "Get all facilities for a user")
        self._register("get_utility_bills", self.get_utility_bills, "Get utility bills from DB")
        self._register("get_meter_data", self.get_meter_data, "Get meter readings from DB")
        self._register("get_discharge_reports", self.get_discharge_reports, "Get discharge/permit reports")
        self._register("get_suppliers", self.get_suppliers, "Get supplier list with water intensity")
        self._register("get_usage_summary", self.get_usage_summary, "Aggregate total usage and cost")

    async def get_facilities(self, user_id: str = "demo") -> List[Dict]:
        db = get_db()
        return await db.facilities.find({"user_id": user_id}, {"_id": 0}).to_list(length=None)

    async def get_utility_bills(self, user_id: str = "demo", facility_id: Optional[str] = None) -> List[Dict]:
        db = get_db()
        query: Dict[str, Any] = {"user_id": user_id}
        if facility_id:
            query["facility_id"] = facility_id
        return await db.utility_bills.find(query, {"_id": 0}).to_list(length=None)

    async def get_meter_data(self, user_id: str = "demo", facility_id: Optional[str] = None) -> List[Dict]:
        db = get_db()
        query: Dict[str, Any] = {"user_id": user_id}
        if facility_id:
            query["facility_id"] = facility_id
        return await db.meter_data.find(query, {"_id": 0}).to_list(length=None)

    async def get_discharge_reports(self, user_id: str = "demo") -> List[Dict]:
        db = get_db()
        return await db.discharge_reports.find({"user_id": user_id}, {"_id": 0}).to_list(length=None)

    async def get_suppliers(self, user_id: str = "demo") -> Optional[Dict]:
        db = get_db()
        return await db.suppliers.find_one({"user_id": user_id}, {"_id": 0})

    async def get_usage_summary(self, user_id: str = "demo") -> Dict:
        bills = await self.get_utility_bills(user_id)
        meters = await self.get_meter_data(user_id)

        total_volume = sum(b.get("water_volume_gallons", 0) for b in bills)
        total_cost = sum(b.get("total_cost", 0) for b in bills)
        total_meter_consumption = sum(m.get("consumption", 0) for m in meters)

        facility_breakdown = {}
        for b in bills:
            name = b.get("facility_name", b.get("facility_id", "Unknown"))
            facility_breakdown[name] = facility_breakdown.get(name, 0) + b.get("water_volume_gallons", 0)

        return {
            "total_volume_gallons": total_volume,
            "total_cost_usd": round(total_cost, 2),
            "avg_cost_per_1000_gal": round(total_cost / total_volume * 1000, 2) if total_volume else 0,
            "bill_count": len(bills),
            "meter_count": len(meters),
            "total_meter_consumption": total_meter_consumption,
            "facility_breakdown": facility_breakdown,
            "has_data": total_volume > 0 or total_meter_consumption > 0,
        }

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = task.get("tool")
        params = task.get("params", {})
        if not tool_name:
            # Default: return full usage summary
            return await self.get_usage_summary(params.get("user_id", "demo"))
        return await self.run_tool(tool_name, **params)
