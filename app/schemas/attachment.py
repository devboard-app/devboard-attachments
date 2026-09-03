import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.attachment import StatusEnum

MAX_BATCH_SIZE = 100
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

class ResolveResponse(BaseModel):
    url: str

class BatchRequest(BaseModel):
    attachment_ids: list[uuid.UUID] = Field(..., max_length=MAX_BATCH_SIZE)
    owner_id: uuid.UUID | None = None
class ResolvedAttachment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:uuid.UUID
    filename: str
    content_type: str
    size: int | None
    url: str