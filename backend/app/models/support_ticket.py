import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User


class SupportTicketStatus(str, enum.Enum):
    open = "open"
    answered = "answered"
    closed = "closed"


class SupportTicket(Base):
    """Обращение/жалоба пользователя в поддержку."""

    __tablename__ = "support_ticket"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
      Integer,
      ForeignKey("user.id", ondelete="CASCADE"),
      nullable=False,
      index=True,
    )
    user: Mapped[User] = relationship()

    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[SupportTicketStatus] = mapped_column(
        Enum(SupportTicketStatus, name="support_ticket_status_enum"),
        nullable=False,
        default=SupportTicketStatus.open,
        index=True,
    )

    admin_reply: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
