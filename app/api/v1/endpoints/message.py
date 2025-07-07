from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.api import deps

router = APIRouter()

@router.post("/{thread_id}/messages", response_model=schemas.ChatMessage)
def create_message(
    *,
    db: Session = Depends(deps.get_db),
    thread_id: int,
    message_in: schemas.ChatMessageCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    在指定聊天中创建新消息
    """
    thread = crud.thread.get(db=db, id=thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Chat not found")
    if not crud.thread.is_owner(thread=thread, user_id=current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    
    message = crud.chat_message.create_with_chat(
        db=db, obj_in=message_in, thread_id=thread_id
    )
    return message


@router.get("/{thread_id}/messages", response_model=List[schemas.ChatMessage])
def read_messages(
    *,
    db: Session = Depends(deps.get_db),
    thread_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取指定聊天的消息列表
    """
    thread = crud.thread.get(db=db, id=thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Chat not found")
    if not crud.thread.is_owner(thread=thread, user_id=current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    
    messages = crud.chat_message.get_by_chat(
        db=db, thread_id=thread_id, skip=skip, limit=limit
    )
    return messages 