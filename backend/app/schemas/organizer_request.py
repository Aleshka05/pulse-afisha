from datetime import datetime

from pydantic import BaseModel, Field

from app.models.organizer_request import OrganizerRequestStatus


class OrganizerRequestCreate(BaseModel):
    message: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Коротко: кто вы и зачем вам роль организатора",
    )


class OrganizerRequestRead(BaseModel):
    id: int
    user_id: int
    status: OrganizerRequestStatus
    message: str | None
    admin_comment: str | None
    created_at: datetime
    resolved_at: datetime | None

    class Config:
        from_attributes = True
