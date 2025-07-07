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
    chat_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatBase(BaseModel):
    title: Optional[str] = None


class ChatCreate(ChatBase):
    title: str


class ChatUpdate(ChatBase):
    pass


class Chat(ChatBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool
    messages: List[ChatMessage] = []

    model_config = {"from_attributes": True}


class ChatWithMessages(Chat):
    messages: List[ChatMessage] = []


class ChatResponse(BaseModel):
    chat: Chat
    messages: List[ChatMessage] 