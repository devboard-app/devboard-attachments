import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.attachment import StatusEnum

MAX_BATCH_SIZE = 100
_UNSAFE_FILENAME = re.compile(r"[/\\]")
class UploadRequest(BaseModel):
    filename: str
    content_type: str
    size: int

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if not v or v in {".", ".."} or _UNSAFE_FILENAME.search(v):
            raise ValueError("Filename must not contain path separators")
        return v
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