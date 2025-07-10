from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection
from app.schemas.chat_message import ChatMessage, ChatMessageCreate,ChatMessageContent
from app.api.deps import get_message_collection
from app.crud.crud_chat_message_mongo import CRUDChatMessageMongo
from app.crud.crud_thread_mongo import CRUDThreadMongo
from app.api.deps import get_thread_collection
from app.core.agent import async_start_chat
from app.models.user_mongo import UserMongo
from app.api.deps import get_current_active_user

router = APIRouter()

@router.post("/{thread_id}/chat", response_model=ChatMessageContent)
async def chat(
    *,
    collection: AsyncIOMotorCollection = Depends(get_message_collection),
    thread_collection: AsyncIOMotorCollection = Depends(get_thread_collection),
    thread_id: str,
    message_in: ChatMessageContent,
    current_user: UserMongo = Depends(get_current_active_user),
) -> Any:
    crud_thread = CRUDThreadMongo(thread_collection)
    thread = await crud_thread.get_by_id(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Chat not found")
    #权限校验：验证用户是否为该 thread 的所有者
    if not await crud_thread.is_owner(thread, str(current_user.id)):
        raise HTTPException(status_code=403, detail="Not enough permissions to access this chat")
    
    # 异步调用 start_chat 获取助手回复
    assistant_response = await async_start_chat(
        collection=collection,
        thread_id=thread_id,
        user_input=message_in.content
    )
    
    return ChatMessageContent(content=assistant_response)

@router.get("/{thread_id}/messages", response_model=List[ChatMessage])
async def read_messages(
    *,
    collection: AsyncIOMotorCollection = Depends(get_message_collection),
    thread_collection: AsyncIOMotorCollection = Depends(get_thread_collection),
    thread_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user: UserMongo = Depends(get_current_active_user),
) -> Any:
    crud_thread = CRUDThreadMongo(thread_collection)
    thread = await crud_thread.get_by_id(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Chat not found")
    #权限校验：验证用户是否为该 thread 的所有者
    if not await crud_thread.is_owner(thread, str(current_user.id)):
        raise HTTPException(status_code=403, detail="Not enough permissions to access this chat")
    
    crud_message = CRUDChatMessageMongo(collection)
    messages = await crud_message.get_by_chat(thread_id, skip=skip, limit=limit)
    return messages 