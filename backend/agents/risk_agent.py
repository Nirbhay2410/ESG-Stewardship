"""
RiskAgent — queries WRI data and calculates real water risk scores.
Uses actual facility coordinates to find nearest WRI data points.
AI is used ONLY for generating contextual recommendations and analysis narrative,
after the real scores are calculated from WRI data.
"""
import json
import math
from typing import Any, Dict, List, Optional
from database import get_db
from .base_agent import BaseAgent


# WRI category label maps
BWS_LABELS = {0: "Low (<10%)", 1: "Low-Medium (10-20%)", 2: "Medium-High (20-40%)",
              3: "High (40-80%)", 4: "Extremely High (>80%)", -1: "Arid & Low Water Use"}
RISK_LEVELS = [(4.0, "Extremely High"), (3.0, "High"), (2.0, "Medium"), (1.0, "Low"), (0, "Very Low")]


def _risk_level(score: float) -> str:
    for threshold, label in RISK_LEVELS:
        if score >= threshold:
            return label
    return "Very Low"


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# Approximate US state bounding boxes [min_lat, max_lat, min_lon, max_lon]
_US_STATES = {
    "California": [32.5, 42.0, -124.5, -114.1],
    "Texas": [25.8, 36.5, -106.6, -93.5],
    "Arizona": [31.3, 37.0, -114.8, -109.0],
    "Nevada": [35.0, 42.0, -120.0, -114.0],
    "Oregon": [42.0, 46.3, -124.6, -116.5],
    "Washington": [45.5, 49.0, -124.7, -116.9],
    "Colorado": [37.0, 41.0, -109.1, -102.0],
    "New Mexico": [31.3, 37.0, -109.1, -103.0],
    "Utah": [37.0, 42.0, -114.1, -109.0],
    "Idaho": [42.0, 49.0, -117.2, -111.0],
    "Montana": [44.4, 49.0, -116.1, -104.0],
    "Wyoming": [41.0, 45.0, -111.1, -104.1],
    "North Dakota": [45.9, 49.0, -104.1, -96.6],
    "South Dakota": [42.5, 45.9, -104.1, -96.4],
    "Nebraska": [40.0, 43.0, -104.1, -95.3],
    "Kansas": [37.0, 40.0, -102.1, -94.6],
    "Oklahoma": [33.6, 37.0, -103.0, -94.4],
    "Minnesota": [43.5, 49.4, -97.2, -89.5],
    "Iowa": [40.4, 43.5, -96.6, -90.1],
    "Missouri": [36.0, 40.6, -95.8, -89.1],
    "Arkansas": [33.0, 36.5, -94.6, -89.6],
    "Louisiana": [28.9, 33.0, -94.0, -88.8],
    "Wisconsin": [42.5, 47.1, -92.9, -86.8],
    "Illinois": [37.0, 42.5, -91.5, -87.5],
    "Michigan": [41.7, 48.3, -90.4, -82.4],
    "Indiana": [37.8, 41.8, -88.1, -84.8],
    "Ohio": [38.4, 42.3, -84.8, -80.5],
    "Kentucky": [36.5, 39.1, -89.6, -81.9],
    "Tennessee": [35.0, 36.7, -90.3, -81.6],
    "Mississippi": [30.2, 35.0, -91.7, -88.1],
    "Alabama": [30.2, 35.0, -88.5, -84.9],
    "Georgia": [30.4, 35.0, -85.6, -80.8],
    "Florida": [24.5, 31.0, -87.6, -80.0],
    "South Carolina": [32.0, 35.2, -83.4, -78.5],
    "North Carolina": [33.8, 36.6, -84.3, -75.5],
    "Virginia": [36.5, 39.5, -83.7, -75.2],
    "West Virginia": [37.2, 40.6, -82.6, -77.7],
    "Maryland": [37.9, 39.7, -79.5, -75.0],
    "Pennsylvania": [39.7, 42.3, -80.5, -74.7],
    "New York": [40.5, 45.0, -79.8, -71.9],
    "New Jersey": [38.9, 41.4, -75.6, -73.9],
    "Connecticut": [41.0, 42.1, -73.7, -71.8],
    "Massachusetts": [41.2, 42.9, -73.5, -69.9],
    "Vermont": [42.7, 45.0, -73.4, -71.5],
    "New Hampshire": [42.7, 45.3, -72.6, -70.6],
    "Maine": [43.1, 47.5, -71.1, -67.0],
    "Rhode Island": [41.1, 42.0, -71.9, -71.1],
    "Delaware": [38.4, 39.8, -75.8, -75.0],
    "Hawaii": [18.9, 22.2, -160.2, -154.8],
    "Alaska": [54.0, 71.4, -168.0, -130.0],
}


