from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class ChatMessageBase(BaseModel):
    content: str


class ChatMessageCreate(ChatMessageBase):
    pass


class ChatMessage(ChatMessageBase):
    id: str
    thread_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
