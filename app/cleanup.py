import asyncio
import logging
from contextlib import AsyncExitStack
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.attachment import Attachment, StatusEnum
from app.storage import delete_object, init_storage

logger = logging.getLogger("cleanup")

PENDING_MAX_AGE_HOURS = 24


async def cleanup_pending(max_age_hours: int = PENDING_MAX_AGE_HOURS) -> tuple[int, int]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    objects_deleted = 0

    async with AsyncExitStack() as stack:
        await init_storage(stack)
        async with AsyncSessionLocal() as db:
            rows = (
                await db.execute(
                    select(Attachment).where(
                        Attachment.status == StatusEnum.pending,
                        Attachment.created_at < cutoff,
                    )
                )
            ).scalars().all()

            for a in rows:
                try:
                    await delete_object(a.storage_key)
                    objects_deleted += 1
                except Exception:
                    logger.exception("could not delete object %s", a.storage_key)
                await db.delete(a)
            await db.commit()

    logger.info(
        "cleanup: removed %d pending rows older than %dh, deleted %d objects",
        len(rows), max_age_hours, objects_deleted,
    )
    return len(rows), objects_deleted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(cleanup_pending())