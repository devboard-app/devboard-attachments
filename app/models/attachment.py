import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from urllib.parse import quote

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.database import Base


class StatusEnum(PyEnum):
    pending = "pending"
    stored = "stored"


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(255))
    size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_key: Mapped[str] = mapped_column(Text)
    status: Mapped[StatusEnum] = mapped_column(Enum(StatusEnum), default=StatusEnum.pending, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True) ,default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    @property
    def public_url(self) -> str | None:
        if not self.is_public or self.status != StatusEnum.stored:
            return None
        return f"{settings.S3_PUBLIC_ENDPOINT_URL}/{settings.S3_BUCKET}/{quote(self.storage_key)}"