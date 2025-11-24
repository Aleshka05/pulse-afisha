from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import role_required
from app.db.session import get_session
from app.loader import APP_LOGGER
from app.models.organizer_request import OrganizerRequest, OrganizerRequestStatus
from app.models.user import User, UserRole
from app.schemas.organizer_request import OrganizerRequestRead

router = APIRouter(
    prefix="/admin/organizer-requests",
    tags=["admin:organizer-requests"],
    dependencies=[Depends(role_required(UserRole.admin))],
)


@router.get("/", response_model=List[OrganizerRequestRead])
async def list_organizer_requests(
    session: AsyncSession = Depends(get_session),
    status_filter: OrganizerRequestStatus | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[OrganizerRequestRead]:
    """
    Список заявок на роль организатора.

    Можно отфильтровать по статусу: pending / approved / rejected.
    """
    conditions = []

    if status_filter is not None:
        conditions.append(OrganizerRequest.status == status_filter)

    stmt = (
        select(OrganizerRequest)
        .where(and_(*conditions) if conditions else True)
        .order_by(desc(OrganizerRequest.created_at))
        .limit(limit)
        .offset(offset)
    )

    result = await session.execute(stmt)
    rows = result.scalars().unique().all()
    return [OrganizerRequestRead.model_validate(r) for r in rows]


@router.post("/{request_id}/approve", response_model=OrganizerRequestRead)
async def approve_organizer_request(
    request_id: int,
    session: AsyncSession = Depends(get_session),
) -> OrganizerRequestRead:
    """
    Одобрение заявки на роль организатора.

    Меняет статус на approved и роль пользователя на organizer.
    """
    stmt = select(OrganizerRequest).where(OrganizerRequest.id == request_id)
    result = await session.execute(stmt)
    req = result.scalar_one_or_none()

    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена",
        )

    if req.status != OrganizerRequestStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Можно одобрить только заявку в статусе pending",
        )

    # Получаем пользователя
    user_stmt = select(User).where(User.id == req.user_id)
    user_res = await session.execute(user_stmt)
    user = user_res.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь заявки не найден",
        )

    req.status = OrganizerRequestStatus.approved
    from datetime import datetime as dt

    req.resolved_at = dt.utcnow()
    req.admin_comment = (req.admin_comment or "").strip() or "Одобрено администратором"

    # Меняем роль пользователя
    user.role = UserRole.organizer

    session.add_all([req, user])
    await session.commit()
    await session.refresh(req)

    APP_LOGGER.info(
        f"[OrganizerRequest] approved id={req.id} user_id={user.id}"
    )

    return OrganizerRequestRead.model_validate(req)


@router.post("/{request_id}/reject", response_model=OrganizerRequestRead)
async def reject_organizer_request(
    request_id: int,
    reason: str = Query(
        default="Заявка отклонена администратором",
        min_length=3,
        max_length=2000,
    ),
    session: AsyncSession = Depends(get_session),
) -> OrganizerRequestRead:
    """
    Отклонение заявки на роль организатора.

    Меняет статус на rejected и сохраняет причину.
    """
    stmt = select(OrganizerRequest).where(OrganizerRequest.id == request_id)
    result = await session.execute(stmt)
    req = result.scalar_one_or_none()

    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена",
        )

    if req.status != OrganizerRequestStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Можно отклонить только заявку в статусе pending",
        )

    from datetime import datetime as dt

    req.status = OrganizerRequestStatus.rejected
    req.resolved_at = dt.utcnow()
    req.admin_comment = reason.strip()

    session.add(req)
    await session.commit()
    await session.refresh(req)

    APP_LOGGER.info(
        f"[OrganizerRequest] rejected id={req.id}"
    )

    return OrganizerRequestRead.model_validate(req)
