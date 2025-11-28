from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.user import UserRead, UserUpdateProfile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_user)) -> UserRead:
    """Возвращает профиль текущего пользователя."""
    return UserRead.model_validate(current_user)


@router.put("/me", response_model=UserRead)
async def update_me(
    payload: UserUpdateProfile,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """Обновляет профиль текущего пользователя."""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
    if payload.phone is not None:
        current_user.phone = payload.phone

    if payload.telegram is not None:
        current_user.telegram = payload.telegram

    if payload.about is not None:
        current_user.about = payload.about

    if payload.preferences is not None:
        current_user.preferences = payload.preferences
        
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)

    return UserRead.model_validate(current_user)
