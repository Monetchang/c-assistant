from pydantic import BaseModel, Field, field_serializer
from typing import Optional
from bson import ObjectId
from datetime import datetime

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info=None):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

class ChatMessageMongo(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    thread_id: str
    role: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_serializer('id')
    def serialize_id(self, id, _info):
        return str(id) if id is not None else None

    class Config:
        arbitrary_types_allowed = True