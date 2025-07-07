from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.chat import Chat, ChatMessage
from app.schemas.chat import ChatCreate, ChatUpdate, ChatMessageCreate


class CRUDChat(CRUDBase[Chat, ChatCreate, ChatUpdate]):
    def get_by_user(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Chat]:
        return (
            db.query(self.model)
            .filter(Chat.user_id == user_id, Chat.is_active == True)
            .order_by(Chat.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_with_user(
        self, db: Session, *, obj_in: ChatCreate, user_id: int
    ) -> Chat:
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data, user_id=user_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def is_owner(self, *, chat: Chat, user_id: int) -> bool:
        return chat.user_id == user_id

    def deactivate(self, db: Session, *, chat_id: int) -> Chat:
        chat = db.query(self.model).filter(self.model.id == chat_id).first()
        if chat:
            chat.is_active = False
            db.commit()
            db.refresh(chat)
        return chat


class CRUDChatMessage(CRUDBase[ChatMessage, ChatMessageCreate, ChatMessageCreate]):
    def get_by_chat(
        self, db: Session, *, chat_id: int, skip: int = 0, limit: int = 100
    ) -> List[ChatMessage]:
        return (
            db.query(self.model)
            .filter(ChatMessage.chat_id == chat_id)
            .order_by(ChatMessage.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_with_chat(
        self, db: Session, *, obj_in: ChatMessageCreate, chat_id: int
    ) -> ChatMessage:
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data, chat_id=chat_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


chat = CRUDChat(Chat)
chat_message = CRUDChatMessage(ChatMessage) 