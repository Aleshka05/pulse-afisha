from datetime import datetime

from pydantic import BaseModel

from app.models.event_rsvp import RSVPStatus
from app.schemas.event import EventRead  # ← ДОБАВИТЬ этот импорт


class EventRSVPMutate(BaseModel):
    status: RSVPStatus


class EventRSVPRead(BaseModel):
    id: int
    user_id: int
    event_id: int
    status: RSVPStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EventRSVPStats(BaseModel):
    going: int
    interested: int
    canceled: int


class MyRSVPItem(BaseModel):
    """
    Отклик текущего пользователя с вложенным событием.
    Используется для /rsvp/my.
    """

    id: int
    user_id: int
    event_id: int
    status: RSVPStatus
    created_at: datetime
    updated_at: datetime
    event: EventRead

    class Config:
        from_attributes = True
