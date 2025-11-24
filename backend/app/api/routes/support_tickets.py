from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.db.session import get_session
from app.loader import APP_LOGGER
from app.models.support_ticket import SupportTicket
from app.models.user import User
from app.schemas.support_ticket import (
    SupportTicketCreate,
    SupportTicketRead,
)

router = APIRouter(
    prefix="/support-tickets",
    tags=["support-tickets"],
)


@router.get("/my", response_model=List[SupportTicketRead])
async def list_my_tickets(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SupportTicketRead]:
    """Список обращений текущего пользователя."""
    stmt = (
        select(SupportTicket)
        .where(SupportTicket.user_id == current_user.id)
        .order_by(desc(SupportTicket.created_at))
    )
    result = await session.execute(stmt)
    rows = result.scalars().unique().all()
    return [SupportTicketRead.model_validate(t) for t in rows]


@router.post(
    "/",
    response_model=SupportTicketRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_ticket(
    payload: SupportTicketCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SupportTicketRead:
    """
    Создание нового обращения/жалобы в поддержку.
    """
    ticket = SupportTicket(
        user_id=current_user.id,
        subject=payload.subject.strip(),
        message=payload.message.strip(),
    )
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)

    APP_LOGGER.info(
        f"[SupportTicket] created id={ticket.id} user_id={current_user.id}"
    )

    return SupportTicketRead.model_val_
