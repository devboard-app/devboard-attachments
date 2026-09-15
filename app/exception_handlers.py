from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
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
        return JSONResponse(status_code=404, content={"detail": "Attachment not found", "errors": None})

    @app.exception_handler(InvalidTypeFileException)
    async def invalid_type_file_handler(request, exc):
        return JSONResponse(status_code=415, content={"detail": "Invalid type file", "errors": None})

    @app.exception_handler(TooManyAttachmentsException)
    async def too_many_attachments_handler(request, exc):
        return JSONResponse(status_code=409, content={"detail": f"Maximum {settings.MAX_ATTACHMENTS_PER_CONTEXT} attachments per context.", "errors": None})

    @app.exception_handler(FileTooLargeException)
    async def file_too_large_handler(request, exc):
        return JSONResponse(status_code=413, content={"detail": "File size too large.", "errors": None})

    @app.exception_handler(FileNotUploadedException)
    async def file_not_uploaded_handler(request, exc):
        return JSONResponse(status_code=409, content={"detail": "File was not uploaded.", "errors": None})

    @app.exception_handler(FileSizeMissmatchException)
    async def file_size_missmatch_handler(request, exc):
        return JSONResponse(status_code=409, content={"detail": "File size missmatch.", "errors": None})

    @app.exception_handler(NotAttachmentOwnerException)
    async def not_attachment_owner_handler(request, exc):
        return JSONResponse(status_code=403, content={"detail": "Forbidden.", "errors": None})

    @app.exception_handler(AttachmentNotStoredException)
    async def attachment_not_stored_handler(request, exc):
        return JSONResponse(status_code=409, content={"detail": "Attachment is not stored.", "errors": None})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request, exc):
        errors: dict[str, list[str]] = {}
        for error in exc.errors():
            field = str(error["loc"][-1]) if error["loc"] else "non_field_errors"
            errors.setdefault(field, []).append(error["msg"])
        return JSONResponse(status_code=422, content={"detail": next(iter(errors.values()))[0], "errors": errors})

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "errors": None})