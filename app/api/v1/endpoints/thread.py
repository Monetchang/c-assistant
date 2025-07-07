from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.Thread])
def read_chats(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取当前用户的聊天列表
    """
    chats = crud.thread.get_by_user(
        db=db, user_id=current_user.id, skip=skip, limit=limit
    )
    return chats


@router.post("/", response_model=schemas.Thread)
def create_chat(
    *,
    db: Session = Depends(deps.get_db),
    thread_in: schemas.ThreadCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建新的聊天
    """
    chat = crud.thread.create_with_owner(
        db=db, obj_in=thread_in, user_id=current_user.id
    )
    return chat


@router.get("/{thread_id}", response_model=schemas.ThreadWithMessages)
def read_chat(
    *,
    db: Session = Depends(deps.get_db),
    thread_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取指定聊天及其消息
    """
    chat = crud.thread.get(db=db, id=thread_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if not crud.thread.is_owner(chat=chat, user_id=current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    
    messages = crud.chat_message.get_by_chat(db=db, chat_id=thread_id)
    return schemas.ThreadWithMessages(
        **chat.__dict__,
        messages=messages
    )


@router.put("/{thread_id}", response_model=schemas.Thread)
def update_chat(
    *,
    db: Session = Depends(deps.get_db),
    thread_id: int,
    thread_in: schemas.ThreadUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新聊天信息
    """
    thread = crud.thread.get(db=db, id=thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Chat not found")
    if not crud.thread.is_owner(thread=thread, user_id=current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    thread = crud.thread.update(db=db, db_obj=thread, obj_in=thread_in)
    return thread


@router.delete("/{thread_id}", response_model=schemas.Thread)
def delete_chat(
    *,
    db: Session = Depends(deps.get_db),
    thread_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除聊天（软删除）
    """
    thread = crud.thread.get(db=db, id=thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Chat not found")
    if not crud.thread.is_owner(thread=thread, user_id=current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    thread = crud.thread.deactivate(db=db, thread_id=thread_id)
    return {"message": "Chat deleted successfully"}