from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import role_required
from app.db.session import get_session
from app.models.event import Event, EventStatus
from app.models.user import UserRole
from app.schemas.event import EventModerationAction, EventRead

router = APIRouter(
    prefix="/admin/events",
    tags=["admin:events"],
    dependencies=[Depends(role_required(UserRole.admin))],
)


@router.get("/", response_model=list[EventRead])
async def list_events_for_moderation(
    session: AsyncSession = Depends(get_session),
    status_filter: EventStatus | None = Query(default=EventStatus.pending_moderation),
) -> list[EventRead]:
    """
    Список событий для админа, по умолчанию — на модерации.
    """
    stmt = select(Event)
    if status_filter is not None:
        stmt = stmt.where(Event.status == status_filter)

    stmt = stmt.order_by(Event.created_at.desc())
    result = await session.execute(stmt)
    events = result.scalars().unique().all()
    return [EventRead.model_validate(e) for e in events]


@router.post("/{event_id}/publish", response_model=EventRead)
async def publish_event(
    event_id: int,
    body: EventModerationAction | None = None,
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    """
    Публикация события.

    Обычно из статуса pending_moderation, но админ может опубликовать и черновик.
    """
    stmt = select(Event).where(Event.id == event_id)
    result = await session.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Событие не найдено",
        )

    if event.status == EventStatus.published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Событие уже опубликовано",
        )

    event.status = EventStatus.published
    event.moderation_comment = body.moderation_comment if body else None

    session.add(event)
    await session.commit()
    await session.refresh(event)
    return EventRead.model_validate(event)


@router.post("/{event_id}/reject", response_model=EventRead)
async def reject_event(
    event_id: int,
    body: EventModerationAction,
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    """
    Отклонение события с комментарием модератора.
    """
    stmt = select(Event).where(Event.id == event_id)
    result = await session.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Событие не найдено",
        )

    # Разрешаем отклонять только событие на модерации
    if event.status != EventStatus.pending_moderation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Можно отклонить только событие в статусе 'на модерации'",
        )

    # Нормализуем комментарий
    comment = (body.moderation_comment or "").strip()
    if not comment:
        comment = "Событие отклонено модератором"

    event.status = EventStatus.rejected
    event.moderation_comment = comment

    # если есть поле moderated_at в модели Event — можешь раскомментировать:
    # from datetime import datetime as dt
    # event.moderated_at = dt.utcnow()

    session.add(event)
    await session.commit()
    await session.refresh(event)

    return EventRead.model_validate(event)



@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event_as_admin(
    event_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Полное удаление события админом.
    """
    stmt = select(Event).where(Event.id == event_id)
    result = await session.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Событие не найдено",
        )

    await session.delete(event)
    await session.commit()
