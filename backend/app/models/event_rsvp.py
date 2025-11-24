import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User
from app.models.event import Event


class RSVPStatus(str, enum.Enum):
    going = "going"
    interested = "interested"
    canceled = "canceled"


class EventRSVP(Base):
    """Отклик пользователя на событие (RSVP)."""

    __tablename__ = "event_rsvp"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "event_id",
            name="uq_event_rsvp_user_event",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user: Mapped[User] = relationship()

    event_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("event.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event: Mapped[Event] = relationship()

    status: Mapped[RSVPStatus] = mapped_column(
        Enum(RSVPStatus, name="event_rsvp_status_enum"),
        nullable=False,
        default=RSVPStatus.interested,
        index=True,
    )

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
