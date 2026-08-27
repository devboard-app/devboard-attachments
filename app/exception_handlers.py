from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.exceptions import (
    AttachmentNotFoundException,
    InvalidTypeFileException,
    TooManyAttachmentsException,
)


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(AttachmentNotFoundException)
    async def attachment_not_found_handler(request, exc):
        return JSONResponse(status_code=404, content={"detail": "Attachment not found"})
    
    @app.exception_handler(InvalidTypeFileException)
    async def invalid_type_file_handler(request, exc):
        return JSONResponse(status_code=415, content={"detail": "Invalid type file"})
    
    @app.exception_handler(TooManyAttachmentsException)
    async def too_many_attachments_handler(request, exc):
        return JSONResponse(status_code=415, content={"detail": "Too many attachments."})