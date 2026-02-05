"""
Email ingestion worker that combines email and storage services.
Processes emails, extracts attachments, and uploads to storage.
"""

import uuid
from typing import List, Dict
from datetime import datetime

from app.services.email import EmailService
from app.services.storage import StorageService
from app.utils.supabase import get_supabase_client


class IngestionService:
    """Service for ingesting emails and processing receipts."""

    def __init__(self):
        """Initialize ingestion service."""
        self.email_service = EmailService()
        self.storage_service = StorageService()
        self.supabase = get_supabase_client()

    def process_email(self, message_id: str, user_id: str) -> Dict:
        """
        Process a single email message.

        Args:
            message_id: Gmail message ID
            user_id: Supabase user ID

        Returns:
            Dictionary with processing results
        """
        result = {
            'message_id': message_id,
            'success': False,
            'attachments_processed': 0,
            'receipts_created': [],
            'errors': []
        }

        try:
            # Get full message
            message = self.email_service.get_message(message_id)
            if not message:
                result['errors'].append("Failed to fetch message")
                return result

            # Extract metadata
            metadata = self.email_service.extract_email_metadata(message)
            print(f"Processing email: {metadata.get('subject', 'No subject')}")

            # Extract attachments
            attachments = self.email_service.extract_attachments(message)

            if not attachments:
                print(f"No attachments found in message {message_id}")
                # Still mark as processed to avoid re-checking
                self.email_service.mark_message_processed(message_id, user_id, 0)
                result['success'] = True
                return result

            # Process each attachment
            for filename, file_data, mime_type in attachments:
                try:
                    # Only process receipt-like files
                    if not self._is_receipt_file(filename, mime_type):
                        print(f"Skipping non-receipt file: {filename}")
                        continue

                    # Upload to storage
                    file_url, file_hash, file_path = self.storage_service.upload_receipt_file(
                        user_id=user_id,
                        filename=filename,
                        file_data=file_data,
                        mime_type=mime_type
                    )

                    if file_url:
                        # Create receipt record (without parsing yet - that's Phase 3)
                        receipt_id = self._create_receipt_record(
                            user_id=user_id,
                            file_url=file_url,
                            file_hash=file_hash,
                            file_name=filename,
                            mime_type=mime_type
                        )

                        if receipt_id:
                            result['receipts_created'].append(receipt_id)
                            result['attachments_processed'] += 1
                            print(f"✓ Processed: {filename}")
                        else:
                            result['errors'].append(f"Failed to create receipt record for {filename}")
                    else:
                        result['errors'].append(f"Failed to upload {filename}")

                except Exception as e:
                    result['errors'].append(f"Error processing {filename}: {str(e)}")

            # Mark message as processed
            self.email_service.mark_message_processed(
                message_id,
                user_id,
                result['attachments_processed']
            )

            result['success'] = True
            return result

        except Exception as e:
            result['errors'].append(f"Error processing email: {str(e)}")
            return result

    def _is_receipt_file(self, filename: str, mime_type: str) -> bool:
        """
        Check if file is likely a receipt.

        Args:
            filename: File name
            mime_type: MIME type

        Returns:
            True if file should be processed as a receipt
        """
        # Accept PDF and common image formats
        receipt_mime_types = [
            'application/pdf',
            'image/jpeg',
            'image/jpg',
            'image/png',
            'text/html',
            'application/octet-stream'  # Sometimes PDFs are misidentified
        ]

        receipt_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.html']

        # Check MIME type
        if mime_type in receipt_mime_types:
            return True

        # Check file extension
        filename_lower = filename.lower()
        if any(filename_lower.endswith(ext) for ext in receipt_extensions):
            return True

        return False

    def _create_receipt_record(
        self,
        user_id: str,
        file_url: str,
        file_hash: str,
        file_name: str,
        mime_type: str
    ) -> str:
        """
        Create a receipt record in the database.

        Args:
            user_id: User UUID
            file_url: URL to file in storage
            file_hash: SHA-256 hash of file
            file_name: Original filename
            mime_type: File MIME type

        Returns:
            Receipt ID if successful, None otherwise
        """
        try:
            receipt_data = {
                'user_id': user_id,
                'file_url': file_url,
                'file_hash': file_hash,
                'file_name': file_name,
                'mime_type': mime_type,
                # OCR/parsing fields will be populated in Phase 3
                'vendor': None,
                'amount': None,
                'currency': 'USD',  # Default
                'date': None,
                'tax': None
            }

            response = self.supabase.table('receipts').insert(receipt_data).execute()

            if response.data:
                return response.data[0]['id']
            return None

        except Exception as e:
            print(f"Error creating receipt record: {str(e)}")
            return None

    def sync_emails(self, user_id: str, days_back: int = 7) -> Dict:
        """
        Sync all unprocessed emails for a user.

        Args:
            user_id: Supabase user ID
            days_back: How many days back to check

        Returns:
            Summary of sync operation
        """
        summary = {
            'messages_checked': 0,
            'messages_processed': 0,
            'receipts_created': 0,
            'errors': []
        }

        try:
            # Get unprocessed messages
            messages = self.email_service.get_unprocessed_messages(
                user_id=user_id,
                days_back=days_back,
                max_results=50
            )

            summary['messages_checked'] = len(messages)
            print(f"Found {len(messages)} unprocessed messages")

            # Process each message
            for msg in messages:
                result = self.process_email(msg['id'], user_id)

                if result['success']:
                    summary['messages_processed'] += 1
                    summary['receipts_created'] += len(result['receipts_created'])

                if result['errors']:
                    summary['errors'].extend(result['errors'])

            return summary

        except Exception as e:
            summary['errors'].append(f"Sync failed: {str(e)}")
            return summary
