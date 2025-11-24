from datetime import datetime

from pydantic import BaseModel, Field

from app.models.support_ticket import SupportTicketStatus


class SupportTicketCreate(BaseModel):
    subject: str = Field(..., min_length=3, max_length=255)
    message: str = Field(..., min_length=10, max_length=5000)


class SupportTicketRead(BaseModel):
    id: int
    user_id: int
    subject: str
    message: str
    status: SupportTicketStatus
    admin_reply: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SupportTicketReply(BaseModel):
    reply: str = Field(..., min_length=3, max_length=5000)
