import uuid

from pydantic import BaseModel


class UploadRequest(BaseModel):
    filename: str
    content_type: str
    size: int
    context_type: str | None = None
    context_id: uuid.UUID | None = None

class UploadResponse(BaseModel):
    attachment_id: uuid.UUID
    upload_url: str