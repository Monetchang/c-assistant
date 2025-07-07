from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class ChatMessageBase(BaseModel):
    role: str
    content: str


class ChatMessageCreate(ChatMessageBase):
    pass


class ChatMessage(ChatMessageBase):
    id: int
    thread_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
