from typing import Optional
from pydantic import BaseModel, Field, field_validator


class UserBase(BaseModel):
    email: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False


class UserCreate(UserBase):
    email: str
    password: str


class UserUpdate(UserBase):
    password: Optional[str] = None


class UserInDBBase(UserBase):
    id: Optional[int] = None

    model_config = {"from_attributes": True}


class User(BaseModel):
    id: str = Field(alias="_id")
    email: str
    is_active: bool = True
    is_superuser: bool = False

    @field_validator("id", mode="before")
    @classmethod
    def str_id(cls, v):
        return str(v)

    class Config:
        orm_mode = True
        populate_by_name = True


class UserInDB(UserInDBBase):
    hashed_password: str 

class UserResponse(UserBase):
    pass