
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import verify_internal_key
from app.schemas.attachment import BatchRequest, ResolvedAttachment
from app.services.attachments import resolve_batch

router = APIRouter(prefix="/internal/attachments", tags=["internal"], dependencies=[Depends(verify_internal_key)])


@router.post("/batch", response_model=list[ResolvedAttachment])
async def batch(body: BatchRequest, db: AsyncSession = Depends(get_db)): # noqa B008
    return await resolve_batch(body.attachment_ids, db)

