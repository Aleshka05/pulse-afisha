from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import role_required
from app.db.session import get_session
from app.loader import APP_LOGGER
from app.models.user import User, UserRole
from app.schemas.user import UserRead, UserRoleUpdate, UserBlockUpdate

router = APIRouter(
    prefix="/admin/users",
    tags=["admin:users"],
    dependencies=[Depends(role_required(UserRole.admin))],
)


@router.get("/", response_model=List[UserRead])
async def list_users(
    session: AsyncSession = Depends(get_session),
    role: UserRole | None = Query(default=None),
    is_blocked: bool | None = Query(default=None),
    q: str | None = Query(
        default=None,
        min_length=1,
        description="Поиск по email и имени",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[UserRead]:
    """
    Список пользователей для админа.

    Фильтры:
    - role: admin / organizer / user
    - is_blocked: true/false
    - q: поиск по email / full_name
    """
    conditions = []

    if role is not None:
        conditions.append(User.role == role)

    if is_blocked is not None:
        conditions.append(User.is_blocked == is_blocked)

    if q:
        like = f"%{q}%"
        conditions.append(
            or_(
                User.email.ilike(like),
                User.full_name.ilike(like),
            )
        )

    stmt = (
        select(User)
        .where(and_(*conditions) if conditions else True)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await session.execute(stmt)
    users = result.scalars().unique().all()
    return [UserRead.model_validate(u) for u in users]


@router.patch("/{user_id}/role", response_model=UserRead)
async def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """
    Изменение роли пользователя.

    Нельзя понизить/изменить свою собственную роль через этот эндпоинт.
    """
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    old_role = user.role
    new_role = payload.role

    if old_role == new_role:
        return UserRead.model_validate(user)

    user.role = new_role

    session.add(user)
    await session.commit()
    await session.refresh(user)

    APP_LOGGER.info(
        f"[admin_users] role changed user_id={user.id} {old_role.value} -> {new_role.value}"
    )

    return UserRead.model_validate(user)


@router.patch("/{user_id}/block", response_model=UserRead)
async def update_user_block(
    user_id: int,
    payload: UserBlockUpdate,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """
    Блокировка/разблокировка пользователя.
    """
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    user.is_blocked = payload.is_blocked

    session.add(user)
    await session.commit()
    await session.refresh(user)

    APP_LOGGER.info(
        f"[admin_users] block changed user_id={user.id} is_blocked={user.is_blocked}"
    )

    return UserRead.model_validate(user)
