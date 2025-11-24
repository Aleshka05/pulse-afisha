from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user, role_required
from app.db.session import get_session
from app.models.event import Event, EventCategory, EventStatus
from app.models.user import User, UserRole
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, or_, select, func, delete
from app.models.event_rsvp import EventRSVP, RSVPStatus
from app.schemas.rsvp import EventRSVPMutate, EventRSVPRead, EventRSVPStats

from app.schemas.event import EventCreate, EventRead, EventUpdate, EventModerationAction


router = APIRouter(
    prefix="/events",
    tags=["events"],
)


@router.get("/", response_model=list[EventRead])
async def list_events(
    session: AsyncSession = Depends(get_session),
    category_id: int | None = Query(default=None, ge=1),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    q: str | None = Query(default=None, min_length=1),
    lat_min: float | None = Query(default=None, ge=-90, le=90),
    lat_max: float | None = Query(default=None, ge=-90, le=90),
    lng_min: float | None = Query(default=None, ge=-180, le=180),
    lng_max: float | None = Query(default=None, ge=-180, le=180),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[EventRead]:
    """
    Список опубликованных событий с фильтрами.

    Используется лентой и картой. Гости видят только опубликованные события.
    """
    conditions = [Event.status == EventStatus.published]

    if category_id is not None:
        conditions.append(Event.category_id == category_id)

    if date_from is not None:
        conditions.append(Event.starts_at >= date_from)
    if date_to is not None:
        conditions.append(Event.starts_at <= date_to)

    if q:
        # упрощённый поиск по заголовку/описанию
        like = f"%{q}%"
        conditions.append(or_(Event.title.ilike(like), Event.description.ilike(like)))

    if None not in (lat_min, lat_max, lng_min, lng_max):
        conditions.append(
            and_(
                Event.latitude >= lat_min,  # type: ignore[arg-type]
                Event.latitude <= lat_max,  # type: ignore[arg-type]
                Event.longitude >= lng_min,  # type: ignore[arg-type]
                Event.longitude <= lng_max,  # type: ignore[arg-type]
            )
        )

    stmt = (
        select(Event)
        .options(selectinload(Event.category))
        .where(and_(*conditions))
        .order_by(Event.starts_at)
        .limit(limit)
        .offset(offset)
    )

    result = await session.execute(stmt)
    events = result.scalars().unique().all()
    return [EventRead.model_validate(e) for e in events]

@router.get("/my", response_model=list[EventRead])
async def list_my_events(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    status_filter: EventStatus | None = Query(default=None),
) -> list[EventRead]:
    """
    Список событий текущего пользователя (организатора).

    Доступен любому авторизованному пользователю.
    По умолчанию не показывает архивные события.
    """
    conditions = [Event.organizer_id == current_user.id]

    if status_filter is not None:
        conditions.append(Event.status == status_filter)
    else:
        # по умолчанию скрываем архив
        conditions.append(Event.status != EventStatus.archived)

    stmt = (
        select(Event)
        .options(selectinload(Event.category))
        .where(and_(*conditions))
        .order_by(Event.created_at.desc())
    )

    result = await session.execute(stmt)
    events = result.scalars().unique().all()
    return [EventRead.model_validate(e) for e in events]


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: int,
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    """
    Получение одного события по id.

    Для публичного просмотра: отдаём только опубликованные события.
    """
    stmt = (
    select(Event)
    .options(selectinload(Event.category))
    .where(
        Event.id == event_id,
        Event.status == EventStatus.published,
    )
)
    result = await session.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Событие не найдено",
        )

    return EventRead.model_validate(event)

