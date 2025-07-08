from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorCollection
from app.models.thread_mongo import ThreadMongo
from bson import ObjectId
from datetime import datetime

class CRUDThreadMongo:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def get_by_user(self, user_id: str, skip: int = 0, limit: int = 100) -> List[ThreadMongo]:
        cursor = self.collection.find({"user_id": ObjectId(user_id), "is_active": True}).skip(skip).limit(limit).sort("updated_at", -1)
        return [ThreadMongo.parse_obj(doc) async for doc in cursor]

    async def create_with_user(self, obj_in: dict, user_id: str) -> ThreadMongo:
        obj_in["user_id"] = ObjectId(user_id)
        obj_in["created_at"] = datetime.utcnow()
        obj_in["is_active"] = True
        result = await self.collection.insert_one(obj_in)
        doc = await self.collection.find_one({"_id": result.inserted_id})
        return ThreadMongo.parse_obj(doc)

    async def get_by_id(self, thread_id: str) -> Optional[ThreadMongo]:
        doc = await self.collection.find_one({"_id": ObjectId(thread_id)})
        return ThreadMongo.parse_obj(doc) if doc else None

    async def is_owner(self, thread: ThreadMongo, user_id: str) -> bool:
        return str(thread.user_id) == user_id

    async def update(self, thread_id: str, update_data: dict) -> Optional[ThreadMongo]:
        update_data.pop("id", None)
        update_data.pop("_id", None)
        await self.collection.update_one({"_id": ObjectId(thread_id)}, {"$set": update_data})
        doc = await self.collection.find_one({"_id": ObjectId(thread_id)})
        return ThreadMongo.parse_obj(doc) if doc else None

    async def deactivate(self, thread_id: str) -> Optional[ThreadMongo]:
        await self.collection.update_one({"_id": ObjectId(thread_id)}, {"$set": {"is_active": False}})
        doc = await self.collection.find_one({"_id": ObjectId(thread_id)})
        return ThreadMongo.parse_obj(doc) if doc else None 