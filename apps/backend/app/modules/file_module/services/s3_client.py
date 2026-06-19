from pathlib import Path
from typing import AsyncGenerator, BinaryIO
from urllib.parse import urlparse
from uuid import uuid4

import aiobotocore.session

from app.core.config import settings


class S3Client:
    """Async S3/MinIO client for upload, download, and delete operations."""

    @property
    def _scheme(self) -> str:
        return "https" if settings.minio_secure else "http"

    def _client(self):
        return aiobotocore.session.get_session().create_client(
            "s3",
            endpoint_url=f"{self._scheme}://{settings.minio_endpoint}",
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
        )

    def _key_from_link(self, link: str) -> str:
        """Extract the object key from a full bucket URL, path, or raw key."""
        if not link:
            return ""

        if "://" in link:
            path = urlparse(link).path
        else:
            parsed = urlparse(link)
            if parsed.scheme and not parsed.netloc and "/" in parsed.path:
                path = "/" + parsed.path
            else:
                path = parsed.path or parsed.netloc or link

        path = path.lstrip("/")

        # 1. Check if starts with bucket name
        bucket_prefix = f"{settings.minio_bucket}/"
        if path.startswith(bucket_prefix):
            return path[len(bucket_prefix) :]

        # 2. Check if bucket name is a segment in path
        segments = path.split("/")
        if settings.minio_bucket in segments:
            idx = segments.index(settings.minio_bucket)
            return "/".join(segments[idx + 1 :])

        return path

    async def create(self, file_obj: BinaryIO, filename: str, content_type: str) -> str:
        """Upload file to bucket. Returns public link stored in DB.

        Streams directly from the file-like object — no extra bytes copy in memory.
        ContentLength is required by S3; determined via seek without reading the data.
        """
        ext = Path(filename).suffix
        key = f"{uuid4().hex}{ext}"

        file_obj.seek(0, 2)
        size = file_obj.tell()
        file_obj.seek(0)

        async with self._client() as client:
            await client.put_object(
                Bucket=settings.minio_bucket,
                Key=key,
                Body=file_obj,
                ContentLength=size,
                ContentType=content_type,
            )

        return (
            f"{self._scheme}://{settings.minio_endpoint}/{settings.minio_bucket}/{key}"
        )

    async def read(self, link: str) -> bytes:
        """Download file from bucket by its stored link. Returns raw bytes."""
        key = self._key_from_link(link)

        async with self._client() as client:
            response = await client.get_object(
                Bucket=settings.minio_bucket,
                Key=key,
            )
            async with response["Body"] as stream:
                return await stream.read()

    async def stream(
        self, link: str, chunk_size: int = 1024 * 1024
    ) -> AsyncGenerator[bytes, None]:
        """Asynchronously stream chunks of a file from S3."""
        key = self._key_from_link(link)

        async with self._client() as client:
            response = await client.get_object(
                Bucket=settings.minio_bucket,
                Key=key,
            )
            body = response["Body"]
            async with body:
                while chunk := await body.read(chunk_size):
                    yield chunk

    async def delete(self, link: str) -> None:
        """Delete file from bucket by its stored link."""
        key = self._key_from_link(link)

        async with self._client() as client:
            await client.delete_object(
                Bucket=settings.minio_bucket,
                Key=key,
            )


s3_client = S3Client()
