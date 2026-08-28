from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError
from types_aiobotocore_s3 import S3Client

from app.config import settings

session = aioboto3.Session()
_s3_config = Config(s3={"addressing_style": "path"}, signature_version="s3v4")

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


def get_s3():
    return _client(settings.S3_ENDPOINT_URL)

def get_public_s3():
    return _client(settings.S3_PUBLIC_ENDPOINT_URL)

async def ensure_bucket():
    s3: S3Client
    async with get_s3() as s3: 
        try:
            await s3.head_bucket(Bucket=settings.S3_BUCKET)
        except Exception:  # noqa: BLE001
            await s3.create_bucket(Bucket=settings.S3_BUCKET)

async def presign_put(key: str) -> str:
    async with get_public_s3() as s3:
        return await s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key},
            ExpiresIn=settings.PRESIGNED_URL_TTL_SECONDS,
        )


async def stat_object(key: str) -> int | None:
    async with get_s3() as s3:
        try:
            head = await s3.head_object(Bucket=settings.S3_BUCKET, Key=key)
            return head["ContentLength"]
        except ClientError:
            return None

async def download_object(key: str) -> bytes:
    async with get_s3() as s3:
        obj = await s3.get_object(Bucket=settings.S3_BUCKET, Key=key)
        async with obj["Body"] as stream:
            return await stream.read()

async def delete_object(key: str) -> None:
    async with get_s3() as s3:
        await s3.delete_object(Bucket=settings.S3_BUCKET, Key=key)