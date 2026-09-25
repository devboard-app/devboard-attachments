import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attachment import Attachment, StatusEnum

PENDING_COUNT_MAX_AGE_HOURS = 1  # matches cleanup.PENDING_MAX_AGE_HOURS


async def create_pending(
    attachment_id: uuid.UUID,
    owner_id: uuid.UUID,
    filename: str,
    content_type: str,
    size: int,
    storage_key: str,
    db: AsyncSession,
    is_public: bool = False,
) -> Attachment:
    attachment = Attachment(
        id=attachment_id,
        owner_id=owner_id,
        filename=filename,
        content_type=content_type,
        size=size,
        storage_key=storage_key,
        is_public=is_public,
        status=StatusEnum.pending,
    )
    db.add(attachment)
    await db.flush()
    await db.refresh(attachment)
    return attachment

async def get_attachment_by_id(attachment_id: uuid.UUID, db: AsyncSession, for_update: bool = False) -> Attachment | None:
    query = select(Attachment).where(Attachment.id == attachment_id)
    if for_update:
        query = query.with_for_update()
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def mark_attachment_stored(attachment: Attachment, real_size: int, db: AsyncSession) -> None:
    attachment.status = StatusEnum.stored
    attachment.size = real_size
    await db.flush()

async def delete_attachment(attachment: Attachment, db: AsyncSession) -> None:
    await db.delete(attachment)
    await db.flush()

async def get_stored_by_ids(ids: list[uuid.UUID], db: AsyncSession, owner_id: uuid.UUID | None = None) -> list[Attachment]:
    if not ids:
        return []
    query = select(Attachment).where(Attachment.id.in_(ids), Attachment.status == StatusEnum.stored)
    if owner_id is not None:
        query = query.where(Attachment.owner_id == owner_id)
    result = await db.execute(query)
    return list(result.scalars().all())

async def count_by_owner(owner_id: uuid.UUID, db: AsyncSession) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=PENDING_COUNT_MAX_AGE_HOURS)
    query = select(func.count()).select_from(Attachment).where(
        Attachment.owner_id == owner_id,
        (Attachment.status == StatusEnum.stored)
        | ((Attachment.status == StatusEnum.pending) & (Attachment.created_at >= cutoff)),
    )
    result = await db.execute(query)
    return result.scalar_one()