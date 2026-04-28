from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json

from database import get_db
from agents.efficiency_agent import EfficiencyAgent

router = APIRouter()
_efficiency_agent = EfficiencyAgent()

@router.get("/dashboard")
async def get_dashboard_data(
    user_id: str = Query("anonymous"),
    timeframe: str = Query("monthly", regex="^(daily|weekly|monthly|yearly)$")
):
    """
    Get dashboard data for water overview
    """
    try:
        # Get user's facilities
        db = get_db()
        facilities = await db.facilities.find(
            {"user_id": user_id},
            {"_id": 0, "facility_id": 1, "name": 1, "location": 1, "facility_type": 1}
        ).to_list(100)
        
        # Get water data for facilities
        facility_ids = [f["facility_id"] for f in facilities]
        
        # Calculate timeframe
        end_date = datetime.utcnow()
        if timeframe == "daily":
            start_date = end_date - timedelta(days=1)
        elif timeframe == "weekly":
            start_date = end_date - timedelta(weeks=1)
        elif timeframe == "monthly":
            start_date = end_date - timedelta(days=30)
        else:  # yearly
            start_date = end_date - timedelta(days=365)
        
        # Get water usage data
        water_data = await db.water_data.find({
            "facility_id": {"$in": facility_ids},
            "timestamp": {"$gte": start_date, "$lte": end_date},
            "data_type": "water_usage"
        }).sort("timestamp", -1).to_list(1000)
        
        # Calculate summary metrics
        total_withdrawal = 0
        total_cost = 0
        total_discharge = 0
        high_stress_facilities = 0
        
        for facility in facilities:
            # Get facility water data
            facility_water_data = [d for d in water_data if d["facility_id"] == facility["facility_id"]]
            
            if facility_water_data:
                # Calculate facility metrics
                facility_withdrawal = sum(d.get("volume", 0) for d in facility_water_data)
                facility_cost = sum(d.get("cost", 0) for d in facility_water_data)
                facility_discharge = sum(d.get("discharge_volume", 0) for d in facility_water_data)
                
                total_withdrawal += facility_withdrawal
                total_cost += facility_cost
                total_discharge += facility_discharge
                
                # Check if facility is in high stress area
                risk_assessment = await db.risk_assessments.find_one(
                    {"facility_id": facility["facility_id"]},
                    sort=[("assessment_date", -1)]
                )
                
                if risk_assessment and risk_assessment.get("overall_risk_score", 0) >= 3.5:
                    high_stress_facilities += 1
        
        # Calculate water intensity (simulated)
        water_intensity = 12  # gal/$1000 revenue (simulated)
        
        # Calculate consumption rate
        consumption_rate = 0
        if total_withdrawal > 0:
            consumption_rate = ((total_withdrawal - total_discharge) / total_withdrawal) * 100
        
        # Prepare summary cards
        summary_cards = [
            {
                "title": "Total Withdrawal",
                "value": f"{total_withdrawal:,} gal",
                "period": timeframe,
                "icon": "💧",
                "trend": "+8%",  # Simulated trend
                "color": "blue"
            },
            {
                "title": "Total Cost",
                "value": f"${total_cost:,.0f}",
                "period": timeframe,
                "icon": "💰",
                "trend": "+5%",
                "color": "green"
            },
            {
                "title": "Consumption Rate",
                "value": f"{consumption_rate:.0f}%",
                "period": timeframe,
                "icon": "📉",
                "trend": "-2%",
                "color": "orange"
            },
            {
                "title": "Discharge",
                "value": f"{total_discharge:,} gal",
                "period": timeframe,
                "icon": "♻️",
                "trend": "+3%",
                "color": "purple"
            },
            {
                "title": "High-Stress Facilities",
                "value": f"{high_stress_facilities} of {len(facilities)}",
                "percentage": f"{(high_stress_facilities/len(facilities)*100 if facilities else 0):.0f}%",
                "icon": "🗺️",
                "color": "red"
            },
            {
                "title": "Water Intensity",
                "value": f"{water_intensity} gal/$1K revenue",
                "icon": "📊",
                "trend": "-5%",
                "color": "teal"
            }
        ]
        
        # Get recent activities
        recent_activities = await get_recent_activities(user_id)
        
        # Get efficiency opportunities
        efficiency_opportunities = await _efficiency_agent.get_opportunities(user_id)
        opps_list = efficiency_opportunities.get("opportunities", [])
        
        return {
            "summary_cards": summary_cards,
            "facility_count": len(facilities),
            "timeframe": timeframe,
            "recent_activities": recent_activities,
            "efficiency_opportunities": opps_list[:3],  # Top 3
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting dashboard data: {str(e)}")

async def get_recent_activities(user_id: str) -> List[Dict]:
    """Get recent activities for user"""
    db = get_db()
    
    # Get recent uploads
    recent_uploads = await db.uploaded_files.find(
        {"user_id": user_id},
        {"_id": 0, "filename": 1, "file_type": 1, "uploaded_at": 1, "processing_status": 1}
    ).sort("uploaded_at", -1).limit(5).to_list(5)
    
    # Get recent risk assessments
    recent_assessments = await db.risk_assessments.find(
        {"user_id": user_id},
        {"_id": 0, "facility_name": 1, "assessment_date": 1, "overall_risk_score": 1}
    ).sort("assessment_date", -1).limit(3).to_list(3)
    
    # Format activities
    activities = []
    
    for upload in recent_uploads:
        activities.append({
            "type": "file_upload",
            "title": f"Uploaded {upload['file_type'].replace('_', ' ')}",
            "description": upload['filename'],
            "timestamp": upload['uploaded_at'],
            "status": upload.get('processing_status', 'unknown')
        })
    
    for assessment in recent_assessments:
        risk_level = "Low"
        if assessment.get('overall_risk_score', 0) >= 3.5:
            risk_level = "High"
        elif assessment.get('overall_risk_score', 0) >= 2.5:
            risk_level = "Medium"
        
        activities.append({
            "type": "risk_assessment",
            "title": f"Risk assessment for {assessment.get('facility_name', 'Unknown')}",
            "description": f"Risk level: {risk_level}",
            "timestamp": assessment['assessment_date'],
            "risk_score": assessment.get('overall_risk_score')
        })
    
    # Sort by timestamp
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return activities[:10]  # Return top 10

@router.get("/trends")
async def get_water_trends(
    user_id: str = Query("anonymous"),
    period: str = Query("12months", regex="^(3months|6months|12months|24months)$")
):
    """
    Get water usage trends
    """
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        if period == "3months":
            months = 3
        elif period == "6months":
            months = 6
        elif period == "12months":
            months = 12
        else:  # 24months
            months = 24
        
        start_date = end_date - timedelta(days=months*30)
        
        # Get water data
        db = get_db()
        
        # Get user's facilities
        facilities = await db.facilities.find(
            {"user_id": user_id},
            {"_id": 0, "facility_id": 1, "name": 1}
        ).to_list(100)
        
        facility_ids = [f["facility_id"] for f in facilities]
        
        # Aggregate water data by month
        pipeline = [
            {
                "$match": {
                    "facility_id": {"$in": facility_ids},
                    "timestamp": {"$gte": start_date, "$lte": end_date},
                    "data_type": "water_usage"
                }
            },
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$timestamp"},
                        "month": {"$month": "$timestamp"}
                    },
                    "total_volume": {"$sum": "$volume"},
                    "total_cost": {"$sum": "$cost"},
                    "avg_unit_cost": {"$avg": "$unit_cost"},
                    "record_count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id.year": 1, "_id.month": 1}
            }
        ]
        
        monthly_data = await db.water_data.aggregate(pipeline).to_list(50)
        
        # Format trend data
        trends = []
        for data in monthly_data:
            month_str = f"{data['_id']['year']}-{data['_id']['month']:02d}"
            trends.append({
                "month": month_str,
                "volume": data["total_volume"],
                "cost": data["total_cost"],
                "unit_cost": data["avg_unit_cost"],
                "record_count": data["record_count"]
            })
        
        # Calculate insights
        insights = calculate_trend_insights(trends)
        
        return {
            "period": period,
            "trends": trends,
            "insights": insights,
            "facility_count": len(facilities)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting trends: {str(e)}")

def calculate_trend_insights(trends: List[Dict]) -> Dict:
    """Calculate insights from trend data"""
    if not trends:
        return {"message": "No data available"}
    
    # Calculate average
    volumes = [t["volume"] for t in trends if t["volume"]]
    if not volumes:
        return {"message": "No volume data"}
    
    avg_volume = sum(volumes) / len(volumes)
    max_volume = max(volumes)
    min_volume = min(volumes)
    
    # Find peak month
    peak_month = trends[volumes.index(max_volume)]["month"]
    
    # Calculate year-over-year change if we have enough data
    yoy_change = None
    if len(trends) >= 13:
        recent_avg = sum(volumes[-12:]) / 12
        previous_avg = sum(volumes[-24:-12]) / 12 if len(volumes) >= 24 else sum(volumes[:12]) / 12
        yoy_change = ((recent_avg - previous_avg) / previous_avg * 100) if previous_avg > 0 else 0
    
    # Check for seasonal pattern (simplified)
    seasonal_pattern = "Detected" if len(trends) >= 12 else "Insufficient data"
    
    return {
        "average_volume": avg_volume,
        "peak_volume": max_volume,
        "peak_month": peak_month,
        "lowest_volume": min_volume,
        "year_over_year_change": f"{yoy_change:+.1f}%" if yoy_change is not None else "N/A",
        "seasonal_pattern": seasonal_pattern,
        "data_points": len(trends)
    }

@router.get("/water-balance")
async def get_water_balance(
    user_id: str = Query("anonymous"),
    facility_id: Optional[str] = Query(None)
):
    """
    Get water balance breakdown
    """
    try:
        db = get_db()
        
        # Get facilities
        query = {"user_id": user_id}
        if facility_id:
            query["facility_id"] = facility_id
        
        facilities = await db.facilities.find(query).to_list(100)
        
        if not facilities:
            return {"message": "No facilities found"}
        
        # Get water balance data (simulated for now)
        # In real implementation, this would come from detailed water tracking
        
        water_balance = {
            "sources": [
                {"name": "Municipal", "volume": 90000, "percentage": 60, "color": "#3B82F6"},
                {"name": "Groundwater", "volume": 60000, "percentage": 40, "color": "#10B981"}
            ],
            "uses": [
                {"name": "Cooling Towers", "volume": 60000, "percentage": 40, "color": "#EF4444"},
                {"name": "Process Water", "volume": 45000, "percentage": 30, "color": "#F59E0B"},
                {"name": "Sanitary", "volume": 30000, "percentage": 20, "color": "#8B5CF6"},
                {"name": "Irrigation", "volume": 15000, "percentage": 10, "color": "#06B6D4"}
            ],
            "outputs": [
                {"name": "Discharge", "volume": 90000, "percentage": 60, "color": "#6366F1"},
                {"name": "Consumption", "volume": 60000, "percentage": 40, "color": "#EC4899"}
            ],
            "consumption_breakdown": [
                {"name": "Evaporation", "volume": 35000, "percentage": 58.3},
                {"name": "Product Incorporation", "volume": 15000, "percentage": 25.0},
                {"name": "Other Losses", "volume": 10000, "percentage": 16.7}
            ]
        }
        
        return {
            "facilities": [f["name"] for f in facilities],
            "water_balance": water_balance,
            "total_withdrawal": 150000,
            "total_discharge": 90000,
            "total_consumption": 60000,
            "circulation_efficiency": "40%",  # Consumption/Withdrawal
            "reuse_potential": "High"  # Based on discharge quality
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting water balance: {str(e)}")

@router.get("/efficiency-opportunities")
async def get_efficiency_opportunities(
    user_id: str = Query("anonymous"),
    roi_threshold: float = Query(1.0, description="Minimum ROI (payback period in years)")
):
    """
    Get water efficiency opportunities
    """
    try:
        result = await _efficiency_agent.get_opportunities(user_id)
        opportunities = result.get("opportunities", [])
        # filter by roi_threshold (payback in years)
        opportunities = [o for o in opportunities if o.get("payback_months", 999) / 12 <= (1 / roi_threshold) * 12]
        
        return {
            "opportunity_count": len(opportunities),
            "total_potential_savings": sum(o.get("annual_savings", 0) for o in opportunities),
            "total_investment": sum(o.get("implementation_cost", 0) for o in opportunities),
            "average_payback": calculate_average_payback(opportunities),
            "opportunities": opportunities
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting efficiency opportunities: {str(e)}")

def calculate_average_payback(opportunities: List[Dict]) -> float:
    """Calculate average payback period"""
    if not opportunities:
        return 0
    
    paybacks = []
    for opp in opportunities:
        cost = opp.get("implementation_cost", 0)
        savings = opp.get("annual_savings", 0)
        
        if cost > 0 and savings > 0:
            payback = cost / savings  # Years
            paybacks.append(payback)
    
    return sum(paybacks) / len(paybacks) if paybacks else 0

@router.get("/compliance-status")
async def get_compliance_status(
    user_id: str = Query("anonymous")
):
    """
    Get compliance status for all facilities
    """
    try:
        db = get_db()
        
        # Get facilities
        facilities = await db.facilities.find(
            {"user_id": user_id},
            {"_id": 0, "facility_id": 1, "name": 1, "address": 1}
        ).to_list(100)
        
        # Get compliance data (simulated)
        compliance_data = []
        
        for facility in facilities:
            # Simulated permit data
            permits = [
                {
                    "permit_id": "NPDES-CA0001234",
                    "type": "Wastewater Discharge",
                    "status": "Active",
                    "expiration": "2027-03-15",
                    "days_until_expiry": 365,
                    "compliance_rate": 100,
                    "last_violation": None
                },
                {
                    "permit_id": "GW-AZ-5678",
                    "type": "Groundwater Withdrawal",
                    "status": "Expiring Soon",
                    "expiration": "2026-03-15",
                    "days_until_expiry": 60,
                    "compliance_rate": 95,
                    "last_violation": "2025-07-15"
                }
            ]
            
            compliance_data.append({
                "facility": facility["name"],
                "facility_id": facility["facility_id"],
                "permits": permits,
                "overall_compliance": 98,
                "upcoming_deadlines": 2,
                "active_violations": 0
            })
        
        # Calculate overall metrics
        total_permits = sum(len(f["permits"]) for f in compliance_data)
        active_permits = sum(1 for f in compliance_data for p in f["permits"] if p["status"] == "Active")
        expiring_soon = sum(1 for f in compliance_data for p in f["permits"] if p.get("days_until_expiry", 999) <= 90)
        
        return {
            "facility_count": len(facilities),
            "total_permits": total_permits,
            "active_permits": active_permits,
            "permits_expiring_soon": expiring_soon,
            "overall_compliance_rate": 98,  # Simulated
            "compliance_data": compliance_data,
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting compliance status: {str(e)}")