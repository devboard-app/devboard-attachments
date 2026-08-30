import uuid
from io import BytesIO

from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import (
    AttachmentNotFoundException,
    AttachmentNotStoredException,
    FileNotUploadedException,
    FileSizeMissmatchException,
    FileTooLargeException,
    InvalidTypeFileException,
    NotAttachmentOwnerException,
    TooManyAttachmentsException,
)
from app.models.attachment import Attachment, StatusEnum
from app.repositories.attachment import (
    count_by_context,
    create_pending,
    delete_attachment,
    get_attachment_by_id,
    get_stored_by_ids,
    mark_attachment_stored,
)
from app.schemas.attachment import UploadRequest, UploadResponse
from app.storage import (
    delete_object,
    download_object,
    presign_get,
    presign_put,
    stat_object,
)

FORMAT_TO_TYPE = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp", "GIF": "image/gif"}


def _valid_image(data: bytes, content_type: str) -> bool:
    try:
        with Image.open(BytesIO(data)) as img:
            fmt = img.format
            img.verify()
    except Exception:  # noqa: BLE001
        return False
    return fmt is not None and FORMAT_TO_TYPE.get(fmt) == content_type

def _valid_pdf(data: bytes, content_type: str) -> bool:
    return data.startswith(b"%PDF-")

def _valid_text(data: bytes, content_type: str) -> bool:
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False
    
CONTENT_VALIDATORS = {
    "image/png":  _valid_image,
    "image/jpeg": _valid_image,
    "image/webp": _valid_image,
    "image/gif":  _valid_image,
    "application/pdf": _valid_pdf,
    "text/plain": _valid_text,
}
ALLOWED_TYPES = set(CONTENT_VALIDATORS) 

async def request_upload(data: UploadRequest, owner_id: uuid.UUID, db: AsyncSession)-> UploadResponse:
    if data.content_type not in ALLOWED_TYPES:
        raise InvalidTypeFileException()
    if data.size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise FileTooLargeException()
    if data.context_type is not None and data.context_id is not None and await count_by_context(data.context_type, data.context_id, db) >= settings.MAX_ATTACHMENTS_PER_CONTEXT:
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

async def _rollback(attachment, db):
    await delete_object(attachment.storage_key)
    await delete_attachment(attachment, db)
    await db.commit()

async def confirm_upload(attachment_id: uuid.UUID, owner_id: uuid.UUID, db: AsyncSession) -> Attachment:
    attachment = await get_attachment_by_id(attachment_id, db)
    if attachment is None :
        raise AttachmentNotFoundException()
    if attachment.owner_id != owner_id:
        raise NotAttachmentOwnerException()
    if attachment.status == StatusEnum.stored:
        return attachment

    real_size = await stat_object(attachment.storage_key)
    if real_size is None:
        await _rollback(attachment, db)
        raise FileNotUploadedException()
    if real_size != attachment.size:
        await _rollback(attachment, db)
        raise FileSizeMissmatchException()
    if real_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        await _rollback(attachment, db)
        raise FileTooLargeException()

    data = await download_object(attachment.storage_key)
    validator = CONTENT_VALIDATORS.get(attachment.content_type)
    if validator is None or not validator(data, attachment.content_type):
        await _rollback(attachment, db)
        raise InvalidTypeFileException()

    await mark_attachment_stored(attachment, real_size, db)
    await db.commit()
    return attachment

async def resolve_url(attachment_id: uuid.UUID, owner_id: uuid.UUID, db: AsyncSession) -> str:
    attachment = await get_attachment_by_id(attachment_id, db)
    if attachment is None:
        raise AttachmentNotFoundException()
    if attachment.owner_id != owner_id:
        raise NotAttachmentOwnerException()
    if attachment.status != StatusEnum.stored:
        raise AttachmentNotStoredException()
    return await presign_get(attachment.storage_key, attachment.filename, attachment.content_type)

async def delete_by_id(attachment_id: uuid.UUID, owner_id: uuid.UUID, db: AsyncSession) -> None:
    attachment = await get_attachment_by_id(attachment_id, db)
    if attachment is None:
        raise AttachmentNotFoundException()
    if attachment.owner_id != owner_id:
        raise NotAttachmentOwnerException()
    await delete_object(attachment.storage_key)
    await delete_attachment(attachment, db)
    await db.commit()

async def resolve_batch(ids: list[uuid.UUID], db: AsyncSession) -> list[dict]:
    attachments = await get_stored_by_ids(ids, db)
    out = []
    for a in attachments:
        url = await presign_get(a.storage_key, a.filename, a.content_type)
        out.append({"id": a.id, "filename": a.filename, "content_type": a.content_type, "size": a.size, "url": url})
    return out