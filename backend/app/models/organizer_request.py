import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User


class OrganizerRequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class OrganizerRequest(Base):
    """Заявка пользователя на получение роли организатора."""

    __tablename__ = "organizer_request"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user: Mapped[User] = relationship()

    status: Mapped[OrganizerRequestStatus] = mapped_column(
        Enum(OrganizerRequestStatus, name="organizer_request_status_enum"),
        nullable=False,
        index=True,
        default=OrganizerRequestStatus.pending,
    )

    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Сообщение пользователя: кто он, почему хочет стать организатором",
    )

    admin_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Комментарий администратора при одобрении/отклонении",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
