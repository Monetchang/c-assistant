from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

class UserMongo(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    user_name: Optional[str]
    email: EmailStr
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str} 