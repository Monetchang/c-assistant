from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.Chat])
def read_chats(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取当前用户的聊天列表
    """
    chats = crud.chat.get_by_user(
        db=db, user_id=current_user.id, skip=skip, limit=limit
    )
    return chats


@router.post("/", response_model=schemas.Chat)
def create_chat(
    *,
    db: Session = Depends(deps.get_db),
    chat_in: schemas.ChatCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建新的聊天
    """
    chat = crud.chat.create_with_owner(
        db=db, obj_in=chat_in, user_id=current_user.id
    )
    return chat


@router.get("/{chat_id}", response_model=schemas.ChatWithMessages)
def read_chat(
    *,
    db: Session = Depends(deps.get_db),
    chat_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取指定聊天及其消息
    """
    chat = crud.chat.get(db=db, id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if not crud.chat.is_owner(chat=chat, user_id=current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    
    messages = crud.chat_message.get_by_chat(db=db, chat_id=chat_id)
    return schemas.ChatWithMessages(
        **chat.__dict__,
        messages=messages
    )


@router.put("/{chat_id}", response_model=schemas.Chat)
def update_chat(
    *,
    db: Session = Depends(deps.get_db),
    chat_id: int,
    chat_in: schemas.ChatUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新聊天信息
    """
    chat = crud.chat.get(db=db, id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if not crud.chat.is_owner(chat=chat, user_id=current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    chat = crud.chat.update(db=db, db_obj=chat, obj_in=chat_in)
    return chat


@router.delete("/{chat_id}")
def delete_chat(
    *,
    db: Session = Depends(deps.get_db),
    chat_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除聊天（软删除）
    """
    chat = crud.chat.get(db=db, id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if not crud.chat.is_owner(chat=chat, user_id=current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    chat = crud.chat.deactivate(db=db, chat_id=chat_id)
    return {"message": "Chat deleted successfully"}


@router.post("/{chat_id}/messages", response_model=schemas.ChatMessage)
def create_message(
    *,
    db: Session = Depends(deps.get_db),
    chat_id: int,
    message_in: schemas.ChatMessageCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    在指定聊天中创建新消息
    """
    chat = crud.chat.get(db=db, id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if not crud.chat.is_owner(chat=chat, user_id=current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    
    message = crud.chat_message.create_with_chat(
        db=db, obj_in=message_in, chat_id=chat_id
    )
    return message


@router.get("/{chat_id}/messages", response_model=List[schemas.ChatMessage])
def read_messages(
    *,
    db: Session = Depends(deps.get_db),
    chat_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取指定聊天的消息列表
    """
    chat = crud.chat.get(db=db, id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if not crud.chat.is_owner(chat=chat, user_id=current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    
    messages = crud.chat_message.get_by_chat(
        db=db, chat_id=chat_id, skip=skip, limit=limit
    )
    return messages 