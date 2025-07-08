from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.core import security
from app.core.config import settings
from app.schemas import token
from app.api import deps
from app.crud.crud_user_mongo import CRUDUserMongo

router = APIRouter()


@router.post("/login/access-token", response_model=token.Token)
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    collection=Depends(deps.get_user_collection)
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    crud_user = CRUDUserMongo(collection)
    user = await crud_user.authenticate(email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    elif not crud_user.is_active(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            str(user.id), expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post("/test-token", response_model=token.Token)
def test_token(current_user: Any = Depends(deps.get_current_user)) -> Any:
    """
    Test access token
    """
    return {"access_token": "test", "token_type": "bearer"} 