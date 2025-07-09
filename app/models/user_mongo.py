from pydantic import BaseModel, EmailStr, Field, field_serializer
from typing import Optional
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info=None):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

class UserMongo(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    email: EmailStr
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False

    @field_serializer('id')
    def serialize_id(self, id, _info):
        return str(id) if id is not None else None

    class Config:
        arbitrary_types_allowed = True