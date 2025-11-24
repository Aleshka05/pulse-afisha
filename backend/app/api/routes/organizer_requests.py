from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.db.session import get_session
from app.loader import APP_LOGGER
from app.models.organizer_request import OrganizerRequest, OrganizerRequestStatus
from app.models.user import User, UserRole
from app.schemas.organizer_request import (
    OrganizerRequestCreate,
    OrganizerRequestRead,
)

router = APIRouter(
    prefix="/organizer-requests",
    tags=["organizer-requests"],
)


@router.get("/my", response_model=List[OrganizerRequestRead])
async def list_my_organizer_requests(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[OrganizerRequestRead]:
    """
    Список заявок текущего пользователя на роль организатора.

    Отдаём в порядке от новых к старым.
    """
    stmt = (
        select(OrganizerRequest)
        .where(OrganizerRequest.user_id == current_user.id)
        .order_by(desc(OrganizerRequest.created_at))
    )
    result = await session.execute(stmt)
    rows = result.scalars().unique().all()
    return [OrganizerRequestRead.model_validate(r) for r in rows]


@router.post(
    "/",
    response_model=OrganizerRequestRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_organizer_request(
    payload: OrganizerRequestCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OrganizerRequestRead:
    """
    Создание заявки на роль организатора.

    Ограничения:
    - если уже organizer/admin — заявку создать нельзя;
    - если есть активная (pending) заявка — создаём ошибку.
    """
    if current_user.role in (UserRole.organizer, UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У вас уже есть расширенные права, заявка не требуется",
        )

    # Проверяем, нет ли активной заявки
    stmt = select(OrganizerRequest).where(
        and_(
            OrganizerRequest.user_id == current_user.id,
            OrganizerRequest.status == OrganizerRequestStatus.pending,
        )
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У вас уже есть активная заявка, дождитесь решения",
        )

    req = OrganizerRequest(
        user_id=current_user.id,
        status=OrganizerRequestStatus.pending,
        message=payload.message.strip(),
    )
    session.add(req)
    await session.commit()
    await session.refresh(req)

    APP_LOGGER.info(
        f"[OrganizerRequest] created id={req.id} user_id={current_user.id}"
    )

    return OrganizerRequestRead.model_validate(req)
