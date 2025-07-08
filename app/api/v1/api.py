from fastapi import APIRouter
from app.api.v1.endpoints import chat_message, thread, users, auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(thread.router, prefix="/threads", tags=["threads"])
api_router.include_router(chat_message.router, prefix="/chats", tags=["chats"]) 