@router.post(
    "/{event_id}/rsvp",
    response_model=EventRSVPRead,
    status_code=status.HTTP_200_OK,
)
async def set_event_rsvp(
    event_id: int,
    payload: EventRSVPMutate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EventRSVPRead:
    """
    Установка или изменение RSVP текущего пользователя на событие.

    Статусы:
    - going      — иду
    - interested — интересно
    - canceled   — отмена (по сути, пользователь передумал)
    """
    # Проверяем, что событие существует и опубликовано
    stmt_event = select(Event).where(
        Event.id == event_id,
        Event.status == EventStatus.published,
    )
    res_event = await session.execute(stmt_event)
    event = res_event.scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Событие не найдено или не опубликовано",
        )

    # На свои события тоже можно ставить RSVP, но смысла немного, оставляем как есть

    # Ищем существующий отклик
    stmt_rsvp = select(EventRSVP).where(
        EventRSVP.user_id == current_user.id,
        EventRSVP.event_id == event_id,
    )
    res_rsvp = await session.execute(stmt_rsvp)
    rsvp = res_rsvp.scalar_one_or_none()

    if rsvp is None:
        rsvp = EventRSVP(
            user_id=current_user.id,
            event_id=event_id,
            status=payload.status,
        )
        session.add(rsvp)
    else:
        rsvp.status = payload.status
        session.add(rsvp)

    await session.commit()
    await session.refresh(rsvp)

    return EventRSVPRead.model_validate(rsvp)

@router.get(
    "/{event_id}/rsvp/my",
    response_model=EventRSVPRead | None,
)
async def get_my_event_rsvp(
    event_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EventRSVPRead | None:
    """
    Текущий RSVP пользователя на событие (или null, если не откликался).
    """
    stmt = select(EventRSVP).where(
        EventRSVP.user_id == current_user.id,
        EventRSVP.event_id == event_id,
    )
    res = await session.execute(stmt)
    rsvp = res.scalar_one_or_none()

    if rsvp is None:
        return None

    return EventRSVPRead.model_validate(rsvp)

@router.get(
    "/{event_id}/rsvp/stats",
    response_model=EventRSVPStats,
)
async def get_event_rsvp_stats(
    event_id: int,
    session: AsyncSession = Depends(get_session),
) -> EventRSVPStats:
    """
    Простая статистика откликов по событию.
    """
    stmt = (
        select(EventRSVP.status, func.count())
        .where(EventRSVP.event_id == event_id)
        .group_by(EventRSVP.status)
    )
    res = await session.execute(stmt)
    rows = res.all()

    counts = {
        RSVPStatus.going: 0,
        RSVPStatus.interested: 0,
        RSVPStatus.canceled: 0,
    }

    for status_value, cnt in rows:
        counts[status_value] = cnt

    return EventRSVPStats(
        going=counts[RSVPStatus.going],
        interested=counts[RSVPStatus.interested],
        canceled=counts[RSVPStatus.canceled],
    )
    
@router.get(
    "/{event_id}/rsvp/list",
    response_model=list[EventRSVPRead],
)
async def list_event_rsvps_for_organizer(
    event_id: int,
    current_user: User = Depends(
        role_required(UserRole.organizer, UserRole.admin)
    ),
    session: AsyncSession = Depends(get_session),
) -> list[EventRSVPRead]:
    """
    Список всех RSVP по событию.

    Организатор может смотреть только по своим событиям,
    админ — по любым.
    """
    stmt_event = select(Event).where(Event.id == event_id)
    res_event = await session.execute(stmt_event)
    event = res_event.scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Событие не найдено",
        )

    if (
        current_user.role != UserRole.admin
        and event.organizer_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к откликам на это событие",
        )

    stmt = (
        select(EventRSVP)
        .where(EventRSVP.event_id == event_id)
        .order_by(EventRSVP.created_at.desc())
    )
    res = await session.execute(stmt)
    rsvps = res.scalars().unique().all()

    return [EventRSVPRead.model_validate(r) for r in rsvps]

@router.get("/{event_id}/manage", response_model=EventRead)
async def get_event_for_manage(
    event_id: int,
    current_user: User = Depends(
        role_required(UserRole.organizer, UserRole.admin)
    ),
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    """
    Получение события для управления (редактирование/отправка на модерацию).

    Доступно только организатору этого события или администратору.
    Статус события не ограничиваем.
    """
    stmt = (
        select(Event)
        .options(selectinload(Event.category))
        .where(Event.id == event_id)
    )
    result = await session.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Событие не найдено",
        )

    if current_user.role != UserRole.admin and event.organizer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя управлять чужим событием",
        )

    return EventRead.model_validate(event)

