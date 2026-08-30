from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import cast

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError
from types_aiobotocore_s3 import S3Client

from app.config import settings

session = aioboto3.Session()
_s3_config = Config(s3={"addressing_style": "path"}, signature_version="s3v4")

_s3: S3Client | None = None
_public_s3: S3Client | None = None


@asynccontextmanager
async def _client(endpoint: str) -> AsyncIterator[S3Client]:
    async with session.client( # type: ignore[call-overload]
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name="us-east-1",
        config=_s3_config,
    ) as client:
        yield cast(S3Client, client)

async def init_storage(stack: AsyncExitStack) -> None:
    global _s3, _public_s3
    _s3 = await stack.enter_async_context(_client(settings.S3_ENDPOINT_URL))
    _public_s3 = await stack.enter_async_context(_client(settings.S3_PUBLIC_ENDPOINT_URL))


def get_s3():
    if _s3 is None:
        raise RuntimeError("Storage not initialized: init_storage() must run in lifespan.")
    return _s3

def get_public_s3():
    if _public_s3 is None:
        raise RuntimeError("Storage not initialized: init_storage() must run in lifespan.")
    return _public_s3

async def ensure_bucket():
    s3 = get_s3() 
    try:
        await s3.head_bucket(Bucket=settings.S3_BUCKET)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") not in ("404", "NoSuchBucket"):
            raise
        await s3.create_bucket(Bucket=settings.S3_BUCKET)

async def presign_put(key: str) -> str:
    return await get_public_s3().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=settings.PRESIGNED_URL_TTL_SECONDS,
    )

async def presign_get(key: str, filename: str, content_type: str) -> str:
    disposition = "inline" if content_type.startswith("image/") else "attachment"
    safe_name = filename.replace('"', "").replace("\n", "").replace("\r", "")
    params = {
        "Bucket": settings.S3_BUCKET,
        "Key": key,
        "ResponseContentType": content_type,
        "ResponseContentDisposition": f'{disposition}; filename="{safe_name}"',
    }
    
    return await get_public_s3().generate_presigned_url(
        "get_object",
        Params=params,
        ExpiresIn=settings.PRESIGNED_URL_TTL_SECONDS,
    )

async def stat_object(key: str) -> int | None:
    try:
        head = await get_s3().head_object(Bucket=settings.S3_BUCKET, Key=key)
        return head["ContentLength"]
    except ClientError:
        return None

async def download_object(key: str) -> bytes:
    obj = await get_s3().get_object(Bucket=settings.S3_BUCKET, Key=key)
    async with obj["Body"] as stream:
        return await stream.read()

async def delete_object(key: str) -> None:
    await get_s3().delete_object(Bucket=settings.S3_BUCKET, Key=key)