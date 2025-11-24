from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps.auth import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.models.event_rsvp import EventRSVP
from app.models.event import Event, EventCategory
from app.schemas.rsvp import MyRSVPItem

router = APIRouter(
    prefix="/rsvp",
    tags=["rsvp"],
)


@router.get("/my", response_model=list[MyRSVPItem])
async def list_my_rsvp(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[MyRSVPItem]:
    """
    Список всех откликов текущего пользователя на мероприятия.

    Возвращает:
    - сам отклик (id, status, created/updated, user_id, event_id)
    - вложенное событие `event` (через EventRead), включая категорию.
    """

    stmt = (
        select(EventRSVP)
        .options(
            # подгружаем событие и категорию, чтобы не словить MissingGreenlet
            selectinload(EventRSVP.event).selectinload(Event.category)
        )
        .where(EventRSVP.user_id == current_user.id)
        .order_by(EventRSVP.created_at.desc())
    )

    result = await session.execute(stmt)
    rsvps = result.scalars().unique().all()

    return [MyRSVPItem.model_validate(r) for r in rsvps]
