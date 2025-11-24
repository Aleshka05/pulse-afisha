from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import role_required
from app.db.session import get_session
from app.models.event import EventCategory
from app.models.user import UserRole
from app.schemas.event import EventCategoryCreate, EventCategoryRead

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[EventCategoryRead])
async def list_categories(
    session: AsyncSession = Depends(get_session),
) -> list[EventCategoryRead]:
    """Список всех категорий событий."""
    result = await session.execute(select(EventCategory).order_by(EventCategory.name))
    categories = result.scalars().all()
    return [EventCategoryRead.model_validate(c) for c in categories]


@router.post(
    "/",
    response_model=EventCategoryRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(role_required(UserRole.admin))],
)
async def create_category(
    payload: EventCategoryCreate,
    session: AsyncSession = Depends(get_session),
) -> EventCategoryRead:
    """Создание новой категории (только админ)."""
    exists_query = select(EventCategory).where(
        (EventCategory.name == payload.name) | (EventCategory.slug == payload.slug)
    )
    exists = await session.execute(exists_query)
    if exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Категория с таким названием или slug уже существует",
        )

    category = EventCategory(
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return EventCategoryRead.model_validate(category)
