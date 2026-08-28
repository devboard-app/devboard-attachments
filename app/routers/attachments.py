import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser
from app.schemas.attachment import (
    AttachmentResponse,
    ResolveResponse,
    UploadRequest,
    UploadResponse,
)
from app.services.attachments import confirm_upload as confirm_upload_service
from app.services.attachments import delete_by_id as delete_by_id_service
from app.services.attachments import request_upload as request_upload_service
from app.services.attachments import resolve_url as resolve_url_service

router = APIRouter(prefix="/attachments", tags=["attachments"])

@router.post("/request-upload", response_model=UploadResponse)
async def request_upload(body: UploadRequest, owner_id: CurrentUser, db: AsyncSession = Depends(get_db)):  # noqa: B008
    return await request_upload_service(body, owner_id, db)

@router.post("/{attachment_id}/confirm", response_model=AttachmentResponse)
async def confirm_upload(attachment_id: uuid.UUID, owner_id: CurrentUser, db: AsyncSession = Depends(get_db)):  # noqa: B008
    return await confirm_upload_service(attachment_id, owner_id, db)

@router.get("/{attachment_id}/url", response_model=ResolveResponse)
async def resolve(attachment_id: uuid.UUID, owner_id: CurrentUser, db: AsyncSession = Depends(get_db)): # noqa: B008
    url = await resolve_url_service(attachment_id, db)
    return ResolveResponse(url=url)

@router.get("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(attachment_id: uuid.UUID, owner_id: CurrentUser, db: AsyncSession = Depends(get_db)): #noqa: B008
    await delete_by_id_service(attachment_id, owner_id, db)
    