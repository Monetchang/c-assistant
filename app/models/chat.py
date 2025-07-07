from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base


class Chat(Base):
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # 关系
    user = relationship("User", back_populates="chats")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")


class ChatMessage(Base):
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chat.id"), nullable=False)
    role = Column(String(50), nullable=False)  # 'user' 或 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    chat = relationship("Chat", back_populates="messages") 