"""
Storage service for uploading files to Supabase Storage.
"""

import hashlib
import uuid
from typing import Optional, Tuple
from pathlib import Path

from app.config import settings
from app.utils.supabase import get_supabase_client


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

    def generate_file_path(
        self,
        user_id: str,
        filename: str,
        receipt_id: Optional[str] = None
    ) -> str:
        """
        Generate storage path for a file.

        Args:
            user_id: User's UUID
            filename: Original filename
            receipt_id: Optional receipt UUID

        Returns:
            Storage path: {user_id}/{receipt_id}_{filename}
        """
        if receipt_id is None:
            receipt_id = str(uuid.uuid4())

        # Sanitize filename
        safe_filename = Path(filename).name

        # Create path: user_id/receipt_id_filename
        file_path = f"{user_id}/{receipt_id}_{safe_filename}"

        return file_path

    def upload_file(
        self,
        file_data: bytes,
        file_path: str,
        mime_type: str = "application/octet-stream"
    ) -> Optional[str]:
        """
        Upload a file to Supabase Storage.

        Args:
            file_data: Raw file bytes
            file_path: Destination path in storage bucket
            mime_type: MIME type of the file

        Returns:
            Public URL of uploaded file, or None if upload failed
        """
        try:
            # Upload to Supabase Storage
            response = self.supabase.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=file_data,
                file_options={"content-type": mime_type}
            )

            # Get public URL (even though bucket is private, we store the path)
            file_url = self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)

            return file_url

        except Exception as e:
            print(f"Error uploading file {file_path}: {str(e)}")
            return None

    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file already exists in storage.

        Args:
            file_path: Path to check

        Returns:
            True if file exists, False otherwise
        """
        try:
            # Try to get file metadata
            files = self.supabase.storage.from_(self.bucket_name).list(
                path=str(Path(file_path).parent)
            )

            filename = Path(file_path).name
            return any(f['name'] == filename for f in files)

        except Exception as e:
            print(f"Error checking file existence: {str(e)}")
            return False

    def upload_receipt_file(
        self,
        user_id: str,
        filename: str,
        file_data: bytes,
        mime_type: str,
        receipt_id: Optional[str] = None
    ) -> Tuple[Optional[str], str, str]:
        """
        Upload a receipt file with automatic deduplication.

        Args:
            user_id: User's UUID
            filename: Original filename
            file_data: Raw file bytes
            mime_type: MIME type
            receipt_id: Optional receipt UUID

        Returns:
            Tuple of (file_url, file_hash, file_path)
        """
        # Calculate file hash for deduplication
        file_hash = self.calculate_file_hash(file_data)

        # Check if file with same hash already exists in DB
        # (This would require querying the receipts table)
        # For now, we'll upload anyway and handle deduplication in the parser

        # Generate file path
        if receipt_id is None:
            receipt_id = str(uuid.uuid4())

        file_path = self.generate_file_path(user_id, filename, receipt_id)

        # Upload file
        file_url = self.upload_file(file_data, file_path, mime_type)

        return (file_url, file_hash, file_path)

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
            return True

        except Exception as e:
            print(f"Error deleting file {file_path}: {str(e)}")
            return False

    def get_file_url(self, file_path: str) -> str:
        """
        Get the URL for a file in storage.

        Args:
            file_path: Path to file

        Returns:
            URL to access the file
        """
        return self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)

    def create_signed_url(self, file_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Create a signed URL for temporary access to a private file.

        Args:
            file_path: Path to file
            expires_in: Expiration time in seconds (default 1 hour)

        Returns:
            Signed URL or None if failed
        """
        try:
            response = self.supabase.storage.from_(self.bucket_name).create_signed_url(
                path=file_path,
                expires_in=expires_in
            )
            return response.get('signedURL')

        except Exception as e:
            print(f"Error creating signed URL: {str(e)}")
            return None
