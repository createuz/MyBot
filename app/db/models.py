# app/db/models.py
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Integer, String, DateTime, BigInteger, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_premium: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # NULL until user confirms
    added_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
