from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum,
    ForeignKey, Integer, String, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class PracticeType(str, PyEnum):
    tomiris = "tomiris"
    curator = "curator"


class Student(Base):
    __tablename__ = "students"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    stream_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    group_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Student tg={self.telegram_id} group={self.group_name}>"


class Curator(Base):
    __tablename__ = "curators"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    curator_groups: Mapped[List["CuratorGroup"]] = relationship(
        "CuratorGroup", back_populates="curator", cascade="all, delete-orphan"
    )
    practices: Mapped[List["Practice"]] = relationship(
        "Practice", back_populates="curator"
    )


class CuratorGroup(Base):
    __tablename__ = "curator_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    curator_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("curators.telegram_id", ondelete="CASCADE"), nullable=False
    )
    group_name: Mapped[str] = mapped_column(String(100), nullable=False)
    stream_name: Mapped[str] = mapped_column(String(100), nullable=False)

    curator: Mapped["Curator"] = relationship("Curator", back_populates="curator_groups")


class Practice(Base):
    __tablename__ = "practices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_name: Mapped[str] = mapped_column(String(100), nullable=False)
    stream_name: Mapped[str] = mapped_column(String(100), nullable=False)
    curator_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("curators.telegram_id", ondelete="CASCADE"), nullable=False
    )
    practice_type: Mapped[PracticeType] = mapped_column(
        Enum(PracticeType, name="practice_type_enum"), nullable=False
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    curator: Mapped["Curator"] = relationship("Curator", back_populates="practices")


class TomirisReminderSent(Base):
    __tablename__ = "tomiris_reminders_sent"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_name: Mapped[str] = mapped_column(String(100), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    label: Mapped[str] = mapped_column(String(20), nullable=False)
