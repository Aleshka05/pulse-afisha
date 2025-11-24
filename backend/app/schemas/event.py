from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.event import EventStatus


class EventCategoryRead(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None

    class Config:
        from_attributes = True


class EventCategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)

class EventModerationAction(BaseModel):
    moderation_comment: str | None = Field(
        default=None,
        max_length=2000,
        description="Комментарий модератора (причина решения)",
    )

class EventBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=5000)

    category_id: int = Field(..., ge=1)

    starts_at: datetime
    ends_at: datetime | None = None

    address_text: str | None = Field(default=None, max_length=255)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

    is_free: bool = True
    price_from: int | None = Field(default=None, ge=0)
    capacity: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def check_dates(self) -> "EventBase":
        """Проверка, что конец не раньше начала."""
        if self.ends_at is not None and self.ends_at < self.starts_at:
            raise ValueError("Время окончания не может быть раньше начала")
        return self


class EventCreate(EventBase):
    """Данные для создания события."""
    pass


class EventUpdate(BaseModel):
    """Данные для обновления события (все поля опциональны)."""

    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=5000)

    category_id: int | None = Field(default=None, ge=1)

    starts_at: datetime | None = None
    ends_at: datetime | None = None

    address_text: str | None = Field(default=None, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    is_free: bool | None = None
    price_from: int | None = Field(default=None, ge=0)
    capacity: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def check_dates(self) -> "EventUpdate":
        """Если оба времени заданы, проверяем порядок."""
        if self.starts_at and self.ends_at and self.ends_at < self.starts_at:
            raise ValueError("Время окончания не может быть раньше начала")
        return self


class EventRead(BaseModel):
    id: int
    title: str
    description: str | None

    category: EventCategoryRead
    organizer_id: int

    status: EventStatus

    starts_at: datetime
    ends_at: datetime | None

    address_text: str | None
    latitude: float
    longitude: float

    is_free: bool
    price_from: int | None
    capacity: int | None

    created_at: datetime

    class Config:
        from_attributes = True
