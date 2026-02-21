"""
Cloud Storage service.
Async wrapper for Google Cloud Storage operations.
"""
import asyncio
from typing import Optional
from google.cloud.storage import Bucket
from ..config import storage_bucket


class StorageService:
    """Service for Cloud Storage operations."""

    def __init__(self, bucket: Bucket = storage_bucket):
        """
        Initialize Storage service.

        Args:
            bucket: Cloud Storage bucket instance
        """
        self.bucket = bucket

    async def upload_file(self, file_data: bytes, blob_path: str) -> str:
        """
        Upload file to Cloud Storage.

        Args:
            file_data: File bytes to upload
            blob_path: Destination path in bucket

        Returns:
            Public URL of uploaded file
        """
        def _upload():
            blob = self.bucket.blob(blob_path)
            blob.upload_from_string(file_data)
            return f"gs://{self.bucket.name}/{blob_path}"

        # Wrap sync operation in thread pool
        return await asyncio.to_thread(_upload)

    async def upload_text(self, text: str, blob_path: str) -> str:
        """
        Upload text content to Cloud Storage.

        Args:
            text: Text content to upload
            blob_path: Destination path in bucket

        Returns:
            Public URL of uploaded file
        """
        def _upload():
            blob = self.bucket.blob(blob_path)
            blob.upload_from_string(text, content_type='text/plain')
            return f"gs://{self.bucket.name}/{blob_path}"

        # Wrap sync operation in thread pool
        return await asyncio.to_thread(_upload)

    async def download_text(self, blob_path: str) -> str:
        """
        Download text content from Cloud Storage.

        Args:
            blob_path: Path to blob in bucket

        Returns:
            Text content as string

        Raises:
            Exception: If blob not found
        """
        def _download():
            blob = self.bucket.blob(blob_path)
            return blob.download_as_text()

        # Wrap sync operation in thread pool
        return await asyncio.to_thread(_download)

    async def download_bytes(self, blob_path: str) -> bytes:
        """
        Download file as bytes from Cloud Storage.

        Args:
            blob_path: Path to blob in bucket

        Returns:
            File content as bytes

        Raises:
            Exception: If blob not found
        """
        def _download():
            blob = self.bucket.blob(blob_path)
            return blob.download_as_bytes()

        # Wrap sync operation in thread pool
        return await asyncio.to_thread(_download)

    async def delete_file(self, blob_path: str) -> None:
        """
        Delete file from Cloud Storage.

        Args:
            blob_path: Path to blob in bucket
        """
        def _delete():
            blob = self.bucket.blob(blob_path)
            blob.delete()

        # Wrap sync operation in thread pool
        await asyncio.to_thread(_delete)

    async def file_exists(self, blob_path: str) -> bool:
        """
        Check if file exists in Cloud Storage.

        Args:
            blob_path: Path to blob in bucket

        Returns:
            True if file exists, False otherwise
        """
        def _exists():
            blob = self.bucket.blob(blob_path)
            return blob.exists()

        # Wrap sync operation in thread pool
        return await asyncio.to_thread(_exists)


# Global service instance
storage_service = StorageService()
