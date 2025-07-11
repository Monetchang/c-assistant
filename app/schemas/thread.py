from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.chat_message import ChatMessage

class ThreadBase(BaseModel):
    title: str


class ThreadCreate(ThreadBase):
    pass


class ThreadUpdate(ThreadBase):
    pass


class Thread(ThreadBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool
    messages: List[ChatMessage] = []

    model_config = {"from_attributes": True}

class ThreadWithMessages(Thread):
    messages: List[ChatMessage] = []


class ThreadResponse(ThreadBase):
    id: str