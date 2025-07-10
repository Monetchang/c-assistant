from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorCollection
from app.models.chat_message_mongo import ChatMessageMongo
from bson import ObjectId
from datetime import datetime
from app.schemas.chat_message import ChatMessage

class CRUDChatMessageMongo:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def get_by_chat(self, thread_id: str, skip: int = 0, limit: int = 100) -> List[ChatMessage]:
        cursor = self.collection.find({"thread_id": thread_id}).skip(skip).limit(limit).sort("created_at", 1)
        return [ChatMessage(**{**doc, "id": str(doc["_id"])}) async for doc in cursor]

    async def create_with_chat(self, obj_in: dict, thread_id: str) -> ChatMessageMongo:
        obj_in["thread_id"] = thread_id
        obj_in["created_at"] = datetime.utcnow()
        result = await self.collection.insert_one(obj_in)
        doc = await self.collection.find_one({"_id": result.inserted_id})
        return ChatMessageMongo.parse_obj(doc) 