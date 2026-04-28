"""
OpenRouter AI service — drop-in replacement for GeminiService.
Uses OpenAI-compatible API pointed at openrouter.ai.
Free model: nvidia/nemotron-3-super-120b-a12b:free (no rate limit issues)
"""
import asyncio
import os
import time
from typing import Any, Dict, Optional

from openai import AsyncOpenAI


class OpenRouterService:
    def __init__(self):
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set in backend/.env")

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        self.model = "nvidia/nemotron-3-super-120b-a12b:free"
        self._fallback_model = "meta-llama/llama-3.3-70b-instruct:free"
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def generate_content(self, prompt: str) -> str:
        """Generate a response. Compatible with GeminiService.generate_content()."""
        async with self._get_lock():
            for model in [self.model, self._fallback_model]:
                try:
                    response = await self.client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        extra_headers={
                            "HTTP-Referer": "http://localhost:3000",
                            "X-Title": "Water Stewardship Agent",
                        },
                    )
                    return response.choices[0].message.content or ""
                except Exception as e:
                    err = str(e)
                    if "404" in err or "not a valid model" in err or "No endpoints" in err:
                        print(f"Model {model} unavailable, trying fallback...")
                        continue
                    if "429" in err or "rate" in err.lower():
                        wait = 10
                        print(f"OpenRouter rate limit, waiting {wait}s")
                        await asyncio.sleep(wait)
                        continue
                    raise
            raise RuntimeError("All models failed")

    async def process_chat_message(
        self,
        user_message: str,
        session_id: str = None,
        conversation_id: str = None,
    ) -> Dict[str, Any]:
        """Process a chat message. Compatible with GeminiService.process_chat_message()."""
        try:
            prompt = f"""You are a Water Stewardship AI Assistant. You help users with:
1. Water usage analysis and optimization
2. Water risk assessment
3. Water efficiency recommendations
4. Compliance and regulatory guidance
5. Water stewardship strategy

User message: {user_message}

Provide a helpful, accurate, and conversational response about water stewardship.
Keep responses concise and actionable."""

            response_text = await self.generate_content(prompt)
            return {
                "success": True,
                "response": response_text,
                "model": self.model,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": "AI service error. Please try again.",
            }

    async def generate_mitigation_plan(
        self, facility_data: Dict, risk_data: Dict
    ) -> Dict[str, Any]:
        """Generate mitigation plan. Compatible with GeminiService.generate_mitigation_plan()."""
        import json
        try:
            # Pull real DB data
            real_data = await self._fetch_real_db_data()

            prompt = f"""You are a water stewardship expert. Generate a comprehensive water risk mitigation plan.

FACILITY DATA:
{json.dumps(facility_data or real_data.get("facilities"), indent=2)}

RISK ASSESSMENT:
{json.dumps(risk_data, indent=2)}

ACTUAL WATER USAGE:
{json.dumps(real_data.get("usage_summary"), indent=2)}

Return ONLY valid JSON with this structure:
{{
  "plan_name": "Water Risk Mitigation Strategy 2026",
  "created_date": "2026-03-14",
  "timeline": "12 months",
  "total_investment": <number>,
  "expected_savings": <number>,
  "roi_months": <number>,
  "phases": [{{"phase": 1, "name": "...", "duration": "...", "status": "ready", "actions": [{{"task": "...", "owner": "...", "deadline": "...", "cost": <number>}}]}}],
  "kpis": [{{"metric": "...", "baseline": "...", "target": "...", "reduction": "X%"}}],
  "risk_mitigation": [{{"risk": "...", "mitigation": "...", "impact": "High/Medium", "timeline": "..."}}]
}}"""

            response_text = await self.generate_content(prompt)
            clean = response_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return {"success": True, "mitigation_plan": json.loads(clean)}

        except json.JSONDecodeError as e:
            print(f"JSON parse error in mitigation plan: {e}")
            return {"success": False, "error": "Failed to parse AI response", "mitigation_plan": self._get_fallback_plan({})}
        except Exception as e:
            print(f"Mitigation plan error: {e}")
            return {"success": False, "error": str(e), "mitigation_plan": self._get_fallback_plan({})}

    async def _fetch_real_db_data(self) -> Dict:
        try:
            from database import get_db
            db = get_db()
            if db is None:
                return {}
            bills = await db.utility_bills.find({"user_id": "demo"}, {"_id": 0}).to_list(length=None)
            facilities = await db.facilities.find({"user_id": "demo"}, {"_id": 0}).to_list(length=None)
            total_volume = sum(b.get("water_volume_gallons", 0) for b in bills)
            total_cost = sum(b.get("total_cost", 0) for b in bills)
            return {
                "facilities": facilities,
                "usage_summary": {
                    "total_water_volume_gallons": total_volume,
                    "total_cost_usd": round(total_cost, 2),
                },
            }
        except Exception as e:
            print(f"Warning: could not fetch DB data: {e}")
            return {}

    def _get_fallback_plan(self, real_data: Dict) -> Dict:
        return {
            "plan_name": "Water Risk Mitigation Strategy 2026",
            "created_date": "2026-03-14",
            "timeline": "12 months",
            "total_investment": 450000,
            "expected_savings": 180000,
            "roi_months": 30,
            "phases": [],
            "kpis": [],
            "risk_mitigation": [],
        }
