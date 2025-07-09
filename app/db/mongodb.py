from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional  # 可根据实际情况修改
from app.core.config import settings

class MongoDB:
    client: Optional[AsyncIOMotorClient] = None

mongodb = MongoDB()

def get_database():
    if mongodb.client is None:
        raise RuntimeError("MongoDB client is not connected")
    return mongodb.client["agent"]  # 替换为你的数据库名

async def connect_to_mongo():
    mongodb.client = AsyncIOMotorClient(settings.MONGODB_URL)

async def close_mongo_connection():
    if mongodb.client is None:
        raise RuntimeError("MongoDB client is not connected")
    mongodb.client.close()