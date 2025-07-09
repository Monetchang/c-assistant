from typing import Optional
from motor.motor_asyncio import AsyncIOMotorCollection
from app.models.user_mongo import UserMongo
from app.core.security import get_password_hash, verify_password
from bson import ObjectId
from app.schemas.user import UserResponse

class CRUDUserMongo:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def get_by_id(self, id: str) -> Optional[UserMongo]:
        doc = await self.collection.find_one({"_id": ObjectId(id)})
        return UserMongo(**doc) if doc else None

    async def get_by_email(self, email: str) -> Optional[UserMongo]:
        doc = await self.collection.find_one({"email": email})
        return UserMongo(**doc) if doc else None

    async def create(self, user_data) -> UserResponse:
        user_data["hashed_password"] = get_password_hash(user_data["password"])
        del user_data["password"]
        print("user_data:", user_data)
        result = await self.collection.insert_one(user_data)
        user = await self.collection.find_one({"_id": result.inserted_id})
        if not user:
            raise ValueError("Failed to create user")
        return UserResponse(
            id = str(user["_id"]),
            email=user["email"]
        )

    async def authenticate(self, email: str, password: str) -> Optional[UserMongo]:
        user = await self.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: UserMongo) -> bool:
        return user.is_active

    def is_superuser(self, user: UserMongo) -> bool:
        return user.is_superuser

    async def update(self, id: str, update_data: dict) -> Optional[UserMongo]:
        # 不允许直接更新 _id
        update_data.pop("id", None)
        update_data.pop("_id", None)
        await self.collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": update_data}
        )
        doc = await self.collection.find_one({"_id": ObjectId(id)})
        return UserMongo(**doc) if doc else None 