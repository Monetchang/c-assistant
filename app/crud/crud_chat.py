from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.chat import ChatMessage
from app.schemas.chat import ChatMessageCreate

class CRUDChatMessage(CRUDBase[ChatMessage, ChatMessageCreate, ChatMessageCreate]):
    def get_by_chat(
        self, db: Session, *, thread_id: int, skip: int = 0, limit: int = 100
    ) -> List[ChatMessage]:
        return (
            db.query(self.model)
            .filter(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_with_chat(
        self, db: Session, *, obj_in: ChatMessageCreate, thread_id: int
    ) -> ChatMessage:
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data, thread_id=thread_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

chat_message = CRUDChatMessage(ChatMessage) 