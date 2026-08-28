from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser
from app.schemas.attachment import UploadRequest, UploadResponse
from app.services.attachments import request_upload as request_upload_service

router = APIRouter(prefix="/attachments", tags=["attachments"])

@router.post("/request-upload", response_model=UploadResponse)
async def request_upload(body: UploadRequest, owner_id: CurrentUser, db: AsyncSession = Depends(get_db)):  # noqa: B008
    return await request_upload_service(body, owner_id, db)
