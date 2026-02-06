"""
Email ingestion worker that combines email and storage services.
Processes emails, extracts attachments, and uploads to storage.
"""

import uuid
from typing import List, Dict, Optional
from datetime import datetime

from app.services.email import EmailService
from app.services.storage import StorageService
from app.services.ocr import OCRService
from app.services.parser import ReceiptParser
from app.utils.supabase import get_supabase_client


class IngestionService:
    """Service for ingesting emails and processing receipts."""

    def __init__(self):
        """Initialize ingestion service."""
        self.email_service = EmailService()
        self.storage_service = StorageService()
        self.ocr_service = OCRService()
        self.parser = ReceiptParser()
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
                print(f"No attachments found in message {message_id}, checking email body...")

                # Try to process email body as receipt (Uber, Amazon, etc.)
                try:
                    html_body, text_body = self.email_service.extract_email_body(message)

                    if html_body or text_body:
                        # Convert HTML to text for processing
                        body_text = html_body if html_body else text_body
                        if html_body:
                            body_text = self.email_service.convert_html_to_text(html_body)

                        # Process the email body as a receipt
                        receipt_id = self._process_email_body_as_receipt(
                            user_id=user_id,
                            message_id=message_id,
                            body_text=body_text,
                            metadata=metadata
                        )

                        if receipt_id:
                            result['receipts_created'].append(receipt_id)
                            result['attachments_processed'] = 1  # Count body as 1 "receipt"
                            print(f"✓ Processed email body as receipt")
                        else:
                            print(f"Could not extract receipt data from email body")

                except Exception as e:
                    print(f"Error processing email body: {str(e)}")

                # Still mark as processed to avoid re-checking
                self.email_service.mark_message_processed(
                    message_id,
                    user_id,
                    result['attachments_processed']
                )
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
                        # Run OCR and parsing on the file
                        parsed_data = self._process_receipt_file(
                            file_data=file_data,
                            mime_type=mime_type,
                            filename=filename
                        )

                        # Create receipt record with parsed data
                        receipt_id = self._create_receipt_record(
                            user_id=user_id,
                            file_url=file_url,
                            file_hash=file_hash,
                            file_name=filename,
                            mime_type=mime_type,
                            parsed_data=parsed_data
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

    def _process_receipt_file(
        self,
        file_data: bytes,
        mime_type: str,
        filename: str
    ) -> Dict:
        """
        Process receipt file with OCR and parsing.

        Args:
            file_data: Raw file bytes
            mime_type: File MIME type
            filename: Filename

        Returns:
            Dictionary with parsed data
        """
        try:
            print(f"  → Running OCR on {filename}...")

            # Extract text using OCR
            text = self.ocr_service.extract_and_normalize(
                file_data=file_data,
                mime_type=mime_type,
                filename=filename
            )

            if not text:
                print("  ⚠ No text extracted from file")
                return {}

            print(f"  → Extracted {len(text)} characters of text")
            print(f"  → Parsing receipt data...")

            # Parse the text
            parsed_data = self.parser.parse(text)

            # Log what we found
            if parsed_data.get('vendor'):
                print(f"  → Vendor: {parsed_data['vendor']}")
            if parsed_data.get('amount'):
                print(f"  → Amount: {parsed_data['currency']} {parsed_data['amount']}")
            if parsed_data.get('date'):
                print(f"  → Date: {parsed_data['date']}")

            print(f"  → Confidence: {parsed_data.get('confidence', 0):.0%}")

            return parsed_data

        except Exception as e:
            print(f"  ✗ Error processing file: {str(e)}")
            return {}

    def _process_email_body_as_receipt(
        self,
        user_id: str,
        message_id: str,
        body_text: str,
        metadata: Dict
    ) -> Optional[str]:
        """
        Process email body as a receipt (for HTML receipts like Uber, Amazon, etc.).

        Args:
            user_id: User UUID
            message_id: Gmail message ID
            body_text: Email body text (converted from HTML if needed)
            metadata: Email metadata (subject, from, date, etc.)

        Returns:
            Receipt ID if successful, None otherwise
        """
        try:
            print(f"  → Parsing email body as receipt...")

            # Parse the email body text
            parsed_data = self.parser.parse(body_text)

            # If no useful data was extracted, skip
            if not parsed_data.get('amount') and not parsed_data.get('vendor'):
                print(f"  ⚠ No receipt data found in email body")
                return None

            # Try to extract vendor from email subject or sender if not found in body
            if not parsed_data.get('vendor'):
                # Try to get vendor from subject
                subject = metadata.get('subject', '')
                if subject:
                    # Extract first few words from subject as vendor
                    parsed_data['vendor'] = ' '.join(subject.split()[:5])
                else:
                    # Use sender email domain as vendor
                    from_email = metadata.get('from', '')
                    if '@' in from_email:
                        domain = from_email.split('@')[1].split('.')[0]
                        parsed_data['vendor'] = domain.capitalize()

            # Store email body as a "file" in storage (as text)
            # This allows users to reference the original email later
            import uuid
            receipt_id = str(uuid.uuid4())

            # Create a text "file" from the email body
            body_bytes = body_text.encode('utf-8')
            filename = f"email_{message_id[:8]}.txt"

            file_url, file_hash, file_path = self.storage_service.upload_receipt_file(
                user_id=user_id,
                filename=filename,
                file_data=body_bytes,
                mime_type='text/plain',
                receipt_id=receipt_id
            )

            if not file_url:
                print(f"  ⚠ Failed to store email body")
                return None

            # Log what we found
            if parsed_data.get('vendor'):
                print(f"  → Vendor: {parsed_data['vendor']}")
            if parsed_data.get('amount'):
                print(f"  → Amount: {parsed_data.get('currency', 'USD')} {parsed_data['amount']}")
            if parsed_data.get('date'):
                print(f"  → Date: {parsed_data['date']}")

            # Create receipt record
            receipt_id = self._create_receipt_record(
                user_id=user_id,
                file_url=file_url,
                file_hash=file_hash,
                file_name=filename,
                mime_type='text/plain',
                parsed_data=parsed_data
            )

            return receipt_id

        except Exception as e:
            print(f"  ✗ Error processing email body: {str(e)}")
            return None

    def _create_receipt_record(
        self,
        user_id: str,
        file_url: str,
        file_hash: str,
        file_name: str,
        mime_type: str,
        parsed_data: Optional[Dict] = None
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
            # Start with basic file info
            receipt_data = {
                'user_id': user_id,
                'file_url': file_url,
                'file_hash': file_hash,
                'file_name': file_name,
                'mime_type': mime_type,
            }

            # Add parsed data if available
            if parsed_data:
                receipt_data.update({
                    'vendor': parsed_data.get('vendor'),
                    'amount': float(parsed_data['amount']) if parsed_data.get('amount') else None,
                    'currency': parsed_data.get('currency', 'USD'),
                    'date': parsed_data.get('date'),
                    'tax': float(parsed_data['tax']) if parsed_data.get('tax') else None,
                })
            else:
                # No parsed data, use defaults
                receipt_data.update({
                    'vendor': None,
                    'amount': None,
                    'currency': 'USD',
                    'date': None,
                    'tax': None,
                })

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
