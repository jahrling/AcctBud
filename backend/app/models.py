from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PushSubscription(Base):
    __tablename__ = "push_subscription"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    endpoint: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    subscription_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)


class Task(Base):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    sort_order: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class CheckIn(Base):
    __tablename__ = "check_in"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    for_date: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    followup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    journal_written: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    items: Mapped[list["CheckInItem"]] = relationship(
        back_populates="check_in", cascade="all, delete-orphan"
    )
    reflection_finished: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    reflection_journal_written: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    reflection_messages: Mapped[list["ReflectionMessage"]] = relationship(
        back_populates="check_in", cascade="all, delete-orphan"
    )


class CheckInItem(Base):
    __tablename__ = "check_in_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    check_in_id: Mapped[int] = mapped_column(Integer, ForeignKey("check_in.id"), nullable=False)
    task_id: Mapped[int] = mapped_column(Integer, nullable=False)
    task_title: Mapped[str] = mapped_column(String, nullable=False)
    task_category: Mapped[str] = mapped_column(String, nullable=False)
    done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    check_in: Mapped["CheckIn"] = relationship(back_populates="items")


class ReflectionMessage(Base):
    __tablename__ = "reflection_message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    check_in_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("check_in.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    check_in: Mapped["CheckIn"] = relationship(back_populates="reflection_messages")


class NotificationLog(Base):
    __tablename__ = "notification_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    subscription_id: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[str] = mapped_column(String, nullable=False)
