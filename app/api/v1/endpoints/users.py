from typing import Any, List
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorCollection
from app.schemas.user import User, UserCreate, UserUpdate
from app.api.deps import get_user_collection
from app.crud.crud_user_mongo import CRUDUserMongo
from app.schemas.user import UserResponse

router = APIRouter()

@router.get("/", response_model=List[User])
async def read_users(
    collection: AsyncIOMotorCollection = Depends(get_user_collection),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve users.
    """
    cursor = collection.find().skip(skip).limit(limit)
    print("cursor:", cursor)
    users = [User(**doc) async for doc in cursor]
    return users


@router.post("/", response_model=UserResponse)
async def create_user(
    *,
    collection: AsyncIOMotorCollection = Depends(get_user_collection),
    user_in: UserCreate,
) -> Any:
    """
    Create new user.
    """
    crud_user = CRUDUserMongo(collection)
    existing = await crud_user.get_by_email(user_in.email)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    user = await crud_user.create(user_in.model_dump())
    return user


@router.put("/me", response_model=User)
async def update_user_me(
    *,
    collection: AsyncIOMotorCollection = Depends(get_user_collection),
    password: str = Body(None),
    email: str = Body(None),
    current_user: User = Body(...),
) -> Any:
    """
    Update own user.
    """
    crud_user = CRUDUserMongo(collection)
    update_data = current_user.model_dump()
    if password is not None:
        update_data["password"] = password
    if email is not None:
        update_data["email"] = email
    user = await crud_user.update(update_data["id"], update_data)
    return user


@router.get("/me", response_model=User)
async def read_user_me(
    current_user: User = Body(...),
) -> Any:
    """
    Get current user.
    """
    return current_user


@router.get("/{user_id}", response_model=User)
async def read_user_by_id(
    user_id: str,
    collection: AsyncIOMotorCollection = Depends(get_user_collection),
) -> Any:
    """
    Get a specific user by id.
    """
    crud_user = CRUDUserMongo(collection)
    user = await crud_user.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )
    return user 