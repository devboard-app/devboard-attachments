import asyncio
import logging
import uuid
from contextlib import AsyncExitStack

from redis.asyncio import Redis
from redis.exceptions import ResponseError
from sqlalchemy import delete, select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.attachment import Attachment
from app.storage import delete_object, init_storage

STREAM = "devboard:events"
GROUP = "devboard-attachments-group"
CONSUMER = "devboard-attachments-1"

PENDING_SCAN_LIMIT = 5000

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


async def ensure_group(redis: Redis) -> None:
    try:
        await redis.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
        logger.info("Consumer group created.")
    except ResponseError as e:
        if "BUSYGROUP" in str(e):
            logger.info("Consumer group already exists.")
        else:
            raise


async def delete_attachments(attachment_ids: list[uuid.UUID]) -> None:
    if not attachment_ids:
        return
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(select(Attachment).where(Attachment.id.in_(attachment_ids)))
        ).scalars().all()
        for row in rows:
            try:
                await delete_object(row.storage_key)
            except Exception:
                logger.exception("could not delete object %s", row.storage_key)
        await db.execute(delete(Attachment).where(Attachment.id.in_(attachment_ids)))
        await db.commit()
    logger.info("deleted %d attachment(s): %s", len(rows), attachment_ids)


async def run() -> None:
    async with AsyncExitStack() as stack:
        await init_storage(stack)
        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=10)
        await ensure_group(redis)
        logger.info("Consumer started, waiting for events...")

        while True:
            try:
                claimed = []
                cursor = "0-0"
                for _ in range(50):
                    cursor, batch, _ = await redis.xautoclaim(
                        STREAM, GROUP, CONSUMER, min_idle_time=30000, start_id=cursor, count=100
                    )
                    claimed.extend(batch)
                    if cursor == "0-0":
                        break
                else:
                    logger.warning("Reclaim scan hit the iteration cap, continuing anyway")

                results = await redis.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=10, block=5000)
                all_messages = claimed + (results[0][1] if results else [])  # type: ignore

                for message_id, data in all_messages:  # type: ignore
                    if data.get("event") != "comment.deleted":
                        await redis.xack(STREAM, GROUP, message_id)
                        continue
                    try:
                        raw_ids = data.get("attachment_ids", "")
                        attachment_ids = [uuid.UUID(i) for i in raw_ids.split(",") if i]
                        await delete_attachments(attachment_ids)
                        await redis.xack(STREAM, GROUP, message_id)
                    except Exception:
                        logger.exception("failed to process comment.deleted message %s", message_id)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Consumer error: {e}")
                await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run())