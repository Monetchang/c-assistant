from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.thread import Thread
from app.schemas.thread import ThreadCreate, ThreadUpdate


class CRUDThread(CRUDBase[Thread, ThreadCreate, ThreadUpdate]):
    def get_by_user(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Thread]:
        return (
            db.query(self.model)
            .filter(Thread.user_id == user_id, Thread.is_active == True)
            .order_by(Thread.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_with_user(
        self, db: Session, *, obj_in: ThreadCreate, user_id: int
    ) -> Thread:
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data, user_id=user_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def is_owner(self, *, thread: Thread, user_id: int) -> bool:
        return thread.user_id == user_id

    def deactivate(self, db: Session, *, thread_id: int) -> Thread:
        thread = db.query(self.model).filter(self.model.id == thread_id).first()
        if thread:
            thread.is_active = False
            db.commit()
            db.refresh(thread)
        return thread

thread = CRUDThread(Thread)