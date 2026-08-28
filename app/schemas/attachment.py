import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.attachment import StatusEnum


class UploadRequest(BaseModel):
    filename: str
    content_type: str
    size: int
    context_type: str | None = None
    context_id: uuid.UUID | None = None

class UploadResponse(BaseModel):
    attachment_id: uuid.UUID
    upload_url: str

class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    content_type: str
    size: int | None
    status: StatusEnum
    context_type: str | None
    context_id: uuid.UUID | None
    created_at: datetime