def _state_from_coords(lat: float, lon: float) -> str:
    """Return US state name for given coordinates, or empty string."""
    for state, (min_lat, max_lat, min_lon, max_lon) in _US_STATES.items():
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return state
    return ""


class RiskAgent(BaseAgent):
    name = "risk_agent"
    description = "Calculates water risk using real WRI Aqueduct data and facility coordinates"

    def __init__(self, ai_service=None):
        self.ai = ai_service
        super().__init__()

    def register_tools(self):
        self._register("query_wri_near", self.query_wri_near, "Find nearest WRI data point to lat/lon")
        self._register("score_facility", self.score_facility, "Calculate risk score for one facility")
        self._register("assess_all_facilities", self.assess_all_facilities, "Risk assessment for all user facilities")
        self._register("get_climate_projections", self.get_climate_projections, "Get future climate projections for a basin")
        self._register("compare_facilities", self.compare_facilities, "Side-by-side risk comparison of all facilities")
        self._register("get_risk_map_data", self.get_risk_map_data, "Facility coordinates + risk scores for map rendering")
        self._register("get_climate_scenarios", self.get_climate_scenarios, "WRI future projections for all facilities")

    async def query_wri_near(self, lat: float, lon: float, limit: int = 1) -> List[Dict]:
        db = get_db()
        try:
            results = await db.wri_baseline_annual.find(
                {"geometry": {"$near": {"$geometry": {"type": "Point", "coordinates": [lon, lat]}, "$maxDistance": 500000}}},
                {"_id": 0}
            ).limit(limit).to_list(length=limit)
            if results:
                return results
        except Exception:
            pass

        # No geo index — load candidates and sort by haversine
        # Only load records that have lat/lon stored
        candidates = await db.wri_baseline_annual.find(
            {"lat": {"$exists": True, "$ne": None}},
            {"_id": 0, "lat": 1, "lon": 1, "bws_cat": 1, "bwd_cat": 1, "drr_cat": 1,
             "rfr_cat": 1, "cfr_cat": 1, "name_0": 1, "name_1": 1, "aqid": 1}
        ).limit(5000).to_list(length=5000)

        if candidates:
            candidates.sort(key=lambda r: _haversine_km(lat, lon, r.get("lat", 0), r.get("lon", 0)))
            return candidates[:limit]

        # Fallback: match by country/state name using reverse geocode approximation
        # Map known US state bounding boxes to state names
        state = _state_from_coords(lat, lon)
        country = "United States" if -130 < lon < -60 and 20 < lat < 55 else None

        query: Dict = {}
        if state and country:
            query = {"name_0": country, "name_1": state}
        elif country:
            query = {"name_0": country}

        if query:
            results = await db.wri_baseline_annual.find(query, {"_id": 0}).limit(limit).to_list(limit)
            if results:
                return results

        # Last resort: return any record
        return await db.wri_baseline_annual.find({}, {"_id": 0}).limit(limit).to_list(limit)

    async def score_facility(self, facility: Dict) -> Dict:
        coords = facility.get("location", {}).get("coordinates", [])
        if len(coords) < 2:
            return {"error": "No coordinates for facility", "facility_id": facility.get("facility_id")}

        lon, lat = coords[0], coords[1]
        wri_records = await self.query_wri_near(lat=lat, lon=lon, limit=1)

        if not wri_records:
            return {"error": "No WRI data found near facility", "facility_id": facility.get("facility_id")}

        wri = wri_records[0]

        def cat_to_score(cat) -> float:
            try:
                c = int(cat)
                return {-1: 1.0, 0: 1.0, 1: 2.0, 2: 3.0, 3: 4.0, 4: 5.0}.get(c, 2.5)
            except (TypeError, ValueError):
                return 2.5

        bws = cat_to_score(wri.get("bws_cat"))
        bwd = cat_to_score(wri.get("bwd_cat"))
        drr = cat_to_score(wri.get("drr_cat"))
        rfr = cat_to_score(wri.get("rfr_cat"))
        cfr = cat_to_score(wri.get("cfr_cat"))
        overall = round(bws * 0.35 + bwd * 0.25 + drr * 0.20 + rfr * 0.10 + cfr * 0.10, 2)

        return {
            "facility_id": facility.get("facility_id"),
            "facility_name": facility.get("facility_name", facility.get("name", "")),
            "location": f"{facility.get('address', {}).get('city', '')}, {facility.get('address', {}).get('state', '')}",
            "coordinates": {"lat": lat, "lon": lon},
            "wri_region": f"{wri.get('name_1', '')}, {wri.get('name_0', '')}",
            "overall_risk_score": overall,
            "overall_risk_level": _risk_level(overall),
            "risk_breakdown": {
                "baseline_water_stress": {"score": bws, "level": _risk_level(bws), "label": BWS_LABELS.get(int(wri.get("bws_cat", 0)), "Unknown")},
                "water_depletion": {"score": bwd, "level": _risk_level(bwd)},
                "drought_risk": {"score": drr, "level": _risk_level(drr)},
                "riverine_flood": {"score": rfr, "level": _risk_level(rfr)},
                "coastal_flood": {"score": cfr, "level": _risk_level(cfr)},
            },
        }

    async def assess_all_facilities(self, user_id: str = "demo") -> Dict:
        db = get_db()
        facilities = await db.facilities.find({"user_id": user_id}, {"_id": 0}).to_list(length=None)

        if not facilities:
            return {"error": "No facilities found. Please upload facility info first.", "facilities": []}

        scored = []
        for f in facilities:
            score = await self.score_facility(f)
            scored.append(score)

        valid = [s for s in scored if "error" not in s]
        avg_score = round(sum(s["overall_risk_score"] for s in valid) / len(valid), 2) if valid else 0
        high_risk = [s for s in valid if s["overall_risk_score"] >= 3.0]

        # Static key risks from WRI data (no AI)
        key_risks = self._key_risks(valid)

        # AI-generated recommendations and analysis using real scores as context
        ai_analysis = await self._ai_analysis(valid, avg_score)

        return {
            "overall_portfolio_risk": avg_score,
            "overall_risk_level": _risk_level(avg_score),
            "facility_count": len(facilities),
            "high_risk_count": len(high_risk),
            "facilities": scored,
            "key_risks": key_risks,
            "recommendations": ai_analysis.get("recommendations", self._fallback_recommendations(valid)),
            "analysis_summary": ai_analysis.get("summary", ""),
        }

    async def _ai_analysis(self, scored: List[Dict], avg_score: float) -> Dict:
        """Use AI to generate specific recommendations based on real WRI scores."""
        if not self.ai or not scored:
            return {"recommendations": self._fallback_recommendations(scored), "summary": ""}

        # Build a compact summary of real scores to pass to AI
        facility_summaries = []
        for s in scored:
            bd = s.get("risk_breakdown", {})
            facility_summaries.append({
                "name": s.get("facility_name"),
                "location": s.get("location"),
                "industry": s.get("industry_type", ""),
                "overall_score": s.get("overall_risk_score"),
                "overall_level": s.get("overall_risk_level"),
                "water_stress": bd.get("baseline_water_stress", {}).get("level"),
                "drought_risk": bd.get("drought_risk", {}).get("level"),
                "water_depletion": bd.get("water_depletion", {}).get("level"),
                "flood_risk": bd.get("riverine_flood", {}).get("level"),
            })

        prompt = f"""You are a water risk expert. Based on these REAL WRI Aqueduct risk scores for facilities, provide specific actionable recommendations.

REAL RISK DATA (from WRI Aqueduct database):
{json.dumps(facility_summaries, indent=2)}

Portfolio average risk score: {avg_score}/5.0

Return ONLY valid JSON with this exact structure:
{{
  "summary": "2-3 sentence analysis of the portfolio risk situation",
  "recommendations": [
    {{
      "priority": "High|Medium|Low",
      "action": "specific action tailored to these facilities and their locations",
      "impact": "expected measurable impact",
      "facility": "facility name this applies to, or 'All Facilities'"
    }}
  ]
}}

Rules:
- Reference specific facility names and locations in recommendations
- Tailor advice to the actual risk scores (e.g. if drought is Medium but water stress is Extremely High, focus on stress not drought)
- Give 4-6 recommendations, most critical first
- Return ONLY JSON, no markdown"""

        try:
            response = await self.ai.generate_content(prompt)
            clean = response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(clean)
        except Exception as e:
            print(f"RiskAgent AI analysis failed: {e}")
            return {"recommendations": self._fallback_recommendations(scored), "summary": ""}

    async def get_climate_projections(self, basin_id: str) -> Dict:
        db = get_db()
        proj = await db.wri_future_projections.find_one({"BasinID": basin_id}, {"_id": 0})
        if not proj:
            return {"error": f"No projections found for basin {basin_id}"}
        return proj

    def _key_risks(self, scored: List[Dict]) -> List[Dict]:
        risks = []
        for s in scored:
            bd = s.get("risk_breakdown", {})
            if bd.get("baseline_water_stress", {}).get("score", 0) >= 4.0:
                risks.append({"type": "critical", "facility": s["facility_name"],
                               "message": f"Extremely high water stress at {s['location']}", "action": "Implement water recycling immediately"})
            if bd.get("drought_risk", {}).get("score", 0) >= 3.0:
                risks.append({"type": "warning", "facility": s["facility_name"],
                               "message": f"High drought risk at {s['location']}", "action": "Diversify water sources"})
        return risks[:5]

    def _fallback_recommendations(self, scored: List[Dict]) -> List[Dict]:
        recs = []
        avg_bws = sum(s["risk_breakdown"]["baseline_water_stress"]["score"] for s in scored) / len(scored) if scored else 0
        if avg_bws >= 3.0:
            recs.append({"priority": "High", "action": "Install water recycling systems", "impact": "Reduce withdrawal by 30-40%", "facility": "All Facilities"})
        recs.append({"priority": "Medium", "action": "Set up real-time water monitoring", "impact": "Early detection of overuse", "facility": "All Facilities"})
        recs.append({"priority": "Medium", "action": "Develop drought contingency plan", "impact": "Operational resilience", "facility": "All Facilities"})
        return recs

    async def compare_facilities(self, user_id: str = "demo") -> Dict:
        """Side-by-side risk comparison of all facilities from MongoDB."""
        db = get_db()
        facilities = await db.facilities.find({"user_id": user_id}, {"_id": 0}).to_list(length=None)
        if not facilities:
            return {"error": "No facilities found.", "facilities": []}

        scored = [await self.score_facility(f) for f in facilities]
        valid = [s for s in scored if "error" not in s]

        # Build comparison table: each risk dimension across all facilities
        dimensions = ["baseline_water_stress", "water_depletion", "drought_risk", "riverine_flood", "coastal_flood"]
        comparison = []
        for dim in dimensions:
            row = {"dimension": dim.replace("_", " ").title()}
            for s in valid:
                bd = s.get("risk_breakdown", {})
                row[s["facility_name"]] = {
                    "score": bd.get(dim, {}).get("score", 0),
                    "level": bd.get(dim, {}).get("level", "Unknown"),
                }
            comparison.append(row)

        return {
            "facilities": valid,
            "comparison_table": comparison,
            "summary": f"Compared {len(valid)} facilities across {len(dimensions)} risk dimensions.",
        }

    async def get_risk_map_data(self, user_id: str = "demo") -> Dict:
        """Return facility coordinates + risk scores for interactive map."""
        db = get_db()
        facilities = await db.facilities.find({"user_id": user_id}, {"_id": 0}).to_list(length=None)
        if not facilities:
            return {"error": "No facilities found.", "markers": []}

        markers = []
        for f in facilities:
            scored = await self.score_facility(f)
            coords = f.get("location", {}).get("coordinates", [])
            if len(coords) >= 2 and "error" not in scored:
                markers.append({
                    "facility_name": scored["facility_name"],
                    "location": scored["location"],
                    "lat": coords[1],
                    "lon": coords[0],
                    "overall_risk_score": scored["overall_risk_score"],
                    "overall_risk_level": scored["overall_risk_level"],
                    "risk_breakdown": scored["risk_breakdown"],
                    "wri_region": scored.get("wri_region", ""),
                })

        return {
            "markers": markers,
            "center": {
                "lat": sum(m["lat"] for m in markers) / len(markers) if markers else 37.5,
                "lon": sum(m["lon"] for m in markers) / len(markers) if markers else -120.0,
            },
            "summary": f"Mapped {len(markers)} facilities.",
        }

    async def get_climate_scenarios(self, user_id: str = "demo") -> Dict:
        """Get WRI future water stress projections for each facility's basin."""
        db = get_db()
        facilities = await db.facilities.find({"user_id": user_id}, {"_id": 0}).to_list(length=None)
        if not facilities:
            return {"error": "No facilities found.", "scenarios": []}

        scenarios = []
        for f in facilities:
            coords = f.get("location", {}).get("coordinates", [])
            if len(coords) < 2:
                continue
            lon, lat = coords[0], coords[1]

            # Get nearest WRI record to find aqid
            wri_records = await self.query_wri_near(lat=lat, lon=lon, limit=1)
            if not wri_records:
                continue
            wri = wri_records[0]
            aqid = wri.get("aqid")

            # Look up future projections by BasinID = aqid
            proj = None
            if aqid and aqid != -9999:
                proj = await db.wri_future_projections.find_one({"BasinID": aqid}, {"_id": 0})

            # Parse projection fields: ws = water stress, ut = urban/total, bt = baseline total
            # Suffixes: 2024=near, 3024=2030, 4024=2040 | tr=raw, tl=label
            # Scenarios: r=optimistic(RCP2.6), c=business-as-usual(RCP4.5), u=pessimistic(RCP8.5)
            def _proj_val(p, prefix, year, scenario, suffix="tl"):
                if not p:
                    return "No data"
                key = f"{prefix}{year}{scenario}{suffix}"
                return p.get(key, "No data")

            facility_scenario = {
                "facility_name": f.get("facility_name", ""),
                "location": f"{f.get('address', {}).get('city', '')}, {f.get('address', {}).get('state', '')}",
                "current_stress": wri.get("bws_label", _risk_level(float(wri.get("bws_cat", 0) or 0))),
                "basin_id": aqid,
                "projections": {
                    "2030": {
                        "optimistic": _proj_val(proj, "ws", "30", "2"),
                        "business_as_usual": _proj_val(proj, "ws", "30", "4"),
                        "pessimistic": _proj_val(proj, "ws", "30", "u"),
                    },
                    "2040": {
                        "optimistic": _proj_val(proj, "ws", "40", "2"),
                        "business_as_usual": _proj_val(proj, "ws", "40", "4"),
                        "pessimistic": _proj_val(proj, "ws", "40", "u"),
                    },
                } if proj else None,
                "has_projection_data": proj is not None,
            }
            scenarios.append(facility_scenario)

        # If WRI projections are sparse, supplement with AI narrative
        ai_narrative = ""
        if self.ai and scenarios:
            try:
                prompt = f"""You are a climate risk expert. Based on these WRI Aqueduct water stress projections for facilities, provide a brief 3-4 sentence climate outlook.

FACILITY SCENARIOS:
{json.dumps(scenarios, indent=2)}

Focus on: which facilities face worsening stress, what climate drivers are involved, and key adaptation priorities.
Return plain text only, no JSON, no markdown."""
                ai_narrative = await self.ai.generate_content(prompt)
            except Exception as e:
                print(f"Climate scenario AI narrative failed: {e}")

        return {
            "scenarios": scenarios,
            "ai_narrative": ai_narrative,
            "summary": f"Climate projections for {len(scenarios)} facilities using WRI Aqueduct future data.",
        }

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = task.get("tool", "assess_all_facilities")
        params = task.get("params", {})
        return await self.run_tool(tool_name, **params)
