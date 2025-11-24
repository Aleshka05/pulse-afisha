from typing import List
from datetime import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import role_required
from app.db.session import get_session
from app.loader import APP_LOGGER
from app.models.support_ticket import (
    SupportTicket,
    SupportTicketStatus,
)
from app.models.user import UserRole
from app.schemas.support_ticket import (
    SupportTicketRead,
    SupportTicketReply,
)

router = APIRouter(
    prefix="/admin/support-tickets",
    tags=["admin:support-tickets"],
    dependencies=[Depends(role_required(UserRole.admin))],
)


@router.get("/", response_model=List[SupportTicketRead])
async def list_tickets(
    session: AsyncSession = Depends(get_session),
    status_filter: SupportTicketStatus | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[SupportTicketRead]:
    """
    Список обращений пользователей.

    Можно фильтровать по статусу: open / answered / closed.
    """
    conditions = []
    if status_filter is not None:
        conditions.append(SupportTicket.status == status_filter)

    stmt = (
        select(SupportTicket)
        .where(and_(*conditions) if conditions else True)
        .order_by(desc(SupportTicket.created_at))
        .limit(limit)
        .offset(offset)
    )

    result = await session.execute(stmt)
    rows = result.scalars().unique().all()
    return [SupportTicketRead.model_validate(t) for t in rows]


@router.post("/{ticket_id}/reply", response_model=SupportTicketRead)
async def reply_ticket(
    ticket_id: int,
    payload: SupportTicketReply,
    session: AsyncSession = Depends(get_session),
) -> SupportTicketRead:
    """
    Ответ администратора на обращение.

    Статус становится answered.
    """
    stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
    result = await session.execute(stmt)
    ticket = result.scalar_one_or_none()

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Обращение не найдено",
        )

    ticket.admin_reply = payload.reply.strip()
    ticket.status = SupportTicketStatus.answered
    ticket.updated_at = dt.utcnow()

    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)

    APP_LOGGER.info(
        f"[SupportTicket] replied id={ticket.id}"
    )

    return SupportTicketRead.model_validate(ticket)


@router.post("/{ticket_id}/close", response_model=SupportTicketRead)
async def close_ticket(
    ticket_id: int,
    session: AsyncSession = Depends(get_session),
) -> SupportTicketRead:
    """
    Закрытие обращения администратором.
    """
    stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
    result = await session.execute(stmt)
    ticket = result.scalar_one_or_none()

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Обращение не найдено",
        )

    ticket.status = SupportTicketStatus.closed
    ticket.updated_at = dt.utcnow()

    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)

    APP_LOGGER.info(
        f"[SupportTicket] closed id={ticket.id}"
    )

    return SupportTicketRead.model_validate(ticket)
