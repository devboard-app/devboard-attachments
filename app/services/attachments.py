import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import (
    FileTooLargeException,
    InvalidTypeFileException,
    TooManyAttachmentsException,
)
from app.repositories.attachment import count_by_context, create_pending
from app.schemas.attachment import UploadRequest, UploadResponse
from app.storage import presign_put

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_PER_CONTEXT = 5


async def request_upload(data: UploadRequest, owner_id: uuid.UUID, db: AsyncSession)-> UploadResponse:
    if data.content_type not in ALLOWED_TYPES:
        raise InvalidTypeFileException()
    if data.size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise FileTooLargeException()
    if data.context_type is not None and data.context_id is not None and await count_by_context(data.context_type, data.context_id, db) >= MAX_PER_CONTEXT:
        raise TooManyAttachmentsException()


    attachment_id = uuid.uuid4()
    storage_key = f"{attachment_id}/{data.filename}"

    attachment = await create_pending(
        attachment_id=attachment_id,
        owner_id=owner_id,
        filename=data.filename,
        content_type=data.content_type,
        size=data.size,
        storage_key=storage_key,
        context_type=data.context_type,
        context_id=data.context_id,
        db=db,
    )
    await db.commit()

    upload_url = await presign_put(storage_key)
    return UploadResponse(attachment_id=attachment.id, upload_url=upload_url)
    