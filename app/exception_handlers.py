from fastapi import FastAPI
from fastapi.responses import JSONResponse

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


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(AttachmentNotFoundException)
    async def attachment_not_found_handler(request, exc):
        return JSONResponse(status_code=404, content={"detail": "Attachment not found"})
    
    @app.exception_handler(InvalidTypeFileException)
    async def invalid_type_file_handler(request, exc):
        return JSONResponse(status_code=415, content={"detail": "Invalid type file"})
    
    @app.exception_handler(TooManyAttachmentsException)
    async def too_many_attachments_handler(request, exc):
        return JSONResponse(status_code=409, content={"detail": f"Maximum {settings.MAX_ATTACHMENTS_PER_CONTEXT} attachments per context."})

    @app.exception_handler(FileTooLargeException)
    async def file_too_large_handler(request, exc):
        return JSONResponse(status_code=413, content={"detail": "File size too large."})

    @app.exception_handler(FileNotUploadedException)
    async def file_not_uploaded_handler(request, exc):
        return JSONResponse(status_code=409, content={"detail": "File was not uploaded."})

    @app.exception_handler(FileSizeMissmatchException)
    async def file_size_missmatch_handler(request, exc):
        return JSONResponse(status_code=409, content={"detail": "File size missmatch."})
    
    @app.exception_handler(NotAttachmentOwnerException)
    async def not_attachment_owner_handler(request, exc):
        return JSONResponse(status_code=403, content={"detail": "Forbidden."})
    
    @app.exception_handler(AttachmentNotStoredException)
    async def attachment_not_stored_handler(request, exc):
        return JSONResponse(status_code=409, content={"detail": "Attachment is not stored."})