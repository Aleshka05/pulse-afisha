from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user, role_required
from app.db.session import get_session
from app.models.user import User, UserRole
from app.models.support_ticket import SupportTicket, SupportTicketStatus
from app.schemas.support_ticket import (
    SupportTicketCreate,
    SupportTicketRead,
)

router = APIRouter(
    prefix="/support-tickets",
    tags=["support"],
)


@router.post(
    "/",
    response_model=SupportTicketRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_support_ticket(
    payload: SupportTicketCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SupportTicketRead:
    """
    Создание обращения в поддержку текущим пользователем.
    """
    ticket = SupportTicket(
        user_id=current_user.id,
        subject=payload.subject,
        message=payload.message,
        status=SupportTicketStatus.open,
    )

    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)

    return SupportTicketRead.model_validate(ticket)


@router.get("/my", response_model=list[SupportTicketRead])
async def list_my_support_tickets(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SupportTicketRead]:
    """
    Список обращений текущего пользователя.
    """
    stmt = (
        select(SupportTicket)
        .where(SupportTicket.user_id == current_user.id)
        .order_by(SupportTicket.created_at.desc())
    )
    result = await session.execute(stmt)
    tickets = result.scalars().unique().all()
    return [SupportTicketRead.model_validate(t) for t in tickets]


@router.get(
    "/admin",
    response_model=list[SupportTicketRead],
    dependencies=[Depends(role_required(UserRole.admin))],
)
async def admin_list_support_tickets(
    session: AsyncSession = Depends(get_session),
) -> list[SupportTicketRead]:
    """
    Список всех обращений (для админов).
    """
    stmt = (
        select(SupportTicket)
        .order_by(
            SupportTicket.status.asc(),
            SupportTicket.created_at.desc(),
        )
    )
    result = await session.execute(stmt)
    tickets = result.scalars().unique().all()
    return [SupportTicketRead.model_validate(t) for t in tickets]


@router.delete(
    "/admin/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(role_required(UserRole.admin))],
)
async def admin_delete_support_ticket(
    ticket_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Удаление обращения (для админки).
    """
    stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
    result = await session.execute(stmt)
    ticket = result.scalar_one_or_none()

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Обращение не найдено",
        )

    await session.delete(ticket)
    await session.commit()
