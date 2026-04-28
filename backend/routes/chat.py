from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any, Optional
import json
import asyncio
from datetime import datetime
import uuid

from database import Conversation, get_db
from services.openrouter_service import OpenRouterService
from agents import OrchestratorAgent

router = APIRouter()

# Shared service instances
try:
    ai_service = OpenRouterService()
except Exception as e:
    print(f"Warning: OpenRouterService init failed: {e}")
    ai_service = None

# Keep gemini_service alias so existing code that references it still works
gemini_service = ai_service

# Single shared orchestrator instance (agents are stateless per-request)
_orchestrator: Optional[OrchestratorAgent] = None

def get_orchestrator() -> OrchestratorAgent:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = OrchestratorAgent(gemini_service=ai_service)
    return _orchestrator

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_sessions: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.user_sessions[session_id] = websocket

    def disconnect(self, websocket: WebSocket, session_id: str):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if session_id in self.user_sessions:
            del self.user_sessions[session_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

def _calculate_dashboard_from_data(facilities, utility_bills, meter_data, discharge_reports, suppliers):
    """
    Calculate dashboard data directly from database without AI
    Fallback when Gemini API is not available
    """
    # Calculate facilities summary
    facility_list = []
    total_usage = 0
    total_cost = 0
    
    for bill in utility_bills:
        facility_list.append({
            "id": bill.get("facility_id", ""),
            "name": bill.get("facility_name", "Unknown"),
            "usage": bill.get("water_volume_gallons", 0),
            "cost": bill.get("total_cost", 0)
        })
        total_usage += bill.get("water_volume_gallons", 0)
        total_cost += bill.get("total_cost", 0)
    
    # If no bills, use meter data
    if not facility_list and meter_data:
        meter_usage = {}
        for meter in meter_data:
            fac_id = meter.get("facility_id", "")
            consumption = meter.get("consumption", 0)
            if fac_id in meter_usage:
                meter_usage[fac_id] += consumption
            else:
                meter_usage[fac_id] = consumption
        
        for fac_id, usage in meter_usage.items():
            facility_list.append({
                "id": fac_id,
                "name": f"Facility {fac_id}",
                "usage": usage,
                "cost": int(usage * 0.03)  # Estimate $0.03 per gallon
            })
            total_usage += usage
            total_cost += int(usage * 0.03)
    
    # Calculate meters summary
    meter_breakdown = []
    for meter in meter_data:  # All meters
        consumption = meter.get("consumption", 0)
        percentage = round((consumption / total_usage * 100), 1) if total_usage > 0 else 0
        meter_breakdown.append({
            "meter": meter.get("meter_id", ""),
            "location": meter.get("location", ""),
            "consumption": consumption,
            "percentage": percentage
        })
    
    # Calculate compliance
    compliance_rate = 100
    total_tests = 0
    passed_tests = 0
    permits = 0
    
    if discharge_reports:
        for report in discharge_reports:
            if "permits" in report:
                permits += len(report["permits"])
                for permit in report["permits"]:
                    total_tests += permit.get("total_parameters", 0)
                    passed_tests += permit.get("passed_parameters", 0)
        
        if total_tests > 0:
            compliance_rate = round((passed_tests / total_tests * 100), 1)
    
    # Calculate suppliers
    supplier_count = 0
    high_risk_count = 0
    total_spend = 0
    high_risk_list = []
    
    if suppliers and suppliers.get("suppliers"):
        supplier_list = suppliers["suppliers"]
        supplier_count = len(supplier_list)
        
        for supplier in supplier_list:
            total_spend += supplier.get("annual_spend_usd", 0)
            if supplier.get("water_intensity_factor", 0) > 200000:
                high_risk_count += 1
                high_risk_list.append(supplier.get("supplier_name", ""))
    
    # Generate insights
    insights = []
    if meter_data:
        top_meter = max(meter_data, key=lambda x: x.get("consumption", 0))
        top_consumption_pct = round((top_meter.get("consumption", 0) / total_usage * 100), 1) if total_usage > 0 else 0
        if top_consumption_pct > 50:
            insights.append({
                "type": "warning",
                "message": f"{top_meter.get('location', 'One location')} accounts for {top_consumption_pct}% of total consumption",
                "priority": "high"
            })
    
    if compliance_rate == 100:
        insights.append({
            "type": "success",
            "message": f"100% compliance rate on discharge permits",
            "priority": "low"
        })
    elif compliance_rate < 100:
        insights.append({
            "type": "warning",
            "message": f"Compliance rate at {compliance_rate}% - action needed",
            "priority": "high"
        })
    
    if high_risk_count > 0:
        insights.append({
            "type": "info",
            "message": f"{supplier_count} suppliers with {high_risk_count} in high water-risk areas",
            "priority": "medium"
        })
    
    # Generate recommendations
    recommendations = []
    if total_usage > 1000000:
        recommendations.append({
            "title": "Optimize High-Usage Facilities",
            "impact": "High",
            "savings": "15-20%"
        })
    
    if high_risk_count > 0:
        recommendations.append({
            "title": "Monitor High-Risk Suppliers",
            "impact": "Medium",
            "savings": "N/A"
        })
    
    recommendations.append({
        "title": "Install Smart Meters",
        "impact": "Medium",
        "savings": "10-15%"
    })
    
    return {
        "facilities": {
            "total": len(facility_list),
            "list": facility_list
        },
        "total_usage": total_usage,
        "total_cost": total_cost,
        "avg_cost_per_1000_gal": round((total_cost / total_usage * 1000), 2) if total_usage > 0 else 0,
        "meters": {
            "total": len(meter_data),
            "active": len([m for m in meter_data if m.get("status") == "normal"]),
            "consumption_breakdown": meter_breakdown
        },
        "compliance": {
            "rate": compliance_rate,
            "permits": permits,
            "passed_tests": passed_tests,
            "total_tests": total_tests
        },
        "suppliers": {
            "total": supplier_count,
            "high_risk": high_risk_count,
            "total_spend": total_spend,
            "high_risk_list": high_risk_list[:3]
        },
        "insights": insights,
        "recommendations": recommendations
    }

# Welcome message and options
WELCOME_MESSAGE = {
    "type": "welcome",
    "content": "Hi! I'm your Water Stewardship AI Assistant. I help you track water usage, assess risks, optimize efficiency, and ensure compliance. What would you like to do today?",
    "options": [
        {"id": "upload", "label": "📤 Upload Water Data", "icon": "upload"},
        {"id": "dashboard", "label": "📊 View Dashboard", "icon": "dashboard"},
        {"id": "risk", "label": "🗺️ Water Risk Assessment", "icon": "risk"},
        {"id": "footprint", "label": "💧 Calculate Water Footprint", "icon": "footprint"},
        {"id": "efficiency", "label": "📈 Efficiency Opportunities", "icon": "efficiency"},
        {"id": "compliance", "label": "📋 Compliance & Permits", "icon": "compliance"},
        {"id": "supply_chain", "label": "🌊 Supply Chain Water Risk", "icon": "supply_chain"},
        {"id": "strategy", "label": "🎯 Build Stewardship Strategy", "icon": "strategy"},
        {"id": "ask", "label": "💬 Ask Me Anything", "icon": "ask"}
    ]
}

# Upload flow options
UPLOAD_OPTIONS = {
    "type": "upload_options",
    "content": "I need 5 types of documents for complete water insights. Which one would you like to upload?",
    "options": [
        {"id": "utility_bills", "label": "💵 Utility Bills", "description": "Water bills (PDF/Excel/CSV)", "icon": "bill"},
        {"id": "meter_readings", "label": "📟 Meter Readings", "description": "IoT/meter logs", "icon": "meter"},
        {"id": "facility_info", "label": "🏭 Facility Info", "description": "Location & operational details", "icon": "facility"},
        {"id": "supplier_list", "label": "📦 Supplier List", "description": "Supply chain data", "icon": "supplier"},
        {"id": "discharge_reports", "label": "🧪 Discharge Reports", "description": "Permits & pollutant data", "icon": "discharge"}
    ]
}

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    
    try:
        # Send welcome message
        await manager.send_personal_message(
            json.dumps(WELCOME_MESSAGE),
            websocket
        )
        
        # Create conversation in database
        conversation = await Conversation.create_conversation(
            user_id="anonymous",  # In real app, get from auth
            session_id=session_id
        )
        
        # Add welcome message to conversation
        await Conversation.add_message(
            conversation["conversation_id"],
            "assistant",
            WELCOME_MESSAGE["content"],
            {"type": "welcome", "options": WELCOME_MESSAGE["options"]}
        )
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Handle different message types
            message_type = message_data.get("type", "text")
            
            if message_type == "text":
                await handle_text_message(
                    websocket, 
                    session_id, 
                    conversation["conversation_id"], 
                    message_data
                )
            elif message_type == "option_selected":
                await handle_option_selection(
                    websocket,
                    session_id,
                    conversation["conversation_id"],
                    message_data
                )
            elif message_type == "file_uploaded":
                await handle_file_upload(
                    websocket,
                    session_id,
                    conversation["conversation_id"],
                    message_data
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.send_personal_message(
            json.dumps({
                "type": "error",
                "content": f"An error occurred: {str(e)}"
            }),
            websocket
        )

async def handle_text_message(websocket: WebSocket, session_id: str, conversation_id: str, message_data: Dict):
    """Handle text messages from user"""
    user_message = message_data.get("content", "")
    
    # Add user message to conversation
    await Conversation.add_message(
        conversation_id,
        "user",
        user_message
    )
    
    # Process with AI
    response = await gemini_service.process_chat_message(
        user_message=user_message,
        session_id=session_id,
        conversation_id=conversation_id
    )
    
    # Add assistant response to conversation
    await Conversation.add_message(
        conversation_id,
        "assistant",
        response["content"],
        response.get("metadata", {})
    )
    
    # Send response to client
    await manager.send_personal_message(
        json.dumps(response),
        websocket
    )

async def handle_option_selection(websocket: WebSocket, session_id: str, conversation_id: str, message_data: Dict):
    """Handle option selection from user"""
    option_id = message_data.get("option_id", "")
    
    # Add user selection to conversation
    await Conversation.add_message(
        conversation_id,
        "user",
        f"Selected option: {option_id}",
        {"option_id": option_id}
    )
    
    # Handle different options
    if option_id == "upload":
        response = UPLOAD_OPTIONS
    elif option_id == "utility_bills":
        response = {
            "type": "upload_prompt",
            "content": "Upload your water utility bill (PDF, Excel, or CSV). I can handle 25+ utility formats.",
            "upload_type": "utility_bill",
            "allowed_formats": ["pdf", "csv", "xlsx", "xls"],
            "max_size": "10MB"
        }
    elif option_id == "meter_readings":
        response = {
            "type": "meter_options",
            "content": "Upload meter logs (Excel/CSV) or connect smart meters",
            "options": [
                {"id": "upload_meter", "label": "📁 Upload File", "icon": "upload"},
                {"id": "connect_iot", "label": "🔌 Connect IoT Device", "icon": "iot"}
            ]
        }
    elif option_id == "dashboard":
        orch = get_orchestrator()
        response = await orch.handle_message("Show Dashboard", session_id)
    elif option_id == "risk":
        orch = get_orchestrator()
        response = await orch.handle_message("Water Risk Assessment", session_id)
    else:
        # Default response for other options
        response = {
            "type": "text",
            "content": f"Processing your selection: {option_id}. This feature is coming soon!"
        }
    
    # Add assistant response to conversation
    await Conversation.add_message(
        conversation_id,
        "assistant",
        response["content"],
        response
    )
    
    # Send response to client
    await manager.send_personal_message(
        json.dumps(response),
        websocket
    )

async def handle_file_upload(websocket: WebSocket, session_id: str, conversation_id: str, message_data: Dict):
    """Handle file upload completion"""
    file_id = message_data.get("file_id", "")
    filename = message_data.get("filename", "")
    file_type = message_data.get("file_type", "")
    
    # Add file upload to conversation
    await Conversation.add_message(
        conversation_id,
        "user",
        f"Uploaded file: {filename}",
        {"file_id": file_id, "filename": filename, "file_type": file_type}
    )
    
    # Process file based on type
    if file_type == "utility_bill":
        response = await process_utility_bill(file_id, filename)
    elif file_type == "meter_data":
        response = await process_meter_data(file_id, filename)
    elif file_type == "discharge_report":
        response = await process_discharge_report(file_id, filename)
    else:
        response = {
            "type": "text",
            "content": f"File {filename} uploaded successfully. Processing..."
        }
    
    # Add assistant response to conversation
    await Conversation.add_message(
        conversation_id,
        "assistant",
        response["content"],
        response
    )
    
    # Send response to client
    await manager.send_personal_message(
        json.dumps(response),
        websocket
    )

async def process_utility_bill(file_id: str, filename: str) -> Dict:
    """Process utility bill using Gemini OCR"""
    try:
        # In real implementation, this would:
        # 1. Get file from storage
        # 2. Use Gemini to extract data
        # 3. Parse and validate data
        # 4. Store in database
        
        # Simulated extracted data
        extracted_data = {
            "facility": "Acme Manufacturing, San Francisco CA",
            "water_volume": 150000,  # gallons
            "wastewater_volume": 90000,  # gallons
            "cost": 4500,  # dollars
            "period": "Jan 1-31, 2026",
            "source": "Municipal water",
            "meter_reading_current": 45230,
            "meter_reading_previous": 45080,
            "rate_tier": "Tier 2 (10-50 CCF @ $3/CCF)",
            "confidence": 0.95
        }
        
        response = {
            "type": "utility_bill_result",
            "content": "✅ Processing... Done! I extracted:",
            "data": extracted_data,
            "options": [
                {"id": "upload_another", "label": "📤 Upload Another Bill", "icon": "upload"},
                {"id": "add_meter", "label": "📟 Add Meter Data", "icon": "meter"},
                {"id": "add_discharge", "label": "🧪 Add Discharge Report", "icon": "discharge"},
                {"id": "show_insights", "label": "📊 Show Insights", "icon": "insights"}
            ]
        }
        
        return response
        
    except Exception as e:
        return {
            "type": "error",
            "content": f"Error processing utility bill: {str(e)}"
        }

async def process_meter_data(file_id: str, filename: str) -> Dict:
    """Process meter data"""
    # Simulated meter data processing
    extracted_data = {
        "meters_tracked": 3,
        "meter_details": [
            {"id": "M-001", "name": "Main Supply", "reading": 45230, "unit": "gallons"},
            {"id": "M-002", "name": "Cooling Tower", "reading": 28500, "unit": "gallons"},
            {"id": "M-003", "name": "Process Line", "reading": 15200, "unit": "gallons"}
        ],
        "time_range": "Jan 1-31, 2026",
        "frequency": "Daily readings",
        "anomaly_detected": True,
        "anomaly_details": "M-002 shows 15% spike on Jan 15"
    }
    
    response = {
        "type": "meter_data_result",
        "content": "✅ Processing meter data... Found:",
        "data": extracted_data,
        "options": [
            {"id": "investigate_anomaly", "label": "🔍 Investigate Anomaly", "icon": "investigate"},
            {"id": "view_trends", "label": "📊 View Meter Trends", "icon": "trends"},
            {"id": "upload_more", "label": "📤 Upload More Data", "icon": "upload"}
        ]
    }
    
    return response

async def process_discharge_report(file_id: str, filename: str) -> Dict:
    """Process discharge report"""
    # Simulated discharge report processing
    extracted_data = {
        "permit": "NPDES CA0001234",
        "outfall": "001",
        "discharge_volume": 90000,  # gallons
        "sampling_date": "Jan 15, 2026",
        "pollutant_results": [
            {"parameter": "BOD", "value": 25, "limit": 30, "status": "pass"},
            {"parameter": "COD", "value": 85, "limit": 100, "status": "pass"},
            {"parameter": "TSS", "value": 22, "limit": 30, "status": "pass"},
            {"parameter": "pH", "value": 7.2, "limit_min": 6, "limit_max": 9, "status": "pass"},
            {"parameter": "Temperature", "value": 28, "limit": 30, "status": "pass"}
        ],
        "compliance_status": "compliant"
    }
    
    response = {
        "type": "discharge_report_result",
        "content": "✅ Processing discharge report... Found:",
        "data": extracted_data,
        "options": [
            {"id": "check_permit_expiry", "label": "📅 Check Permit Expiry", "icon": "calendar"},
            {"id": "view_compliance_history", "label": "📊 View Compliance History", "icon": "history"},
            {"id": "set_alerts", "label": "🔔 Set Alerts", "icon": "alert"},
            {"id": "upload_more", "label": "📤 Upload More Data", "icon": "upload"}
        ]
    }
    
    return response

# REST endpoints for chat history
@router.get("/history/{conversation_id}")
async def get_chat_history(conversation_id: str):
    """Get chat history for a conversation"""
    db = get_db()
    conversation = await db.conversations.find_one(
        {"conversation_id": conversation_id},
        {"messages": 1, "created_at": 1, "updated_at": 1}
    )
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "conversation_id": conversation_id,
        "messages": conversation.get("messages", []),
        "created_at": conversation.get("created_at"),
        "updated_at": conversation.get("updated_at")
    }

@router.post("/start")
async def start_new_conversation(user_id: str = "anonymous"):
    """Start a new conversation"""
    conversation = await Conversation.create_conversation(user_id)
    return {
        "conversation_id": conversation["conversation_id"],
        "session_id": conversation["session_id"],
        "created_at": conversation["created_at"]
    }

@router.post("/message")
async def send_message(request: Dict[str, Any]):
    """Send a message and get response — routed through OrchestratorAgent."""
    session_id = request.get("session_id")
    message = request.get("message")
    user_id = request.get("user_id", "demo")

    if not session_id or not message:
        raise HTTPException(status_code=400, detail="session_id and message are required")

    try:
        db = get_db()
        conversation = await db.conversations.find_one({"session_id": session_id})
        if not conversation:
            conversation = await Conversation.create_conversation("anonymous", session_id)

        await Conversation.add_message(conversation["conversation_id"], "user", message)

        message_lower = message.lower()

        # Handle specific upload sub-type selections (from button clicks)
        upload_prompts = {
            "💵 utility bills": ("utility_bill", "Upload your water utility bill (PDF, Excel, or CSV). I can handle 25+ utility formats."),
            "📟 meter readings": ("meter_data", "Upload meter logs (Excel/CSV) or connect smart meters."),
            "🏭 facility info": ("facility_info", "Upload your facility info file (CSV/Excel) or I can guide you through manual entry."),
            "📦 supplier list": ("supplier_list", "Upload your supplier list (Excel/CSV) with columns: Supplier Name, Location, Product Category, Annual Spend."),
            "🧪 discharge reports": ("discharge_report", "Upload discharge/wastewater reports (PDF, lab results, permit documents)."),
        }
        for keyword, (upload_type, prompt_text) in upload_prompts.items():
            if keyword in message_lower:
                response = {
                    "content": prompt_text,
                    "type": "upload_prompt",
                    "upload_type": upload_type,
                    "options": [{"id": "upload_file", "label": "📁 Upload File", "icon": "📁"}],
                }
                await Conversation.add_message(conversation["conversation_id"], "assistant", response["content"], response)
                return response

        # Route everything else through the orchestrator
        orchestrator = get_orchestrator()
        response = await orchestrator.handle(message=message, user_id=user_id, session_id=session_id)

        await Conversation.add_message(
            conversation["conversation_id"], "assistant",
            response.get("content", ""), response
        )
        return response

    except Exception as e:
        print(f"send_message error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message/legacy")
async def send_message_legacy(request: Dict[str, Any]):
    """Legacy endpoint — old monolithic handler kept for reference."""
    session_id = request.get("session_id")
    message = request.get("message")

    if not session_id or not message:
        raise HTTPException(status_code=400, detail="session_id and message are required")

    try:
        # Create or get conversation
        db = get_db()
        conversation = await db.conversations.find_one({"session_id": session_id})

        if not conversation:
            conversation = await Conversation.create_conversation("anonymous", session_id)

        # Add user message
        await Conversation.add_message(
            conversation["conversation_id"],
            "user",
            message
        )

        # Simple response logic without requiring Gemini
        message_lower = message.lower()

        # Check for specific intents
        if any(word in message_lower for word in ['upload', 'file', 'data']) and 'utility' not in message_lower and 'meter' not in message_lower and 'facility' not in message_lower and 'supplier' not in message_lower and 'discharge' not in message_lower:
            response_text = "I need 5 types of documents for complete water insights. Which one would you like to upload?"
            options = [
                {"id": "utility_bills", "label": "Utility Bills", "icon": "💵", "description": "Water bills (PDF/Excel/CSV)"},
                {"id": "meter_readings", "label": "Meter Readings", "icon": "📟", "description": "IoT/meter logs"},
                {"id": "facility_info", "label": "Facility Info", "icon": "🏭", "description": "Location & operational details"},
                {"id": "supplier_list", "label": "Supplier List", "icon": "📦", "description": "Supply chain data"},
                {"id": "discharge_reports", "label": "Discharge Reports", "icon": "🧪", "description": "Permits & pollutant data"}
            ]
        elif 'yes' in message_lower and 'dashboard' in message_lower:
            # User confirmed they want to see dashboard - fetch real data from MongoDB
            db = get_db()
            facilities = await db.facilities.find({"user_id": "demo"}).to_list(length=None)
            utility_bills = await db.utility_bills.find({"user_id": "demo"}).to_list(length=None)
            meter_data = await db.meter_data.find({"user_id": "demo"}).to_list(length=None)
            discharge_reports = await db.discharge_reports.find({"user_id": "demo"}).to_list(length=None)
            suppliers = await db.suppliers.find_one({"user_id": "demo"})
            
            dashboard_data = _calculate_dashboard_from_data(
                facilities, utility_bills, meter_data, discharge_reports, suppliers
            )
            
            response_text = "Here's your water dashboard with key metrics and insights:"
            options = [
                {"id": "efficiency_tips", "label": "Efficiency Tips", "icon": "💡", "description": "Get water-saving recommendations"},
                {"id": "risk_analysis", "label": "Risk Analysis", "icon": "⚠️", "description": "Detailed risk assessment"},
                {"id": "cost_breakdown", "label": "Cost Breakdown", "icon": "💰", "description": "Analyze spending patterns"},
                {"id": "upload_more", "label": "Upload More Data", "icon": "📤", "description": "Add more documents"}
            ]
            
            # Add dashboard data to response
            await Conversation.add_message(
                conversation["conversation_id"],
                "assistant",
                response_text,
                {"type": "dashboard", "dashboard_data": dashboard_data, "options": options}
            )
            
            return {
                "content": response_text,
                "type": "dashboard",
                "dashboard_data": dashboard_data,
                "options": options
            }
        elif 'yes' in message_lower and ('analyze' in message_lower or 'run' in message_lower) and 'risk' in message_lower:
            # User confirmed risk analysis - fetch real WRI data and use Gemini AI
            db = get_db()
            
            facilities = await db.facilities.find({"user_id": "demo"}).to_list(length=None)
            wri_baseline = await db.wri_baseline_annual.find({}).to_list(length=None)
            wri_projections = await db.wri_future_projections.find({}).to_list(length=None)
            
            if not facilities:
                response_text = "Please upload your facility information first to perform risk analysis."
                options = [
                    {"id": "upload_facility", "label": "Upload Facility Data", "icon": "📁", "description": "Upload facility info"},
                    {"id": "back_dashboard", "label": "Back to Dashboard", "icon": "📊", "description": "Return to overview"}
                ]
                
                await Conversation.add_message(
                    conversation["conversation_id"],
                    "assistant",
                    response_text,
                    {"type": "error", "options": options}
                )
                
                return {
                    "content": response_text,
                    "type": "error",
                    "options": options
                }
            
            # Prepare data for Gemini
            prompt = f"""Analyze water risk for these facilities using WRI Aqueduct data:

FACILITIES:
{json.dumps(facilities, indent=2, default=str)}

WRI BASELINE DATA (Current Risk):
{json.dumps(wri_baseline[:5] if wri_baseline else [], indent=2, default=str)}

WRI FUTURE PROJECTIONS (Climate Scenarios):
{json.dumps(wri_projections[:5] if wri_projections else [], indent=2, default=str)}

Match each facility location to the nearest WRI data point and generate a comprehensive risk assessment. Return JSON with this EXACT structure:
{{
    "overall_risk": "Low|Low-Medium|Medium|Medium-High|High|Extremely High",
    "risk_score": <0-5.0>,
    "facilities": [
        {{
            "id": "facility_id",
            "name": "facility name",
            "location": "city, state",
            "coordinates": {{"lat": <latitude>, "lon": <longitude>}},
            "overall_risk": "risk level",
            "risk_score": <0-5.0>,
            "risk_breakdown": {{
                "baseline_water_stress": {{"score": <0-5>, "level": "level", "description": "description"}},
                "water_depletion": {{"score": <0-5>, "level": "level", "description": "description"}},
                "flooding_risk": {{"score": <0-5>, "level": "level", "description": "description"}},
                "drought_risk": {{"score": <0-5>, "level": "level", "description": "description"}},
                "water_quality": {{"score": <0-5>, "level": "level", "description": "description"}}
            }}
        }}
    ],
    "key_risks": [
        {{"type": "critical|warning|info", "message": "risk description", "action": "recommended action"}}
    ],
    "recommendations": [
        {{"priority": "High|Medium|Low", "action": "action description", "impact": "expected impact"}}
    ]
}}

IMPORTANT:
- Use actual WRI risk scores from the data
- Provide specific insights based on facility locations
- Include 3-5 key risks and 4-6 recommendations
- Return ONLY valid JSON, no markdown"""

            gemini_response = await gemini_service.generate_content(prompt)
            
            try:
                clean_response = gemini_response.strip()
                if clean_response.startswith("```json"):
                    clean_response = clean_response[7:]
                if clean_response.startswith("```"):
                    clean_response = clean_response[3:]
                if clean_response.endswith("```"):
                    clean_response = clean_response[:-3]
                clean_response = clean_response.strip()
                
                risk_data = json.loads(clean_response)
            except json.JSONDecodeError:
                response_text = "I encountered an error analyzing risk data. Please try again."
                options = [
                    {"id": "retry_risk", "label": "Retry", "icon": "🔄", "description": "Try again"},
                    {"id": "back_dashboard", "label": "Back to Dashboard", "icon": "📊", "description": "Return to overview"}
                ]
                
                await Conversation.add_message(
                    conversation["conversation_id"],
                    "assistant",
                    response_text,
                    {"type": "error", "options": options}
                )
                
                return {
                    "content": response_text,
                    "type": "error",
                    "options": options
                }
            
            response_text = "Water Risk Assessment Complete - Here's your detailed analysis:"
            options = [
                {"id": "compare_facilities", "label": "Compare All Facilities", "icon": "📊", "description": "Side-by-side comparison"},
                {"id": "view_risk_map", "label": "View Risk Map", "icon": "🗺️", "description": "Interactive map view"},
                {"id": "climate_scenarios", "label": "See Climate Scenarios", "icon": "📈", "description": "Future projections"},
                {"id": "mitigation_plan", "label": "Create Mitigation Plan", "icon": "🛡️", "description": "Build action plan"},
                {"id": "supplier_risk", "label": "Supplier Risk", "icon": "📦", "description": "Analyze supply chain"}
            ]
            
            await Conversation.add_message(
                conversation["conversation_id"],
                "assistant",
                response_text,
                {"type": "risk_analysis", "risk_data": risk_data, "options": options}
            )
            
            return {
                "content": response_text,
                "type": "risk_analysis",
                "risk_data": risk_data,
                "options": options
            }
        elif 'compare' in message_lower and 'facilities' in message_lower:
            # User wants to compare all facilities side-by-side
            comparison_data = {
                "facilities": [
                    {
                        "id": "FAC001",
                        "name": "Acme Manufacturing",
                        "location": "San Francisco, CA",
                        "usage_gal_month": 150000,
                        "cost_month": 4500,
                        "cost_per_1000_gal": 30.00,
                        "employees": 250,
                        "usage_per_employee": 600,
                        "risk_score": 2.1,
                        "risk_level": "Low-Medium",
                        "compliance_rate": 100,
                        "efficiency_rating": "Good"
                    },
                    {
                        "id": "FAC002",
                        "name": "Sunrise Hotel",
                        "location": "San Diego, CA",
                        "usage_gal_month": 85000,
                        "cost_month": 2800,
                        "cost_per_1000_gal": 32.94,
                        "employees": 150,
                        "usage_per_employee": 567,
                        "risk_score": 3.5,
                        "risk_level": "Medium-High",
                        "compliance_rate": 100,
                        "efficiency_rating": "Fair"
                    },
                    {
                        "id": "FAC003",
                        "name": "Tech Data Center",
                        "location": "San Jose, CA",
                        "usage_gal_month": 2500000,
                        "cost_month": 75000,
                        "cost_per_1000_gal": 30.00,
                        "employees": 50,
                        "usage_per_employee": 50000,
                        "risk_score": 3.8,
                        "risk_level": "High",
                        "compliance_rate": 100,
                        "efficiency_rating": "Needs Improvement"
                    }
                ],
                "comparison_insights": [
                    {"type": "warning", "message": "Data Center uses 91% of total water but has only 11% of employees"},
                    {"type": "info", "message": "San Francisco facility has best efficiency rating"},
                    {"type": "critical", "message": "San Jose facility in highest risk area - priority for mitigation"}
                ]
            }
            
            response_text = "Here's a side-by-side comparison of all your facilities:"
            options = [
                {"id": "mitigation_plan", "label": "Create Mitigation Plan", "icon": "🛡️", "description": "Build action plan"},
                {"id": "view_risk_map", "label": "View Risk Map", "icon": "🗺️", "description": "Interactive map view"},
                {"id": "back_dashboard", "label": "Back to Dashboard", "icon": "📊", "description": "Return to overview"}
            ]
            
            await Conversation.add_message(
                conversation["conversation_id"],
                "assistant",
                response_text,
                {"type": "facility_comparison", "comparison_data": comparison_data, "options": options}
            )
            
            return {
                "content": response_text,
                "type": "facility_comparison",
                "comparison_data": comparison_data,
                "options": options
            }
        elif 'view' in message_lower and 'risk' in message_lower and 'map' in message_lower:
            # User wants to see risk map
            map_data = {
                "facilities": [
                    {
                        "id": "FAC001",
                        "name": "Acme Manufacturing",
                        "location": "San Francisco, CA",
                        "coordinates": {"lat": 37.7749, "lon": -122.4194},
                        "risk_score": 2.1,
                        "risk_level": "Low-Medium",
                        "color": "#FFA500",
                        "usage_gal_month": 150000
                    },
                    {
                        "id": "FAC002",
                        "name": "Sunrise Hotel",
                        "location": "San Diego, CA",
                        "coordinates": {"lat": 32.7157, "lon": -117.1611},
                        "risk_score": 3.5,
                        "risk_level": "Medium-High",
                        "color": "#FF6B00",
                        "usage_gal_month": 85000
                    },
                    {
                        "id": "FAC003",
                        "name": "Tech Data Center",
                        "location": "San Jose, CA",
                        "coordinates": {"lat": 37.3382, "lon": -121.8863},
                        "risk_score": 3.8,
                        "risk_level": "High",
                        "color": "#FF0000",
                        "usage_gal_month": 2500000
                    }
                ],
                "legend": [
                    {"level": "Low", "range": "0-1.5", "color": "#00FF00"},
                    {"level": "Low-Medium", "range": "1.5-2.5", "color": "#FFA500"},
                    {"level": "Medium-High", "range": "2.5-3.5", "color": "#FF6B00"},
                    {"level": "High", "range": "3.5-4.5", "color": "#FF0000"},
                    {"level": "Extremely High", "range": "4.5-5.0", "color": "#8B0000"}
                ]
            }
            
            response_text = "Here's your water risk map showing all facilities:"
            options = [
                {"id": "compare_facilities", "label": "Compare All Facilities", "icon": "📊", "description": "Side-by-side comparison"},
                {"id": "climate_scenarios", "label": "See Climate Scenarios", "icon": "📈", "description": "Future projections"},
                {"id": "mitigation_plan", "label": "Create Mitigation Plan", "icon": "🛡️", "description": "Build action plan"}
            ]
            
            await Conversation.add_message(
                conversation["conversation_id"],
                "assistant",
                response_text,
                {"type": "risk_map", "map_data": map_data, "options": options}
            )
            
            return {
                "content": response_text,
                "type": "risk_map",
                "map_data": map_data,
                "options": options
            }
        elif ('climate' in message_lower and 'scenario' in message_lower) or ('see' in message_lower and 'climate' in message_lower):
            # User wants to see climate scenarios
            climate_data = {
                "scenarios": [
                    {
                        "year": 2030,
                        "facilities": [
                            {
                                "name": "Acme Manufacturing",
                                "location": "San Francisco, CA",
                                "current_risk": 2.1,
                                "projected_risk": 2.6,
                                "change": "+24%",
                                "key_changes": ["Drought frequency +15%", "Water stress +20%"]
                            },
                            {
                                "name": "Sunrise Hotel",
                                "location": "San Diego, CA",
                                "current_risk": 3.5,
                                "projected_risk": 4.1,
                                "change": "+17%",
                                "key_changes": ["Drought frequency +25%", "Water stress +15%"]
                            },
                            {
                                "name": "Tech Data Center",
                                "location": "San Jose, CA",
                                "current_risk": 3.8,
                                "projected_risk": 4.4,
                                "change": "+16%",
                                "key_changes": ["Extreme water stress", "Groundwater depletion critical"]
                            }
                        ]
                    },
                    {
                        "year": 2040,
                        "facilities": [
                            {
                                "name": "Acme Manufacturing",
                                "location": "San Francisco, CA",
                                "current_risk": 2.1,
                                "projected_risk": 3.1,
                                "change": "+48%",
                                "key_changes": ["Drought frequency +30%", "Water stress +40%", "Regulatory restrictions likely"]
                            },
                            {
                                "name": "Sunrise Hotel",
                                "location": "San Diego, CA",
                                "current_risk": 3.5,
                                "projected_risk": 4.5,
                                "change": "+29%",
                                "key_changes": ["Extreme drought conditions", "Water stress 80%+", "Allocation cuts expected"]
                            },
                            {
                                "name": "Tech Data Center",
                                "location": "San Jose, CA",
                                "current_risk": 3.8,
                                "projected_risk": 4.8,
                                "change": "+26%",
                                "key_changes": ["Extremely high risk", "Aquifer depletion severe", "Alternative sources critical"]
                            }
                        ]
                    },
                    {
                        "year": 2050,
                        "facilities": [
                            {
                                "name": "Acme Manufacturing",
                                "location": "San Francisco, CA",
                                "current_risk": 2.1,
                                "projected_risk": 3.6,
                                "change": "+71%",
                                "key_changes": ["High water stress", "Drought frequency +50%", "Major infrastructure investment needed"]
                            },
                            {
                                "name": "Sunrise Hotel",
                                "location": "San Diego, CA",
                                "current_risk": 3.5,
                                "projected_risk": 4.9,
                                "change": "+40%",
                                "key_changes": ["Extreme risk level", "Severe water scarcity", "Desalination may be required"]
                            },
                            {
                                "name": "Tech Data Center",
                                "location": "San Jose, CA",
                                "current_risk": 3.8,
                                "projected_risk": 5.0,
                                "change": "+32%",
                                "key_changes": ["Maximum risk level", "Groundwater unavailable", "Relocation may be necessary"]
                            }
                        ]
                    }
                ],
                "recommendations": [
                    {"priority": "Critical", "action": "Implement water recycling at Data Center immediately", "timeline": "2026"},
                    {"priority": "High", "action": "Diversify water sources for all facilities", "timeline": "2027-2028"},
                    {"priority": "High", "action": "Invest in drought-resilient infrastructure", "timeline": "2026-2030"},
                    {"priority": "Medium", "action": "Develop long-term water security strategy", "timeline": "2026"}
                ]
            }
            
            response_text = "Here are climate projections for your facilities through 2050:"
            options = [
                {"id": "mitigation_plan", "label": "Create Mitigation Plan", "icon": "🛡️", "description": "Build action plan"},
                {"id": "compare_facilities", "label": "Compare All Facilities", "icon": "📊", "description": "Side-by-side comparison"},
                {"id": "back_dashboard", "label": "Back to Dashboard", "icon": "📊", "description": "Return to overview"}
            ]
            
            await Conversation.add_message(
                conversation["conversation_id"],
                "assistant",
                response_text,
                {"type": "climate_scenarios", "climate_data": climate_data, "options": options}
            )
            
            return {
                "content": response_text,
                "type": "climate_scenarios",
                "climate_data": climate_data,
                "options": options
            }
        elif 'export' in message_lower and 'plan' in message_lower:
            # User wants to export the mitigation plan
            response_text = "Your mitigation plan is ready for export! Click the button below to download it as an HTML file that you can save or print as PDF."
            options = [
                {"id": "download_plan", "label": "Download Plan", "icon": "⬇️", "description": "Save HTML file"},
                {"id": "back_dashboard", "label": "Back to Dashboard", "icon": "📊", "description": "Return to overview"}
            ]
            
            # Include the plan data for download
            await Conversation.add_message(
                conversation["conversation_id"],
                "assistant",
                response_text,
                {"type": "export_ready", "options": options, "download_ready": True}
            )
            
            return {
                "content": response_text,
                "type": "export_ready",
                "download_ready": True,
                "options": options
            }
        elif 'dashboard' in message_lower:
            # Fetch real data from MongoDB and use Gemini AI for insights
            try:
                db = get_db()
                
                facilities = await db.facilities.find({"user_id": "demo"}).to_list(length=None)
                utility_bills = await db.utility_bills.find({"user_id": "demo"}).to_list(length=None)
                meter_data = await db.meter_data.find({"user_id": "demo"}).to_list(length=None)
                discharge_reports = await db.discharge_reports.find({"user_id": "demo"}).to_list(length=None)
                suppliers = await db.suppliers.find_one({"user_id": "demo"})
                
                # Check if we have any data
                if not facilities and not utility_bills and not meter_data:
                    response_text = "Welcome! Please upload your water data files to get started with your dashboard."
                    options = [
                        {"id": "upload_data", "label": "Upload Data", "icon": "📁", "description": "Upload files to begin"},
                        {"id": "learn_more", "label": "Learn More", "icon": "ℹ️", "description": "About the platform"}
                    ]
                    
                    await Conversation.add_message(
                        conversation["conversation_id"],
                        "assistant",
                        response_text,
                        {"type": "welcome", "options": options}
                    )
                    
                    return {
                        "content": response_text,
                        "type": "welcome",
                        "options": options
                    }
                
                # Prepare data for Gemini
                prompt = f"""Analyze the following water management data and create a comprehensive dashboard summary:

FACILITY DATA:
{json.dumps(facilities, indent=2, default=str) if facilities else "No facility data"}

UTILITY BILLS:
{json.dumps(utility_bills, indent=2, default=str) if utility_bills else "No utility bills"}

METER READINGS:
{json.dumps(meter_data, indent=2, default=str) if meter_data else "No meter data"}

DISCHARGE REPORTS:
{json.dumps(discharge_reports, indent=2, default=str) if discharge_reports else "No discharge reports"}

SUPPLIER DATA:
{json.dumps(suppliers.get("suppliers", []) if suppliers else [], indent=2, default=str)}

Generate a dashboard summary and return a JSON object with this EXACT structure:
{{
    "facilities": {{
        "total": <number of facilities>,
        "list": [
            {{"id": "facility_id", "name": "facility name", "usage": <monthly gallons>, "cost": <monthly cost>}}
        ]
    }},
    "total_usage": <total monthly gallons>,
    "total_cost": <total monthly cost>,
    "avg_cost_per_1000_gal": <calculated average>,
    "meters": {{
        "total": <number of meters>,
        "active": <number of active meters>,
        "consumption_breakdown": [
            {{"meter": "meter_id", "location": "location", "consumption": <gallons>, "percentage": <% of total>}}
        ]
    }},
    "compliance": {{
        "rate": <percentage 0-100>,
        "permits": <number of permits>,
        "passed_tests": <number passed>,
        "total_tests": <total tests>
    }},
    "suppliers": {{
        "total": <number of suppliers>,
        "high_risk": <number of high risk suppliers>,
        "total_spend": <total annual spend>,
        "high_risk_list": ["supplier names"]
    }},
    "insights": [
        {{"type": "warning|success|info", "message": "insight text", "priority": "high|medium|low"}}
    ],
    "recommendations": [
        {{"title": "recommendation title", "impact": "High|Medium|Low", "savings": "X-Y% or N/A"}}
    ]
}}

IMPORTANT:
- Calculate actual totals from the provided data
- Provide 3-5 specific insights based on the data
- Provide 3-5 actionable recommendations
- Return ONLY valid JSON, no markdown formatting"""

                # Call Gemini API with fallback to direct calculation
                dashboard_data = None
                try:
                    gemini_response = await gemini_service.generate_content(prompt)
                    clean_response = gemini_response.strip()
                    if clean_response.startswith("```json"):
                        clean_response = clean_response[7:]
                    if clean_response.startswith("```"):
                        clean_response = clean_response[3:]
                    if clean_response.endswith("```"):
                        clean_response = clean_response[:-3]
                    clean_response = clean_response.strip()
                    dashboard_data = json.loads(clean_response)
                except Exception as gemini_err:
                    print(f"Gemini dashboard failed, using fallback: {gemini_err}")
                    dashboard_data = _calculate_dashboard_from_data(
                        facilities, utility_bills, meter_data, discharge_reports, suppliers
                    )
                
                response_text = "Here's your water dashboard with key metrics and insights:"
                options = [
                    {"id": "efficiency_tips", "label": "Efficiency Tips", "icon": "💡", "description": "Get water-saving recommendations"},
                    {"id": "risk_analysis", "label": "Risk Analysis", "icon": "⚠️", "description": "Detailed risk assessment"},
                    {"id": "cost_breakdown", "label": "Cost Breakdown", "icon": "💰", "description": "Analyze spending patterns"},
                    {"id": "upload_more", "label": "Upload More Data", "icon": "📤", "description": "Add more documents"}
                ]
                
                await Conversation.add_message(
                    conversation["conversation_id"],
                    "assistant",
                    response_text,
                    {"type": "dashboard", "dashboard_data": dashboard_data, "options": options}
                )
                
                return {
                    "content": response_text,
                    "type": "dashboard",
                    "dashboard_data": dashboard_data,
                    "options": options
                }
            except Exception as e:
                print(f"Dashboard error: {e}")
                import traceback
                traceback.print_exc()
                response_text = f"I encountered an error loading the dashboard: {str(e)}. Please try again."
                options = [
                    {"id": "retry_dashboard", "label": "Retry", "icon": "🔄", "description": "Try again"},
                    {"id": "upload_data", "label": "Upload Data", "icon": "📤", "description": "Upload files"}
                ]
                
                await Conversation.add_message(
                    conversation["conversation_id"],
                    "assistant",
                    response_text,
                    {"type": "error", "options": options}
                )
                
                return {
                    "content": response_text,
                    "type": "error",
                    "options": options
                }
        elif any(word in message_lower for word in ['utility', 'bill']):
            response_text = "Upload your water utility bill (PDF, Excel, or CSV). I can handle 25+ utility formats and extract key information like water volume, costs, and meter readings."
            options = [
                {"id": "upload_file", "label": "Upload File", "icon": "📁", "description": "Choose file from computer"},
                {"id": "back_to_options", "label": "Back", "icon": "⬅️", "description": "Choose different document type"}
            ]
        elif any(word in message_lower for word in ['meter', 'reading']):
            response_text = "Upload meter logs (Excel/CSV) or connect smart meters. I can analyze consumption patterns, detect anomalies, and track usage trends."
            options = [
                {"id": "upload_file", "label": "Upload File", "icon": "📁", "description": "Upload meter data file"},
                {"id": "connect_iot", "label": "Connect IoT", "icon": "🔌", "description": "Connect smart meter"},
                {"id": "back_to_options", "label": "Back", "icon": "⬅️", "description": "Choose different document type"}
            ]
        elif any(word in message_lower for word in ['facility', 'info']):
            response_text = "Tell me about your facility. Upload a file or I can help you enter the information manually."
            options = [
                {"id": "upload_file", "label": "Upload File", "icon": "📁", "description": "Upload facility document"},
                {"id": "enter_manually", "label": "Enter Manually", "icon": "✍️", "description": "Fill in facility details"},
                {"id": "back_to_options", "label": "Back", "icon": "⬅️", "description": "Choose different document type"}
            ]
        elif any(word in message_lower for word in ['supplier', 'list']) and 'risk' not in message_lower:
            response_text = "Upload your supplier list (Excel/CSV) with columns: Supplier Name, Location, Product Category, Annual Spend. I'll analyze water risk across your supply chain."
            options = [
                {"id": "upload_file", "label": "Upload File", "icon": "📁", "description": "Upload supplier list"},
                {"id": "back_to_options", "label": "Back", "icon": "⬅️", "description": "Choose different document type"}
            ]
        elif any(word in message_lower for word in ['discharge', 'report', 'permit']):
            response_text = "Upload your discharge reports or NPDES permits (PDF/Excel/CSV). I'll extract permit information, pollutant levels, and compliance data."
            options = [
                {"id": "upload_file", "label": "Upload File", "icon": "📁", "description": "Upload discharge report"},
                {"id": "back_to_options", "label": "Back", "icon": "⬅️", "description": "Choose different document type"}
            ]
        elif 'supplier' in message_lower and 'risk' in message_lower:
            # Check if supplier data exists in database
            db = get_db()
            supplier_data = await db.suppliers.find_one({"user_id": "demo"})
            
            if supplier_data and supplier_data.get("suppliers"):
                # Display supplier risk analysis from existing data
                suppliers = supplier_data.get("suppliers", [])
                
                # Calculate risk levels
                high_risk = [s for s in suppliers if s.get("water_intensity_factor", 0) > 200000]
                medium_risk = [s for s in suppliers if 150000 < s.get("water_intensity_factor", 0) <= 200000]
                low_risk = [s for s in suppliers if s.get("water_intensity_factor", 0) <= 150000]
                
                total_spend = sum(s.get("annual_spend_usd", 0) for s in suppliers)
                high_risk_spend = sum(s.get("annual_spend_usd", 0) for s in high_risk)
                
                supplier_risk_data = {
                    "total_suppliers": len(suppliers),
                    "high_risk_count": len(high_risk),
                    "medium_risk_count": len(medium_risk),
                    "low_risk_count": len(low_risk),
                    "total_spend": total_spend,
                    "high_risk_spend": high_risk_spend,
                    "high_risk_percentage": round((len(high_risk) / len(suppliers) * 100), 1) if suppliers else 0,
                    "top_risk_suppliers": sorted(high_risk + medium_risk, key=lambda x: x.get("water_intensity_factor", 0), reverse=True)[:5],
                    "recommendations": [
                        {"priority": "High", "action": f"Engage with {len(high_risk)} high-risk suppliers", "impact": "Request water data via CDP"},
                        {"priority": "High", "action": "Prioritize suppliers in water-stressed regions", "impact": "Reduce supply chain risk"},
                        {"priority": "Medium", "action": "Diversify sourcing from high-risk areas", "impact": "Improve resilience"},
                        {"priority": "Medium", "action": "Set water efficiency requirements for suppliers", "impact": "Drive improvement"}
                    ],
                    "key_insights": [
                        {"type": "critical" if len(high_risk) > 3 else "warning", "message": f"{len(high_risk)} suppliers in high water-risk areas (>{200000} intensity factor)"},
                        {"type": "info", "message": f"High-risk suppliers represent ${high_risk_spend:,.0f} ({round(high_risk_spend/total_spend*100, 1)}%) of total spend"},
                        {"type": "warning" if len(high_risk) > 0 else "success", "message": f"Top risk categories: {', '.join(set([s.get('material_category', 'Unknown') for s in high_risk[:3]]))}"}
                    ]
                }
                
                response_text = "Here's your supply chain water risk analysis based on your uploaded supplier data:"
                options = [
                    {"id": "engagement_plan", "label": "Generate Engagement Plan", "icon": "📧", "description": "Create supplier outreach strategy"},
                    {"id": "mitigation_plan", "label": "Create Mitigation Plan", "icon": "🛡️", "description": "Build action plan"},
                    {"id": "back_dashboard", "label": "Back to Dashboard", "icon": "📊", "description": "Return to overview"}
                ]
                
                await Conversation.add_message(
                    conversation["conversation_id"],
                    "assistant",
                    response_text,
                    {"type": "supplier_risk_analysis", "supplier_risk_data": supplier_risk_data, "options": options}
                )
                
                return {
                    "content": response_text,
                    "type": "supplier_risk_analysis",
                    "supplier_risk_data": supplier_risk_data,
                    "options": options
                }
        elif 'engagement' in message_lower and 'plan' in message_lower:
            # Generate supplier engagement plan
            db = get_db()
            supplier_data = await db.suppliers.find_one({"user_id": "demo"})
            
            if supplier_data and supplier_data.get("suppliers"):
                suppliers = supplier_data.get("suppliers", [])
                
                # Categorize suppliers by risk
                high_risk = [s for s in suppliers if s.get("water_intensity_factor", 0) > 200000]
                medium_risk = [s for s in suppliers if 150000 < s.get("water_intensity_factor", 0) <= 200000]
                low_risk = [s for s in suppliers if s.get("water_intensity_factor", 0) <= 150000]
                
                engagement_plan = {
                    "plan_name": "Supplier Water Engagement Strategy 2026",
                    "created_date": "2026-03-13",
                    "total_suppliers": len(suppliers),
                    "tiers": [
                        {
                            "tier": 1,
                            "name": "High Priority Engagement",
                            "criteria": "High Risk + High Spend",
                            "supplier_count": len(high_risk),
                            "suppliers": [{"name": s["supplier_name"], "category": s["material_category"], "spend": s["annual_spend_usd"], "risk": "High"} for s in high_risk],
                            "actions": [
                                {"action": "Send CDP Water questionnaire", "timeline": "Within 30 days", "owner": "Procurement"},
                                {"action": "Request water withdrawal and consumption data", "timeline": "Q2 2026", "owner": "Sustainability"},
                                {"action": "Schedule water risk assessment calls", "timeline": "Q2 2026", "owner": "Supply Chain"},
                                {"action": "Set water reduction targets in contracts", "timeline": "Q3 2026", "owner": "Procurement"}
                            ],
                            "goals": {
                                "response_rate": "80%",
                                "data_quality": "Primary data from 60%",
                                "engagement_level": "Active collaboration"
                            }
                        },
                        {
                            "tier": 2,
                            "name": "Medium Priority Engagement",
                            "criteria": "Medium Risk or Medium Spend",
                            "supplier_count": len(medium_risk),
                            "suppliers": [{"name": s["supplier_name"], "category": s["material_category"], "spend": s["annual_spend_usd"], "risk": "Medium"} for s in medium_risk],
                            "actions": [
                                {"action": "Share water efficiency best practices", "timeline": "Q2 2026", "owner": "Sustainability"},
                                {"action": "Host quarterly water stewardship webinars", "timeline": "Quarterly", "owner": "Supply Chain"},
                                {"action": "Provide water risk assessment tools", "timeline": "Q3 2026", "owner": "Sustainability"},
                                {"action": "Recognize water leaders in supplier awards", "timeline": "Annual", "owner": "Procurement"}
                            ],
                            "goals": {
                                "response_rate": "50%",
                                "participation": "50% in webinars",
                                "engagement_level": "Awareness building"
                            }
                        },
                        {
                            "tier": 3,
                            "name": "Monitoring & Awareness",
                            "criteria": "Low Risk",
                            "supplier_count": len(low_risk),
                            "suppliers": [{"name": s["supplier_name"], "category": s["material_category"], "spend": s["annual_spend_usd"], "risk": "Low"} for s in low_risk[:3]],  # Show first 3
                            "actions": [
                                {"action": "Annual water risk screening", "timeline": "Annual", "owner": "Procurement"},
                                {"action": "Share industry water trends", "timeline": "Bi-annual", "owner": "Sustainability"},
                                {"action": "Monitor for risk changes", "timeline": "Ongoing", "owner": "Supply Chain"}
                            ],
                            "goals": {
                                "response_rate": "N/A",
                                "monitoring": "Annual check-in",
                                "engagement_level": "Maintain awareness"
                            }
                        }
                    ],
                    "timeline": {
                        "q1_2026": ["Finalize engagement strategy", "Prepare CDP questionnaires", "Identify key contacts"],
                        "q2_2026": ["Launch Tier 1 engagement", "Send CDP surveys", "Host first webinar"],
                        "q3_2026": ["Analyze responses", "Set supplier targets", "Provide tools and resources"],
                        "q4_2026": ["Review progress", "Recognize leaders", "Plan 2027 strategy"]
                    },
                    "kpis": [
                        {"metric": "Tier 1 Response Rate", "target": "80%", "measurement": "CDP survey completion"},
                        {"metric": "Primary Data Collection", "target": "60% of Tier 1", "measurement": "Supplier-reported data"},
                        {"metric": "Webinar Participation", "target": "50% of Tier 2", "measurement": "Attendance records"},
                        {"metric": "Water Reduction Commitments", "target": "5 suppliers", "measurement": "Signed agreements"}
                    ],
                    "resources": [
                        {"resource": "CDP Water Questionnaire", "description": "Standard water disclosure survey", "cost": "$0"},
                        {"resource": "Water Risk Assessment Tool", "description": "WRI Aqueduct access for suppliers", "cost": "$5,000"},
                        {"resource": "Webinar Platform", "description": "Quarterly engagement sessions", "cost": "$2,000/year"},
                        {"resource": "Consultant Support", "description": "Expert guidance for complex suppliers", "cost": "$15,000"}
                    ],
                    "communication_templates": {
                        "tier1_email": "Subject: Partnership Opportunity - Water Stewardship\n\nDear [Supplier],\n\nAs part of our commitment to sustainable water management, we're engaging key suppliers to understand and reduce water-related risks in our supply chain. Your company has been identified as a strategic partner in this initiative.\n\nWe invite you to complete the CDP Water questionnaire to help us understand your water use, risks, and management practices. This information will help us work together to build resilience and identify opportunities for improvement.\n\nTimeline: Please complete by [Date]\nSupport: Our team is available to assist\n\nThank you for your partnership.",
                        "tier2_invitation": "Subject: Water Stewardship Webinar Invitation\n\nDear [Supplier],\n\nYou're invited to our quarterly Water Stewardship Webinar where we'll share:\n- Industry water trends and best practices\n- Tools and resources for water management\n- Success stories from leading suppliers\n\nDate: [Date]\nTime: [Time]\nRegister: [Link]"
                    }
                }
                
                response_text = "Here's your comprehensive Supplier Engagement Plan:"
                options = [
                    {"id": "download_plan", "label": "Download Plan", "icon": "📄", "description": "Export as document"},
                    {"id": "mitigation_plan", "label": "Create Mitigation Plan", "icon": "🛡️", "description": "Build action plan"},
                    {"id": "back_dashboard", "label": "Back to Dashboard", "icon": "📊", "description": "Return to overview"}
                ]
                
                await Conversation.add_message(
                    conversation["conversation_id"],
                    "assistant",
                    response_text,
                    {"type": "engagement_plan", "engagement_plan": engagement_plan, "options": options}
                )
                
                return {
                    "content": response_text,
                    "type": "engagement_plan",
                    "engagement_plan": engagement_plan,
                    "options": options
                }
            else:
                response_text = "Please upload your supplier list first to generate an engagement plan."
                options = [
                    {"id": "upload_file", "label": "Upload Supplier List", "icon": "📁", "description": "Upload supplier data"}
                ]
                
                await Conversation.add_message(
                    conversation["conversation_id"],
                    "assistant",
                    response_text,
                    {"type": "text", "options": options}
                )
                
                return {
                    "content": response_text,
                    "type": "text",
                    "options": options
                }
        elif any(word in message_lower for word in ['dashboard', 'view', 'show']):
            response_text = "I can show you your water dashboard with usage trends, efficiency metrics, and risk assessments. Would you like to see your current water overview?"
            options = [
                {"id": "show_dashboard", "label": "Yes, Show Dashboard", "icon": "📊", "description": "View water overview"},
                {"id": "stay_chat", "label": "Stay in Chat", "icon": "💬", "description": "Continue conversation"}
            ]
        elif any(word in message_lower for word in ['risk', 'assessment', 'stress']):
            response_text = "I can assess water risk at your facilities using WRI Aqueduct data. This includes physical quantity risk, quality risk, regulatory risk, and reputational risk. Would you like me to analyze your location?"
            options = [
                {"id": "analyze_risk", "label": "Yes, Analyze Risk", "icon": "🔍", "description": "Run risk assessment"},
                {"id": "back_dashboard", "label": "Back to Dashboard", "icon": "📊", "description": "Return to overview"}
            ]
        elif any(word in message_lower for word in ['efficiency', 'save', 'reduce']):
            response_text = "I can identify water efficiency opportunities ranked by ROI. This includes leak detection, fixture upgrades, cooling tower optimization, and water recycling. Would you like to see recommendations?"
            options = None
        elif any(word in message_lower for word in ['compliance', 'permit', 'regulation']):
            response_text = "I can help with compliance tracking, permit management, and regulatory reporting. This includes NPDES permits, discharge monitoring, and deadline tracking. What would you like to know?"
            options = None
        elif any(word in message_lower for word in ['footprint', 'calculate', 'consumption']) and 'yes' not in message_lower:
            response_text = "I can calculate your water footprint including direct operational use and indirect supply chain impacts. This helps identify hotspots and set reduction targets. Shall we start?"
            options = [
                {"id": "calculate_footprint", "label": "Yes, Calculate", "icon": "💧", "description": "Calculate water footprint"},
                {"id": "back_dashboard", "label": "Back to Dashboard", "icon": "📊", "description": "Return to overview"}
            ]
        elif (('yes' in message_lower and 'calculate' in message_lower) or 
              (('yes' in message_lower or 'calculate' in message_lower) and 'footprint' in message_lower)):
            # Calculate water footprint from existing data using Gemini AI
            db = get_db()
            
            # Fetch REAL data from MongoDB
            facilities = await db.facilities.find({"user_id": "demo"}).to_list(length=None)
            utility_bills = await db.utility_bills.find({"user_id": "demo"}).to_list(length=None)
            meter_data = await db.meter_data.find({"user_id": "demo"}).to_list(length=None)
            discharge_reports = await db.discharge_reports.find({"user_id": "demo"}).to_list(length=None)
            suppliers = await db.suppliers.find_one({"user_id": "demo"})
            
            # Check if we have data
            if not facilities and not utility_bills and not meter_data:
                response_text = "I need your facility data, utility bills, or meter readings to calculate water footprint. Please upload these files first."
                options = [
                    {"id": "upload_data", "label": "Upload Data", "icon": "📁", "description": "Upload required files"},
                    {"id": "back_dashboard", "label": "Back to Dashboard", "icon": "📊", "description": "Return to overview"}
                ]
            else:
                # Prepare data for Gemini
                data_summary = {
                    "facilities": facilities if facilities else [],
                    "utility_bills": utility_bills if utility_bills else [],
                    "meter_data": meter_data if meter_data else [],
                    "discharge_reports": discharge_reports if discharge_reports else [],
                    "suppliers": suppliers.get("suppliers", []) if suppliers else []
                }
                
                # Create prompt for Gemini
                prompt = f"""Analyze the following water data and calculate a comprehensive water footprint:

FACILITY DATA:
{json.dumps(facilities, indent=2, default=str) if facilities else "No facility data"}

UTILITY BILLS:
{json.dumps(utility_bills, indent=2, default=str) if utility_bills else "No utility bills"}

METER READINGS:
{json.dumps(meter_data, indent=2, default=str) if meter_data else "No meter data"}

DISCHARGE REPORTS:
{json.dumps(discharge_reports, indent=2, default=str) if discharge_reports else "No discharge reports"}

SUPPLIER DATA:
{json.dumps(suppliers.get("suppliers", []) if suppliers else [], indent=2, default=str)}

Calculate and return a JSON object with this EXACT structure:
{{
    "direct_footprint": {{
        "withdrawal": <total gallons withdrawn>,
        "consumption": <total gallons consumed>,
        "discharge": <total gallons discharged>,
        "consumption_rate": <percentage consumed>,
        "by_facility": [
            {{"name": "facility name", "location": "city, state", "withdrawal": <gallons>, "percentage": <% of total>}}
        ]
    }},
    "indirect_footprint": {{
        "total": <total indirect footprint from suppliers>,
        "percentage_of_total": <% of total footprint>,
        "top_suppliers": [
            {{"name": "supplier name", "category": "category", "footprint": <gallons>, "percentage": <% of indirect>}}
        ]
    }},
    "total_footprint": <direct + indirect>,
    "water_intensity": {{
        "per_million_revenue": <gallons per $1M revenue>,
        "per_employee": <gallons per employee>,
        "per_facility": <gallons per facility>
    }},
    "benchmarking": {{
        "your_intensity": <your intensity>,
        "industry_average": 150000,
        "best_in_class": 80000,
        "vs_average": <% difference from average>,
        "vs_best": <% difference from best>
    }},
    "insights": [
        {{"type": "success|warning|critical|info", "message": "insight text"}}
    ],
    "recommendations": [
        {{"priority": "High|Medium|Low", "action": "action text", "impact": "impact text"}}
    ]
}}

IMPORTANT:
- Calculate actual totals from the provided data
- For facilities without employee count, estimate based on facility type
- For revenue, estimate based on facility size/type if not provided
- Provide specific, actionable insights based on the actual data
- Return ONLY valid JSON, no markdown formatting"""

                # Call Gemini API
                gemini_response = await gemini_service.generate_content(prompt)
                
                # Parse Gemini response
                try:
                    # Clean response (remove markdown if present)
                    clean_response = gemini_response.strip()
                    if clean_response.startswith("```json"):
                        clean_response = clean_response[7:]
                    if clean_response.startswith("```"):
                        clean_response = clean_response[3:]
                    if clean_response.endswith("```"):
                        clean_response = clean_response[:-3]
                    clean_response = clean_response.strip()
                    
                    footprint_data = json.loads(clean_response)
                except json.JSONDecodeError as e:
                    # Fallback if JSON parsing fails
                    footprint_data = {
                        "error": "Failed to parse AI response",
                        "raw_response": gemini_response
                    }
                    response_text = "I encountered an error analyzing your data. Please try again."
                    options = [
                        {"id": "retry_calculate", "label": "Retry", "icon": "🔄", "description": "Try again"},
                        {"id": "back_dashboard", "label": "Back to Dashboard", "icon": "📊", "description": "Return to overview"}
                    ]
                    
                    await Conversation.add_message(
                        conversation["conversation_id"],
                        "assistant",
                        response_text,
                        {"type": "error", "options": options}
                    )
                    
                    return {
                        "content": response_text,
                        "type": "error",
                        "options": options
                    }
                
                # Success - return footprint analysis
                response_text = "Here's your comprehensive water footprint analysis:"
                options = [
                    {"id": "set_targets", "label": "Set Reduction Targets", "icon": "🎯", "description": "Define water goals"},
                    {"id": "back_dashboard", "label": "Back to Dashboard", "icon": "📊", "description": "Return to overview"}
                ]
                
                await Conversation.add_message(
                    conversation["conversation_id"],
                    "assistant",
                    response_text,
                    {"type": "water_footprint", "footprint_data": footprint_data, "options": options}
                )
                
                return {
                    "content": response_text,
                    "type": "water_footprint",
                    "footprint_data": footprint_data,
                    "options": options
                }
        elif 'set' in message_lower and ('target' in message_lower or 'reduction' in message_lower):
            # User wants to set reduction targets using Gemini AI
            db = get_db()
            
            # Fetch data from previous analyses
            facilities = await db.facilities.find({"user_id": "demo"}).to_list(length=None)
            utility_bills = await db.utility_bills.find({"user_id": "demo"}).to_list(length=None)
            suppliers = await db.suppliers.find_one({"user_id": "demo"})
            
            # Get the last footprint calculation from conversation history
            last_messages = await Conversation.get_messages(conversation["conversation_id"], limit=10)
            footprint_data = None
            for msg in reversed(last_messages):
                if msg.get("metadata") and msg["metadata"].get("type") == "water_footprint":
                    footprint_data = msg["metadata"].get("footprint_data")
                    break
            
            if not footprint_data:
                response_text = "Please calculate your water footprint first before setting reduction targets."
                options = [
                    {"id": "calculate_footprint", "label": "Calculate Footprint", "icon": "💧", "description": "Calculate first"},
                    {"id": "back_dashboard", "label": "Back to Dashboard", "icon": "📊", "description": "Return to overview"}
                ]
            else:
                # Create prompt for Gemini to generate realistic reduction targets
                prompt = f"""Based on the following water footprint analysis and facility data, generate realistic water reduction target scenarios:

CURRENT WATER FOOTPRINT:
{json.dumps(footprint_data, indent=2, default=str)}

FACILITY DATA:
{json.dumps(facilities, indent=2, default=str) if facilities else "No facility data"}

UTILITY BILLS:
{json.dumps(utility_bills, indent=2, default=str) if utility_bills else "No utility bills"}

Generate 3 reduction target scenarios (Conservative, Moderate, Aggressive) and return a JSON object with this EXACT structure:
{{
    "baseline": {{
        "year": 2026,
        "footprint": <current total footprint>,
        "intensity": <current intensity per $1M revenue>
    }},
    "scenarios": [
        {{
            "name": "Conservative",
            "reduction_percent": <15-20%>,
            "target_year": <2028-2029>,
            "target_footprint": <calculated value>,
            "annual_reduction": <calculated value>,
            "key_actions": ["action 1", "action 2", "action 3"],
            "investment": "$XX,XXX",
            "annual_savings": "$XX,XXX",
            "difficulty": "Low"
        }},
        {{
            "name": "Moderate (Recommended)",
            "reduction_percent": <25-35%>,
            "target_year": <2030-2031>,
            "target_footprint": <calculated value>,
            "annual_reduction": <calculated value>,
            "key_actions": ["action 1", "action 2", "action 3", "action 4"],
            "investment": "$XXX,XXX",
            "annual_savings": "$XX,XXX",
            "difficulty": "Medium"
        }},
        {{
            "name": "Aggressive",
            "reduction_percent": <40-50%>,
            "target_year": <2033-2035>,
            "target_footprint": <calculated value>,
            "annual_reduction": <calculated value>,
            "key_actions": ["action 1", "action 2", "action 3", "action 4", "action 5"],
            "investment": "$XXX,XXX",
            "annual_savings": "$XXX,XXX",
            "difficulty": "High"
        }}
    ],
    "milestones": [
        {{"year": 2026, "target": "milestone description", "reduction": "X%"}},
        {{"year": 2027, "target": "milestone description", "reduction": "X%"}},
        {{"year": 2028, "target": "milestone description", "reduction": "X%"}},
        {{"year": 2030, "target": "milestone description", "reduction": "X%"}}
    ],
    "alignment": {{
        "science_based": "description of SBTN alignment",
        "sdg": "description of SDG alignment",
        "industry": "description of industry benchmark alignment"
    }}
}}

IMPORTANT:
- Base recommendations on the ACTUAL facility types and water usage patterns
- Provide specific, actionable key_actions relevant to the facilities
- Calculate realistic investment and savings based on facility size
- Ensure milestones are achievable and progressive
- Return ONLY valid JSON, no markdown formatting"""

                # Call Gemini API
                gemini_response = await gemini_service.generate_content(prompt)
                
                # Parse Gemini response
                try:
                    # Clean response
                    clean_response = gemini_response.strip()
                    if clean_response.startswith("```json"):
                        clean_response = clean_response[7:]
                    if clean_response.startswith("```"):
                        clean_response = clean_response[3:]
                    if clean_response.endswith("```"):
                        clean_response = clean_response[:-3]
                    clean_response = clean_response.strip()
                    
                    targets_data = json.loads(clean_response)
                except json.JSONDecodeError as e:
                    response_text = "I encountered an error generating reduction targets. Please try again."
                    options = [
                        {"id": "retry_targets", "label": "Retry", "icon": "🔄", "description": "Try again"},
                        {"id": "back_dashboard", "label": "Back to Dashboard", "icon": "📊", "description": "Return to overview"}
                    ]
                    
                    await Conversation.add_message(
                        conversation["conversation_id"],
                        "assistant",
                        response_text,
                        {"type": "error", "options": options}
                    )
                    
                    return {
                        "content": response_text,
                        "type": "error",
                        "options": options
                    }
                
                response_text = "Here are your water reduction target scenarios based on your current footprint:"
                options = [
                    {"id": "select_moderate", "label": "Select Moderate Target", "icon": "✅", "description": "30% by 2030"},
                    {"id": "custom_target", "label": "Create Custom Target", "icon": "⚙️", "description": "Define your own"},
                    {"id": "back_dashboard", "label": "Back to Dashboard", "icon": "📊", "description": "Return to overview"}
                ]
                
                await Conversation.add_message(
                    conversation["conversation_id"],
                    "assistant",
                    response_text,
                    {"type": "reduction_targets", "targets_data": targets_data, "options": options}
                )
                
                return {
                    "content": response_text,
                    "type": "reduction_targets",
                    "targets_data": targets_data,
                    "options": options
                }
        elif any(word in message_lower for word in ['strategy', 'mitigation']) and not ('yes' in message_lower or 'create' in message_lower):
            response_text = "I can help build a comprehensive water stewardship strategy with reduction targets, implementation timelines, and KPIs. Would you like to create a customized plan?"
            options = [
                {"id": "create_plan", "label": "Yes, Create Plan", "icon": "✅", "description": "Build mitigation strategy"},
                {"id": "back_dashboard", "label": "Back to Dashboard", "icon": "📊", "description": "Return to overview"}
            ]
        elif ('yes' in message_lower and ('create' in message_lower or 'build' in message_lower)) or ('create' in message_lower and ('mitigation' in message_lower or 'plan' in message_lower)):
            # User confirmed mitigation plan creation - generate with AI using real DB data
            db = get_db()
            
            # Fetch real data from MongoDB
            facilities_raw = await db.facilities.find({"user_id": "demo"}).to_list(length=None)
            utility_bills_raw = await db.utility_bills.find({"user_id": "demo"}).to_list(length=None)
            meter_data_raw = await db.meter_data.find({"user_id": "demo"}).to_list(length=None)
            discharge_reports_raw = await db.discharge_reports.find({"user_id": "demo"}).to_list(length=None)
            
            # Build facility_data from real DB
            total_usage = sum(b.get("water_volume_gallons", 0) for b in utility_bills_raw)
            total_cost = sum(b.get("total_cost", 0) for b in utility_bills_raw)
            if not total_usage and meter_data_raw:
                total_usage = sum(m.get("consumption", 0) for m in meter_data_raw)
                total_cost = int(total_usage * 0.03)
            
            facility_data = {
                "facilities": [
                    {
                        "id": f.get("facility_id", ""),
                        "name": f.get("facility_name", ""),
                        "location": f.get("city", "") + ", " + f.get("state", ""),
                        "usage_gal_month": next((b.get("water_volume_gallons", 0) for b in utility_bills_raw if b.get("facility_id") == f.get("facility_id")), 0),
                        "employees": f.get("employee_count", 0)
                    } for f in facilities_raw
                ] if facilities_raw else [],
                "total_usage": total_usage,
                "total_cost": total_cost,
                "meters": len(meter_data_raw),
                "compliance_rate": 100
            }
            
            # Get risk data from last risk analysis in conversation history
            last_msgs = await Conversation.get_messages(conversation["conversation_id"], limit=20)
            risk_data = None
            for msg in reversed(last_msgs):
                if msg.get("metadata") and msg["metadata"].get("type") == "risk_analysis":
                    risk_data = msg["metadata"].get("risk_data")
                    break
            
            if not risk_data:
                risk_data = {
                    "overall_risk": "Medium",
                    "facilities": [
                        {"name": f.get("facility_name", ""), "location": f.get("city", ""), "risk_level": "Medium", "key_risks": ["Water stress", "Efficiency opportunities"]}
                        for f in facilities_raw
                    ] if facilities_raw else []
                }
            
            # Generate AI-powered mitigation plan
            try:
                ai_result = await gemini_service.generate_mitigation_plan(facility_data, risk_data)
                
                if ai_result.get("success"):
                    mitigation_plan = ai_result["mitigation_plan"]
                else:
                    # Use fallback if AI generation failed
                    mitigation_plan = ai_result["mitigation_plan"]
                    
            except Exception as e:
                print(f"Error generating AI plan: {e}")
                # Use fallback plan
                mitigation_plan = {
                    "plan_name": "Water Risk Mitigation Strategy 2026",
                    "created_date": "2026-03-13",
                    "timeline": "12 months",
                    "total_investment": 450000,
                    "expected_savings": 180000,
                    "roi_months": 30,
                    "phases": [
                        {
                            "phase": 1,
                            "name": "Assessment & Planning",
                            "duration": "Months 1-2",
                            "status": "ready",
                            "actions": [
                                {"task": "Complete water audit at all facilities", "owner": "Operations", "deadline": "Month 1", "cost": 15000},
                                {"task": "Install smart meters at Data Center", "owner": "Facilities", "deadline": "Month 2", "cost": 50000},
                                {"task": "Baseline water quality testing", "owner": "EHS", "deadline": "Month 2", "cost": 10000}
                            ]
                        },
                        {
                            "phase": 2,
                            "name": "Infrastructure Upgrades",
                            "duration": "Months 3-6",
                            "status": "pending",
                            "actions": [
                                {"task": "Install water recycling system at Data Center", "owner": "Engineering", "deadline": "Month 5", "cost": 250000},
                                {"task": "Upgrade cooling tower efficiency", "owner": "Facilities", "deadline": "Month 4", "cost": 75000},
                                {"task": "Replace high-flow fixtures", "owner": "Facilities", "deadline": "Month 3", "cost": 20000}
                            ]
                        },
                        {
                            "phase": 3,
                            "name": "Monitoring & Optimization",
                            "duration": "Months 7-12",
                            "status": "pending",
                            "actions": [
                                {"task": "Implement real-time monitoring dashboard", "owner": "IT", "deadline": "Month 7", "cost": 15000},
                                {"task": "Train staff on water efficiency", "owner": "HR", "deadline": "Month 8", "cost": 5000},
                                {"task": "Quarterly performance reviews", "owner": "Sustainability", "deadline": "Ongoing", "cost": 10000}
                            ]
                        }
                    ],
                    "kpis": [
                        {"metric": "Total Water Consumption", "baseline": "2,735,000 gal/month", "target": "2,050,000 gal/month", "reduction": "25%"},
                        {"metric": "Water Cost", "baseline": "$82,300/month", "target": "$67,000/month", "reduction": "19%"},
                        {"metric": "Water Recycling Rate", "baseline": "0%", "target": "40%", "increase": "40%"},
                        {"metric": "Compliance Rate", "baseline": "100%", "target": "100%", "maintain": True}
                    ],
                    "risk_mitigation": [
                        {"risk": "Data Center water stress", "mitigation": "Water recycling system", "impact": "High", "timeline": "Month 5"},
                        {"risk": "Drought in San Diego", "mitigation": "Diversify water sources", "impact": "Medium", "timeline": "Month 6"},
                        {"risk": "Regulatory changes", "mitigation": "Compliance monitoring", "impact": "Medium", "timeline": "Ongoing"}
                    ]
                }
            
            response_text = "Here's your customized Water Risk Mitigation Plan:"
            options = [
                {"id": "export_plan", "label": "Export Plan", "icon": "📄", "description": "Download as PDF"},
                {"id": "back_dashboard", "label": "Back to Dashboard", "icon": "📊", "description": "Return to overview"}
            ]
            
            await Conversation.add_message(
                conversation["conversation_id"],
                "assistant",
                response_text,
                {"type": "mitigation_plan", "mitigation_plan": mitigation_plan, "options": options}
            )
            
            return {
                "content": response_text,
                "type": "mitigation_plan",
                "mitigation_plan": mitigation_plan,
                "options": options
            }
        elif any(word in message_lower for word in ['supply chain', 'supplier', 'vendor']):
            response_text = "I can assess water risk across your supply chain by analyzing supplier locations against water stress data. This helps prioritize engagement and sourcing decisions. Interested?"
            options = None
        else:
            options = None
            # Try Gemini if available, otherwise use default response
            try:
                gemini_response = await gemini_service.process_chat_message(
                    user_message=message,
                    session_id=session_id,
                    conversation_id=conversation["conversation_id"]
                )
                response_text = gemini_response.get("response", "I'm here to help with water stewardship! I can assist with data uploads, risk assessments, efficiency recommendations, compliance tracking, and more. What would you like to explore?")
            except Exception as e:
                print(f"Gemini service error: {e}")
                response_text = "I'm here to help with water stewardship! I can assist with:\n\n• Uploading and analyzing water data\n• Assessing water risk at your facilities\n• Identifying efficiency opportunities\n• Tracking compliance and permits\n• Calculating water footprints\n• Building stewardship strategies\n\nWhat would you like to do?"
        
        # Add assistant response
        await Conversation.add_message(
            conversation["conversation_id"],
            "assistant",
            response_text,
            {"type": "text", "options": options if 'options' in locals() else None}
        )
        
        return {
            "content": response_text,
            "type": "text",
            "data": None,
            "options": options if 'options' in locals() else None
        }
        
    except Exception as e:
        print(f"Chat error: {e}")
        return {
            "content": "I'm here to help with water stewardship! How can I assist you today?",
            "type": "text",
            "data": None,
            "options": None
        }