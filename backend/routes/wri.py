from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import json
from geopy.distance import geodesic
import asyncio
from datetime import datetime

from database import get_db

router = APIRouter()

@router.get("/baseline/search")
async def search_baseline_data(
    latitude: float = Query(..., description="Latitude of location"),
    longitude: float = Query(..., description="Longitude of location"),
    radius_km: float = Query(10, description="Search radius in kilometers"),
    limit: int = Query(10, description="Maximum results to return")
):
    """
    Search for WRI baseline data near a location
    """
    try:
        db = get_db()
        
        # Get all baseline data (this is simplified - in production, use geospatial query)
        all_data = await db.wri_baseline_annual.find({}).limit(1000).to_list(1000)
        
        # Filter by distance (simplified - in production, use MongoDB geospatial indexes)
        nearby_data = []
        for record in all_data:
            # Check if record has coordinates
            if "lat" in record and "lon" in record:
                try:
                    record_lat = float(record["lat"])
                    record_lon = float(record["lon"])
                    
                    # Calculate distance
                    distance = geodesic(
                        (latitude, longitude),
                        (record_lat, record_lon)
                    ).kilometers
                    
                    if distance <= radius_km:
                        record["distance_km"] = distance
                        nearby_data.append(record)
                        
                        if len(nearby_data) >= limit:
                            break
                except (ValueError, TypeError):
                    continue
        
        # Sort by distance
        nearby_data.sort(key=lambda x: x.get("distance_km", float('inf')))
        
        return {
            "search_location": {"latitude": latitude, "longitude": longitude},
            "search_radius_km": radius_km,
            "results_found": len(nearby_data),
            "data": nearby_data[:limit]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching baseline data: {str(e)}")

@router.get("/baseline/{aqid}")
async def get_baseline_by_aqid(aqid: str):
    """
    Get WRI baseline data by AQID
    """
    try:
        db = get_db()
        
        record = await db.wri_baseline_annual.find_one({"aqid": aqid})
        
        if not record:
            raise HTTPException(status_code=404, detail=f"No data found for AQID: {aqid}")
        
        # Remove MongoDB _id field
        if "_id" in record:
            del record["_id"]
        
        return record
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting baseline data: {str(e)}")

@router.get("/baseline/country/{country_code}")
async def get_baseline_by_country(
    country_code: str,
    limit: int = Query(100, description="Maximum results to return")
):
    """
    Get WRI baseline data by country code
    """
    try:
        db = get_db()
        
        # Search by country code (gid_0 field)
        records = await db.wri_baseline_annual.find(
            {"gid_0": country_code.upper()}
        ).limit(limit).to_list(limit)
        
        # Remove MongoDB _id field
        for record in records:
            if "_id" in record:
                del record["_id"]
        
        return {
            "country_code": country_code.upper(),
            "results_found": len(records),
            "data": records
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting country data: {str(e)}")

@router.get("/future/{basin_id}")
async def get_future_projections(basin_id: str):
    """
    Get WRI future projections by basin ID
    """
    try:
        db = get_db()
        
        record = await db.wri_future_projections.find_one({"BasinID": basin_id})
        
        if not record:
            raise HTTPException(status_code=404, detail=f"No future projections found for BasinID: {basin_id}")
        
        # Remove MongoDB _id field
        if "_id" in record:
            del record["_id"]
        
        return record
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting future projections: {str(e)}")

@router.get("/risk-assessment")
async def assess_water_risk(
    latitude: float = Query(..., description="Latitude of facility"),
    longitude: float = Query(..., description="Longitude of facility"),
    include_future: bool = Query(True, description="Include future projections")
):
    """
    Assess water risk for a location using WRI data
    """
    try:
        db = get_db()
        
        # Find nearest baseline data point
        baseline_data = await find_nearest_baseline(latitude, longitude)
        
        if not baseline_data:
            raise HTTPException(status_code=404, detail="No WRI data found near this location")
        
        # Extract risk indicators
        risk_indicators = extract_risk_indicators(baseline_data)
        
        # Calculate overall risk score
        overall_risk = calculate_overall_risk(risk_indicators)
        
        # Get future projections if requested
        future_projections = None
        if include_future and "basinid" in baseline_data:
            future_projections = await db.wri_future_projections.find_one(
                {"BasinID": baseline_data["basinid"]}
            )
        
        # Generate risk assessment
        assessment = {
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "nearest_data_point": {
                    "distance_km": baseline_data.get("distance_km", 0),
                    "aqid": baseline_data.get("aqid"),
                    "basin_name": baseline_data.get("basin_name")
                }
            },
            "risk_indicators": risk_indicators,
            "overall_risk_score": overall_risk["score"],
            "risk_level": overall_risk["level"],
            "risk_category": overall_risk["category"],
            "key_findings": generate_key_findings(risk_indicators, overall_risk),
            "recommendations": generate_recommendations(overall_risk),
            "future_projections": future_projections if future_projections else None,
            "assessment_date": datetime.utcnow().isoformat()
        }
        
        return assessment
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error assessing water risk: {str(e)}")

async def find_nearest_baseline(latitude: float, longitude: float, max_distance_km: float = 50):
    """Find nearest baseline data point"""
    db = get_db()
    
    # Get sample data (simplified - in production, use geospatial query)
    sample_data = await db.wri_baseline_annual.find({}).limit(1000).to_list(1000)
    
    nearest = None
    min_distance = float('inf')
    
    for record in sample_data:
        if "lat" in record and "lon" in record:
            try:
                record_lat = float(record["lat"])
                record_lon = float(record["lon"])
                
                distance = geodesic(
                    (latitude, longitude),
                    (record_lat, record_lon)
                ).kilometers
                
                if distance < min_distance and distance <= max_distance_km:
                    min_distance = distance
                    record["distance_km"] = distance
                    nearest = record
            except (ValueError, TypeError):
                continue
    
    return nearest

def extract_risk_indicators(baseline_data: Dict) -> Dict:
    """Extract risk indicators from baseline data"""
    indicators = {}
    
    # Map WRI fields to risk indicators
    field_mapping = {
        "bws_cat": "baseline_water_stress",
        "bwd_cat": "water_depletion",
        "iav_cat": "interannual_variability",
        "sev_cat": "seasonal_variability",
        "gtd_cat": "groundwater_table_decline",
        "rfr_cat": "riverine_flood_risk",
        "cfr_cat": "coastal_flood_risk",
        "drr_cat": "drought_risk",
        "ucw_cat": "upstream_consumptive_water",
        "ucs_cat": "upstream_storage",
        "rri_cat": "regulatory_risk"
    }
    
    for wri_field, risk_indicator in field_mapping.items():
        if wri_field in baseline_data:
            value = baseline_data[wri_field]
            # Convert categorical to numeric score (1-5)
            score = categorical_to_score(value)
            indicators[risk_indicator] = {
                "value": value,
                "score": score,
                "category": get_risk_category(score)
            }
    
    return indicators

def categorical_to_score(category: str) -> float:
    """Convert WRI categorical value to numeric score (1-5)"""
    category_map = {
        "Low": 1.0,
        "Low to medium": 1.5,
        "Low-medium": 1.5,
        "Medium": 2.5,
        "Medium to high": 3.5,
        "Medium-high": 3.5,
        "High": 4.0,
        "Extremely high": 5.0,
        "Arid and low water use": 1.0
    }
    
    return category_map.get(str(category).strip(), 2.5)

def get_risk_category(score: float) -> str:
    """Get risk category from score"""
    if score >= 4.5:
        return "Extremely High"
    elif score >= 3.5:
        return "High"
    elif score >= 2.5:
        return "Medium-High"
    elif score >= 1.5:
        return "Low-Medium"
    else:
        return "Low"

def calculate_overall_risk(risk_indicators: Dict) -> Dict:
    """Calculate overall risk score"""
    if not risk_indicators:
        return {"score": 0, "level": "Unknown", "category": "Unknown"}
    
    # Calculate weighted average
    weights = {
        "baseline_water_stress": 0.3,
        "water_depletion": 0.2,
        "drought_risk": 0.15,
        "regulatory_risk": 0.1,
        "interannual_variability": 0.1,
        "seasonal_variability": 0.05,
        "groundwater_table_decline": 0.05,
        "riverine_flood_risk": 0.025,
        "coastal_flood_risk": 0.025
    }
    
    total_score = 0
    total_weight = 0
    
    for indicator, data in risk_indicators.items():
        weight = weights.get(indicator, 0.05)
        score = data.get("score", 2.5)
        
        total_score += score * weight
        total_weight += weight
    
    overall_score = total_score / total_weight if total_weight > 0 else 2.5
    
    return {
        "score": round(overall_score, 2),
        "level": get_risk_level(overall_score),
        "category": get_risk_category(overall_score)
    }

def get_risk_level(score: float) -> str:
    """Get risk level from score"""
    if score >= 4.0:
        return "Critical"
    elif score >= 3.0:
        return "High"
    elif score >= 2.0:
        return "Medium"
    elif score >= 1.0:
        return "Low"
    else:
        return "Very Low"

def generate_key_findings(risk_indicators: Dict, overall_risk: Dict) -> List[str]:
    """Generate key findings from risk assessment"""
    findings = []
    
    # Overall risk finding
    findings.append(f"Overall water risk: {overall_risk['level']} ({overall_risk['score']}/5.0)")
    
    # Top 3 risk indicators
    sorted_indicators = sorted(
        risk_indicators.items(),
        key=lambda x: x[1].get("score", 0),
        reverse=True
    )[:3]
    
    for indicator, data in sorted_indicators:
        indicator_name = indicator.replace("_", " ").title()
        findings.append(f"{indicator_name}: {data['category']} ({data['score']}/5.0)")
    
    # Specific recommendations based on high risks
    if overall_risk["score"] >= 3.5:
        findings.append("⚠️ Location is in a high water stress area - immediate action recommended")
    
    if risk_indicators.get("drought_risk", {}).get("score", 0) >= 3.0:
        findings.append("⚠️ High drought risk - consider water storage and alternative sources")
    
    if risk_indicators.get("regulatory_risk", {}).get("score", 0) >= 3.0:
        findings.append("⚠️ High regulatory risk - ensure compliance and engage with regulators")
    
    return findings

def generate_recommendations(overall_risk: Dict) -> List[Dict]:
    """Generate recommendations based on risk level"""
    recommendations = []
    
    if overall_risk["score"] >= 4.0:  # Critical
        recommendations.extend([
            {
                "priority": "Immediate",
                "action": "Conduct detailed water audit",
                "description": "Complete assessment of all water uses and sources",
                "timeline": "Within 30 days"
            },
            {
                "priority": "Immediate",
                "action": "Develop water resilience plan",
                "description": "Create plan for drought and water shortage scenarios",
                "timeline": "Within 60 days"
            },
            {
                "priority": "High",
                "action": "Implement water recycling",
                "description": "Install systems to reuse process water",
                "timeline": "6-12 months"
            }
        ])
    elif overall_risk["score"] >= 3.0:  # High
        recommendations.extend([
            {
                "priority": "High",
                "action": "Monitor water usage closely",
                "description": "Implement daily tracking and reporting",
                "timeline": "Immediate"
            },
            {
                "priority": "High",
                "action": "Identify efficiency opportunities",
                "description": "Audit for leaks and inefficient equipment",
                "timeline": "Within 90 days"
            },
            {
                "priority": "Medium",
                "action": "Explore alternative water sources",
                "description": "Investigate rainwater harvesting or reclaimed water",
                "timeline": "6-12 months"
            }
        ])
    else:  # Medium or Low
        recommendations.extend([
            {
                "priority": "Medium",
                "action": "Establish baseline metrics",
                "description": "Track water usage and set reduction targets",
                "timeline": "Within 90 days"
            },
            {
                "priority": "Medium",
                "action": "Implement best practices",
                "description": "Adopt water-efficient technologies and processes",
                "timeline": "Ongoing"
            },
            {
                "priority": "Low",
                "action": "Plan for future risks",
                "description": "Consider climate change impacts in long-term planning",
                "timeline": "12-24 months"
            }
        ])
    
    return recommendations

@router.get("/compare")
async def compare_locations(
    locations: str = Query(..., description="Comma-separated lat,lon pairs (e.g., '37.7749,-122.4194,34.0522,-118.2437')")
):
    """
    Compare water risk between multiple locations
    """
    try:
        # Parse locations
        coords = locations.split(",")
        if len(coords) % 2 != 0:
            raise HTTPException(status_code=400, detail="Invalid coordinates format")
        
        locations_list = []
        for i in range(0, len(coords), 2):
            try:
                lat = float(coords[i].strip())
                lon = float(coords[i+1].strip())
                locations_list.append((lat, lon))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid coordinate: {coords[i]},{coords[i+1]}")
        
        # Assess risk for each location
        assessments = []
        for lat, lon in locations_list:
            try:
                # Use the risk assessment endpoint logic
                baseline_data = await find_nearest_baseline(lat, lon)
                
                if baseline_data:
                    risk_indicators = extract_risk_indicators(baseline_data)
                    overall_risk = calculate_overall_risk(risk_indicators)
                    
                    assessments.append({
                        "location": {"latitude": lat, "longitude": lon},
                        "overall_risk": overall_risk,
                        "top_risks": get_top_risks(risk_indicators, 3)
                    })
                else:
                    assessments.append({
                        "location": {"latitude": lat, "longitude": lon},
                        "error": "No WRI data available",
                        "overall_risk": {"score": 0, "level": "Unknown"}
                    })
            except Exception as e:
                assessments.append({
                    "location": {"latitude": lat, "longitude": lon},
                    "error": str(e),
                    "overall_risk": {"score": 0, "level": "Error"}
                })
        
        # Sort by risk score (highest first)
        valid_assessments = [a for a in assessments if "error" not in a]
        valid_assessments.sort(key=lambda x: x["overall_risk"]["score"], reverse=True)
        
        return {
            "locations_count": len(locations_list),
            "assessments": assessments,
            "highest_risk": valid_assessments[0] if valid_assessments else None,
            "lowest_risk": valid_assessments[-1] if valid_assessments else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing locations: {str(e)}")

def get_top_risks(risk_indicators: Dict, count: int = 3) -> List[Dict]:
    """Get top risk indicators"""
    sorted_risks = sorted(
        risk_indicators.items(),
        key=lambda x: x[1].get("score", 0),
        reverse=True
    )[:count]
    
    return [
        {
            "indicator": indicator.replace("_", " ").title(),
            "score": data["score"],
            "category": data["category"]
        }
        for indicator, data in sorted_risks
    ]

@router.get("/stats")
async def get_wri_stats():
    """
    Get statistics about WRI data
    """
    try:
        db = get_db()
        
        # Get counts
        baseline_count = await db.wri_baseline_annual.count_documents({})
        future_count = await db.wri_future_projections.count_documents({})
        
        # Get sample of unique countries
        pipeline = [
            {"$group": {"_id": "$gid_0"}},
            {"$limit": 20}
        ]
        
        countries = await db.wri_baseline_annual.aggregate(pipeline).to_list(20)
        country_codes = [c["_id"] for c in countries if c["_id"]]
        
        return {
            "baseline_records": baseline_count,
            "future_projections": future_count,
            "countries_covered": len(country_codes),
            "sample_countries": country_codes,
            "data_source": "WRI Aqueduct 3.0",
            "last_updated": "2019-07-12"  # From folder name
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting WRI stats: {str(e)}")