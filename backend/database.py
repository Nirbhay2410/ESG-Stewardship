from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid

# Use same .env as rest of app (backend/.env)
from config import load_env
load_env()

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "water_stewardship")

client: Optional[AsyncIOMotorClient] = None
db = None

async def init_db():
    """Initialize MongoDB connection"""
    global client, db
    try:
        client = AsyncIOMotorClient(MONGO_URI)
        db = client[DATABASE_NAME]
        
        # Create indexes
        await create_indexes()
        print(f"Connected to MongoDB: {DATABASE_NAME}")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        raise

async def create_indexes():
    """Create necessary indexes for collections"""
    
    # Users collection
    await db.users.create_index([("email", ASCENDING)], unique=True)
    await db.users.create_index([("created_at", DESCENDING)])
    
    # Conversations collection
    await db.conversations.create_index([("user_id", ASCENDING)])
    await db.conversations.create_index([("created_at", DESCENDING)])
    await db.conversations.create_index([("session_id", ASCENDING)])
    
    # Uploaded files collection
    await db.uploaded_files.create_index([("user_id", ASCENDING)])
    await db.uploaded_files.create_index([("uploaded_at", DESCENDING)])
    await db.uploaded_files.create_index([("file_type", ASCENDING)])
    
    # Facilities collection
    await db.facilities.create_index([("user_id", ASCENDING)])
    await db.facilities.create_index([("location", "2dsphere")])
    await db.facilities.create_index([("created_at", DESCENDING)])
    
    # Water data collection
    await db.water_data.create_index([("facility_id", ASCENDING)])
    await db.water_data.create_index([("timestamp", DESCENDING)])
    await db.water_data.create_index([("data_type", ASCENDING)])
    
    # Risk assessments collection
    await db.risk_assessments.create_index([("facility_id", ASCENDING)])
    await db.risk_assessments.create_index([("assessment_date", DESCENDING)])
    
    # WRI data indexes (already created by ingest script)
    print("Database indexes created/verified")

# Database models
class User:
    @staticmethod
    async def create_user(email: str, name: str, company: Optional[str] = None):
        """Create a new user"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": email,
            "name": name,
            "company": company,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "preferences": {
                "theme": "dark",
                "notifications": True,
                "language": "en"
            }
        }
        result = await db.users.insert_one(user_data)
        return user_data

class Conversation:
    @staticmethod
    async def create_conversation(user_id: str, session_id: str = None):
        """Create a new conversation"""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        conversation_data = {
            "conversation_id": str(uuid.uuid4()),
            "user_id": user_id,
            "session_id": session_id,
            "messages": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "status": "active"
        }
        result = await db.conversations.insert_one(conversation_data)
        return conversation_data

    @staticmethod
    async def add_message(conversation_id: str, role: str, content: str, metadata: Dict = None):
        """Add a message to conversation"""
        message = {
            "message_id": str(uuid.uuid4()),
            "role": role,  # "user", "assistant", "system"
            "content": content,
            "timestamp": datetime.utcnow(),
            "metadata": metadata or {}
        }
        
        await db.conversations.update_one(
            {"conversation_id": conversation_id},
            {
                "$push": {"messages": message},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return message

    @staticmethod
    async def get_messages(conversation_id: str, limit: int = 20):
        """Get messages from a conversation"""
        conversation = await db.conversations.find_one(
            {"conversation_id": conversation_id},
            {"messages": 1}
        )
        if not conversation:
            return []
        messages = conversation.get("messages", [])
        return messages[-limit:] if limit else messages


class UploadedFile:
    @staticmethod
    async def create_file_record(
        user_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        s3_key: str = None,
        metadata: Dict = None
    ):
        """Create a record for uploaded file"""
        file_data = {
            "file_id": str(uuid.uuid4()),
            "user_id": user_id,
            "filename": filename,
            "file_type": file_type,  # "utility_bill", "meter_data", "discharge_report", etc.
            "file_size": file_size,
            "s3_key": s3_key,
            "uploaded_at": datetime.utcnow(),
            "status": "uploaded",
            "metadata": metadata or {},
            "extracted_data": None,
            "processing_status": "pending"
        }
        result = await db.uploaded_files.insert_one(file_data)
        return file_data

    @staticmethod
    async def update_extracted_data(file_id: str, extracted_data: Dict):
        """Update extracted data from file"""
        await db.uploaded_files.update_one(
            {"file_id": file_id},
            {
                "$set": {
                    "extracted_data": extracted_data,
                    "processing_status": "completed",
                    "processed_at": datetime.utcnow()
                }
            }
        )

class Facility:
    @staticmethod
    async def create_facility(
        user_id: str,
        name: str,
        address: str,
        location: Dict,
        facility_type: str,
        metadata: Dict = None
    ):
        """Create a new facility"""
        facility_data = {
            "facility_id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": name,
            "address": address,
            "location": location,  # GeoJSON format
            "facility_type": facility_type,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "metadata": metadata or {},
            "water_risk_score": None,
            "compliance_status": "unknown"
        }
        result = await db.facilities.insert_one(facility_data)
        return facility_data

# Get database instance
def get_db():
    return db

# Close database connection
async def close_db():
    if client:
        client.close()