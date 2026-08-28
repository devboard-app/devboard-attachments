from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exception_handlers import register_exception_handlers
from app.storage import ensure_bucket


@asynccontextmanager
async def lifespan(app:FastAPI):
    await ensure_bucket()
    yield

app = FastAPI(
    title="Devboard Attachments Service", lifespan=lifespan
)

register_exception_handlers(app)


@app.get("/health")
async def health():
    return{"status": "ok"}

@app.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)): # noqa: B008
    try:
        await db.execute(text("SELECT 1"))
        return JSONResponse(status_code=200, content={"status":"ok"})
    except Exception: # noqa: BLE001
        return JSONResponse(status_code=500, content={"status":"error", "details":"db unavailable"})