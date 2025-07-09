from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection
from app.schemas.chat import ChatMessage, ChatMessageCreate,ChatMessageContent
from app.api.deps import get_message_collection
from app.crud.crud_chat_message_mongo import CRUDChatMessageMongo
from app.crud.crud_thread_mongo import CRUDThreadMongo
from app.api.deps import get_thread_collection
from app.core.agent import AgentCore

router = APIRouter()

@router.post("/{thread_id}/chat", response_model=ChatMessageContent)
async def chat(
    *,
    thread_id: str,
    message_in: ChatMessageContent, 
) -> str:
    content = AgentCore.start_chat(message_in.content, thread_id)
    return ChatMessageContent(content = content)


async def create_message(
    *,
    collection: AsyncIOMotorCollection = Depends(get_message_collection),
    thread_collection: AsyncIOMotorCollection = Depends(get_thread_collection),
    thread_id: str,
    message_in: ChatMessageCreate,
) -> Any:
    crud_thread = CRUDThreadMongo(thread_collection)
    thread = await crud_thread.get_by_id(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Chat not found")
    # 这里可加权限校验
    crud_message = CRUDChatMessageMongo(collection)
    message = await crud_message.create_with_chat({"role": "assistant", "content": ""}, thread_id)
    return crud_message

@router.get("/{thread_id}/messages", response_model=List[ChatMessage])
async def read_messages(
    *,
    collection: AsyncIOMotorCollection = Depends(get_message_collection),
    thread_collection: AsyncIOMotorCollection = Depends(get_thread_collection),
    thread_id: str,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    crud_thread = CRUDThreadMongo(thread_collection)
    thread = await crud_thread.get_by_id(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Chat not found")
    # 这里可加权限校验
    crud_message = CRUDChatMessageMongo(collection)
    messages = await crud_message.get_by_chat(thread_id, skip=skip, limit=limit)
    return messages 