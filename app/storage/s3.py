"""s3.py — S3 upload and presigned URL service for video preview outputs."""

import boto3

from app.core.config import settings
from app.core.logger import StructuredLogger


logger = StructuredLogger.get_logger(__name__)


class S3Client:
    """Lazy-singleton S3 client for uploading video previews and generating presigned URLs."""

    _boto_client: boto3.client | None = None

    @classmethod
    def _client(cls) -> boto3.client:
        if cls._boto_client is None:
            cls._boto_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
                )
        return cls._boto_client

    def upload_preview(
            self,
            file_path: str,
            session_id: str,
            filename: str,
            expiry_seconds: int = 3600,
            ) -> str:
        """Upload a local file to S3 and return a presigned URL.

        Args:
            file_path:      Absolute path to the local file to upload.
            session_id:     Pipeline session ID used to namespace the S3 key.
            filename:       Destination filename within the session prefix.
            expiry_seconds: Presigned URL validity window (default 1 hour).

        Returns:
            A presigned HTTPS URL for downloading the uploaded file.
        """
        key = f"{settings.S3_KEY_PREFIX}/{session_id}/{filename}"
        self._client().upload_file(file_path, settings.S3_BUCKET_NAME, key)
        url: str = self._client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
            ExpiresIn=expiry_seconds,
            )
        logger.info(
            "s3_upload",
            extra={"key": key, "session_id": session_id, "expiry_seconds": expiry_seconds},
            )
        return url


s3_client = S3Client()
