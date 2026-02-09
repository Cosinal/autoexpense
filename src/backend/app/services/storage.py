"""
Storage service for uploading files to Supabase Storage.
Production-grade implementation with content-addressed paths and idempotent operations.
"""

import hashlib
import logging
import re
from typing import Tuple
from pathlib import Path

from app.config import settings
from app.utils.supabase import get_supabase_client

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing file uploads to Supabase Storage."""

    def __init__(self):
        """Initialize storage service."""
        self.supabase = get_supabase_client()
        self.bucket_name = settings.RECEIPT_BUCKET

    def calculate_file_hash(self, file_data: bytes) -> str:
        """
        Calculate SHA-256 hash of file data for deduplication.

        Args:
            file_data: Raw file bytes

        Returns:
            Hex string of SHA-256 hash
        """
        return hashlib.sha256(file_data).hexdigest()

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe storage.

        Args:
            filename: Original filename

        Returns:
            Safe filename (alphanumeric, hyphens, underscores, dots only)
        """
        # Extract just the filename (no path components)
        safe_name = Path(filename).name

        # Replace unsafe characters with underscores
        safe_name = re.sub(r'[^\w\-\.]', '_', safe_name)

        # Collapse multiple underscores
        safe_name = re.sub(r'_+', '_', safe_name)

        return safe_name

    def generate_file_path(
        self,
        user_id: str,
        file_hash: str,
        filename: str
    ) -> str:
        """
        Generate deterministic, content-addressed storage path.

        Format: {user_id}/{hash[:2]}/{hash}/{safe_filename}

        This ensures:
        - Same content = same path (idempotent uploads)
        - Hash prefix sharding reduces hot spots
        - User isolation

        Args:
            user_id: User's UUID
            file_hash: SHA-256 hash of file content
            filename: Original filename (will be sanitized)

        Returns:
            Storage path string
        """
        safe_filename = self._sanitize_filename(filename)

        # Content-addressed path with hash prefix sharding
        file_path = f"{user_id}/{file_hash[:2]}/{file_hash}/{safe_filename}"

        return file_path

    def upload(
        self,
        file_data: bytes,
        file_path: str,
        mime_type: str = "application/octet-stream"
    ) -> bool:
        """
        Upload a file to Supabase Storage with idempotent upsert.

        Args:
            file_data: Raw file bytes
            file_path: Destination path in storage bucket
            mime_type: MIME type of the file

        Returns:
            True if upload succeeded, False otherwise
        """
        try:
            # Upload with upsert option (idempotent)
            self.supabase.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=file_data,
                file_options={
                    "content-type": mime_type,
                    "upsert": "true"
                }
            )

            logger.debug("Uploaded file to storage", extra={
                "file_path": file_path,
                "size_bytes": len(file_data),
                "mime_type": mime_type
            })

            return True

        except Exception as e:
            logger.error("Error uploading file", extra={
                "file_path": file_path,
                "error": str(e)
            }, exc_info=True)
            return False

    def upload_receipt(
        self,
        user_id: str,
        filename: str,
        file_data: bytes,
        mime_type: str
    ) -> Tuple[str, str]:
        """
        Upload a receipt file with automatic deduplication via content-addressed paths.

        Args:
            user_id: User's UUID
            filename: Original filename
            file_data: Raw file bytes
            mime_type: MIME type

        Returns:
            Tuple of (file_hash, file_path)
            Returns (None, None) if upload fails
        """
        try:
            # Calculate hash for content-addressed storage
            file_hash = self.calculate_file_hash(file_data)

            # Generate deterministic path
            file_path = self.generate_file_path(user_id, file_hash, filename)

            # Upload (idempotent upsert)
            success = self.upload(file_data, file_path, mime_type)

            if not success:
                return (None, None)

            return (file_hash, file_path)

        except Exception as e:
            logger.error("Error uploading receipt", extra={
                "user_id": user_id,
                "filename": filename,
                "error": str(e)
            }, exc_info=True)
            return (None, None)

    def signed_url(self, file_path: str, expires_in: int = 3600) -> str:
        """
        Generate a signed URL for temporary access to a private file.

        Args:
            file_path: Path to file in storage
            expires_in: Expiration time in seconds (default 1 hour)

        Returns:
            Signed URL, or None if failed
        """
        try:
            response = self.supabase.storage.from_(self.bucket_name).create_signed_url(
                path=file_path,
                expires_in=expires_in
            )

            signed_url = response.get('signedURL')

            if not signed_url:
                logger.warning("Signed URL generation returned empty", extra={
                    "file_path": file_path
                })
                return None

            return signed_url

        except Exception as e:
            logger.error("Error creating signed URL", extra={
                "file_path": file_path,
                "error": str(e)
            }, exc_info=True)
            return None

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            file_path: Path to file in storage

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            self.supabase.storage.from_(self.bucket_name).remove([file_path])
            logger.debug("Deleted file from storage", extra={"file_path": file_path})
            return True

        except Exception as e:
            logger.error("Error deleting file", extra={
                "file_path": file_path,
                "error": str(e)
            }, exc_info=True)
            return False
