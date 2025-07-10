from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection
from app.schemas.thread import Thread, ThreadCreate, ThreadUpdate, ThreadWithMessages
from app.schemas.chat_message import ChatMessage
from app.api.deps import get_thread_collection, get_message_collection
from app.crud.crud_thread_mongo import CRUDThreadMongo
from app.crud.crud_chat_message_mongo import CRUDChatMessageMongo
from app.schemas.thread import ThreadResponse

router = APIRouter()


@router.get("/", response_model=List[Thread])
async def read_chats(
    collection: AsyncIOMotorCollection = Depends(get_thread_collection),
    user_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    获取当前用户的聊天列表
    """
    crud_thread = CRUDThreadMongo(collection)
    if user_id is None:
        return []
    threads = await crud_thread.get_by_user(user_id, skip=skip, limit=limit)
    return threads


@router.post("/", response_model=ThreadResponse)
async def create_chat(
    *,
    collection: AsyncIOMotorCollection = Depends(get_thread_collection),
    thread_in: ThreadCreate,
    user_id: str,
) -> Any:
    """
    创建新的聊天
    """
    crud_thread = CRUDThreadMongo(collection)
    thread = await crud_thread.create_with_user(thread_in.model_dump(), user_id)
    return thread


@router.get("/{thread_id}", response_model=ThreadWithMessages)
async def read_chat(
    *,
    collection: AsyncIOMotorCollection = Depends(get_thread_collection),
    message_collection: AsyncIOMotorCollection = Depends(get_message_collection),
    thread_id: str,
    user_id: str,
) -> Any:
    """
    获取指定聊天及其消息
    """
    crud_thread = CRUDThreadMongo(collection)
    crud_message = CRUDChatMessageMongo(message_collection)
    thread = await crud_thread.get_by_id(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Chat not found")
    if not await crud_thread.is_owner(thread, user_id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    messages = await crud_message.get_by_chat(thread_id)
    messages = [ChatMessage(**msg.dict(by_alias=True)) for msg in messages]
    return ThreadWithMessages(**thread.model_dump(), messages=messages)


@router.put("/{thread_id}", response_model=Thread)
async def update_chat(
    *,
    collection: AsyncIOMotorCollection = Depends(get_thread_collection),
    thread_id: str,
    thread_in: ThreadUpdate,
    user_id: str,
) -> Any:
    """
    更新聊天信息
    """
    crud_thread = CRUDThreadMongo(collection)
    thread = await crud_thread.get_by_id(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Chat not found")
    if not await crud_thread.is_owner(thread, user_id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    thread = await crud_thread.update(thread_id, thread_in.model_dump())
    return thread


@router.delete("/{thread_id}", response_model=Thread)
async def delete_chat(
    *,
    collection: AsyncIOMotorCollection = Depends(get_thread_collection),
    thread_id: str,
    user_id: str,
) -> Any:
    """
    删除聊天（软删除）
    """
    crud_thread = CRUDThreadMongo(collection)
    thread = await crud_thread.get_by_id(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Chat not found")
    if not await crud_thread.is_owner(thread, user_id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    thread = await crud_thread.deactivate(thread_id)
    return thread