@router.put("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: int,
    payload: EventUpdate,
    current_user: User = Depends(
        role_required(UserRole.organizer, UserRole.admin)
    ),
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    """
    Обновление события.

    Организатор может редактировать только свои события.
    Обычно редактирование разрешено в статусах draft / rejected.
    """
    stmt = select(Event).where(Event.id == event_id)
    result = await session.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Событие не найдено",
        )

    if current_user.role != UserRole.admin and event.organizer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя редактировать чужое событие",
        )

    if event.status not in (EventStatus.draft, EventStatus.rejected) and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Редактировать можно только черновики или отклонённые события",
        )

    # Применяем изменения, если поля заданы
    if payload.title is not None:
        event.title = payload.title
    if payload.description is not None:
        event.description = payload.description
    if payload.category_id is not None:
        # проверим, что категория существует
        cat_stmt = select(EventCategory).where(EventCategory.id == payload.category_id)
        cat_res = await session.execute(cat_stmt)
        if cat_res.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Указанная категория не существует",
            )
        event.category_id = payload.category_id

    if payload.starts_at is not None:
        event.starts_at = payload.starts_at
    if payload.ends_at is not None:
        event.ends_at = payload.ends_at

    if payload.address_text is not None:
        event.address_text = payload.address_text
    if payload.latitude is not None:
        event.latitude = payload.latitude
    if payload.longitude is not None:
        event.longitude = payload.longitude

    if payload.is_free is not None:
        event.is_free = payload.is_free
        if payload.is_free:
            event.price_from = None

    if payload.price_from is not None:
        event.price_from = payload.price_from

    if payload.capacity is not None:
        event.capacity = payload.capacity

    session.add(event)
    await session.commit()
    await session.refresh(event)
    return EventRead.model_validate(event)

@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    current_user: User = Depends(
        role_required(UserRole.organizer, UserRole.admin)
    ),
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Удаление события.

    Организатор может удалять только свои события.
    По умолчанию разрешаем удалять черновики и отклонённые события.
    Администратор может удалять любое событие.
    """
    stmt = select(Event).where(Event.id == event_id)
    result = await session.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Событие не найдено",
        )

    # Организатор — только свои
    if current_user.role != UserRole.admin and event.organizer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя удалять чужое событие",
        )

    # Ограничение по статусу для организатора
    if (
        current_user.role != UserRole.admin
        and event.status not in (EventStatus.draft, EventStatus.rejected, EventStatus.archived)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Удалять можно только черновики, отклонённые или архивные события",
        )

    await session.delete(event)
    await session.commit()

@router.post("/{event_id}/submit", response_model=EventRead)
async def submit_event_for_moderation(
    event_id: int,
    current_user: User = Depends(
        role_required(UserRole.organizer, UserRole.admin)
    ),
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    """
    Отправка события на модерацию.

    Можно отправить только свои события в статусе draft или rejected.
    """
    stmt = select(Event).where(Event.id == event_id)
    result = await session.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Событие не найдено",
        )

    if current_user.role != UserRole.admin and event.organizer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя отправлять на модерацию чужое событие",
        )

    if event.status not in (EventStatus.draft, EventStatus.rejected):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Отправить на модерацию можно только черновик или отклонённое событие",
        )

    event.status = EventStatus.pending_moderation
    event.moderation_comment = None  # очищаем старый комментарий

    session.add(event)
    await session.commit()
    await session.refresh(event)
    return EventRead.model_validate(event)


@router.post(
    "/",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_event(
    payload: EventCreate,
    current_user: User = Depends(
        role_required(UserRole.organizer, UserRole.admin)
    ),
    session: AsyncSession = Depends(get_session),
) -> EventRead:
    """
    Создание события организатором.

    По умолчанию создаём в статусе draft — публикация пойдёт через модерацию.
    """
    # Проверим, что категория существует
    cat_stmt = select(EventCategory).where(EventCategory.id == payload.category_id)
    cat_res = await session.execute(cat_stmt)
    category = cat_res.scalar_one_or_none()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Указанная категория не существует",
        )

    event = Event(
        title=payload.title,
        description=payload.description,
        category_id=payload.category_id,
        organizer_id=current_user.id,
        status=EventStatus.draft,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        address_text=payload.address_text,
        latitude=payload.latitude,
        longitude=payload.longitude,
        is_free=payload.is_free,
        price_from=payload.price_from,
        capacity=payload.capacity,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return EventRead.model_validate(event)



