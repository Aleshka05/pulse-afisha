from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User
from app.models.event import Event


class FavoriteEvent(Base):
  __tablename__ = "favorite_event"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
  user_id: Mapped[int] = mapped_column(
      ForeignKey("user.id", ondelete="CASCADE"),
      nullable=False,
      index=True,
  )
  event_id: Mapped[int] = mapped_column(
      ForeignKey("event.id", ondelete="CASCADE"),
      nullable=False,
      index=True,
  )
  created_at: Mapped[datetime] = mapped_column(
      DateTime(timezone=True),
      default=datetime.utcnow,
      nullable=False,
  )

  user: Mapped[User] = relationship()
  event: Mapped[Event] = relationship()

  __table_args__ = (
      UniqueConstraint("user_id", "event_id", name="uq_favorite_user_event"),
  )
