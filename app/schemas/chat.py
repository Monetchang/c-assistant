from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class ChatMessageBase(BaseModel):
    content: str

class ChatMessageContent(ChatMessageBase):
    pass

class ChatMessageCreate(ChatMessageBase):
    role: str

class ChatMessage(ChatMessageBase):
    id: str
    thread_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
