from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from app.core import security
from app.core.config import settings
from app.db.mongodb import get_database
from app.crud.crud_user_mongo import CRUDUserMongo
from app.models.user_mongo import UserMongo
from bson import ObjectId
from app.schemas.token import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token"
)

async def get_user_collection():
    db = get_database()
    return db["user"]

async def get_thread_collection():
    db = get_database()
    return db["thread"]

async def get_message_collection():
    db = get_database()
    return db["chat_message"]

async def get_current_user(
    collection=Depends(get_user_collection), token: str = Depends(reusable_oauth2)
) -> UserMongo:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    if not token_data.sub:
        raise HTTPException(status_code=404, detail="User not found")
    crud_user = CRUDUserMongo(collection)
    user = await crud_user.get_by_id(token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def get_current_active_user(
    current_user: UserMongo = Depends(get_current_user),
) -> UserMongo:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_active_superuser(
    current_user: UserMongo = Depends(get_current_user),
) -> UserMongo:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user 