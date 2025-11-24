from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps.auth import get_current_user
from app.db.session import get_session
from app.models.event import Event, EventStatus
from app.models.favorite_event import FavoriteEvent
from app.models.user import User
from app.schemas.event import EventRead

router = APIRouter(
    prefix="/favorites",
    tags=["favorites"],
)


@router.get("/", response_model=List[EventRead])
async def list_my_favorites(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EventRead]:
    """
    Список избранных событий текущего пользователя.
    Показываем только опубликованные события.
    """
    stmt = (
        select(Event)
        .join(FavoriteEvent, FavoriteEvent.event_id == Event.id)
        .options(selectinload(Event.category))
        .where(
            FavoriteEvent.user_id == current_user.id,
            Event.status == EventStatus.published,
        )
        .order_by(FavoriteEvent.created_at.desc())
    )

    result = await session.execute(stmt)
    events = result.scalars().unique().all()
    return [EventRead.model_validate(e) for e in events]


@router.get("/{event_id}", response_model=dict)
async def is_favorite(
    event_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Проверка: находится ли событие в избранном у пользователя.
    """
    stmt = select(FavoriteEvent).where(
        FavoriteEvent.user_id == current_user.id,
        FavoriteEvent.event_id == event_id,
    )
    result = await session.execute(stmt)
    fav = result.scalar_one_or_none()
    return {"is_favorite": fav is not None}


@router.post(
    "/{event_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,
)
async def add_favorite(
    event_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Добавление события в избранное.
    """
    # проверим, что событие существует и опубликовано
    ev_stmt = select(Event).where(
        Event.id == event_id,
        Event.status == EventStatus.published,
    )
    ev_res = await session.execute(ev_stmt)
    event = ev_res.scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Событие не найдено или не опубликовано",
        )

    # проверим, не добавлено ли уже
    check_stmt = select(FavoriteEvent).where(
        FavoriteEvent.user_id == current_user.id,
        FavoriteEvent.event_id == event_id,
    )
    check_res = await session.execute(check_stmt)
    if check_res.scalar_one_or_none() is not None:
        return {"is_favorite": True}

    fav = FavoriteEvent(user_id=current_user.id, event_id=event_id)
    session.add(fav)
    await session.commit()
    return {"is_favorite": True}


@router.delete("/{event_id}", status_code=status.HTTP_200_OK, response_model=dict)
async def remove_favorite(
    event_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Удаление события из избранного.
    """
    stmt = delete(FavoriteEvent).where(
        FavoriteEvent.user_id == current_user.id,
        FavoriteEvent.event_id == event_id,
    )
    await session.execute(stmt)
    await session.commit()
    return {"is_favorite": False}
