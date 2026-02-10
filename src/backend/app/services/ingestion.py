"""
Email ingestion worker that combines email and storage services.
Production-grade implementation with state machine, idempotent operations, and Decimal precision.
"""

import logging
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime

from app.services.email import EmailService
from app.services.storage import StorageService
from app.services.ocr import OCRService
from app.services.parser import ReceiptParser, ParseContext
from app.utils.supabase import get_supabase_client

logger = logging.getLogger(__name__)


class IngestionService:
    """Service for ingesting emails and processing receipts."""

    def __init__(self):
        """Initialize ingestion service."""
        self.email_service = EmailService()
        self.storage_service = StorageService()
        self.ocr_service = OCRService()
        self.parser = ReceiptParser()
        self.supabase = get_supabase_client()

    def _decimal_to_str(self, value: Optional[Decimal]) -> Optional[str]:
        """
        Convert Decimal to string for database storage.

        Supabase-py JSON encoder cannot serialize Decimal objects directly.

        Args:
            value: Decimal value or None

        Returns:
            String representation or None
        """
        return str(value) if value is not None else None

    def _check_duplicate_by_hash(self, user_id: str, file_hash: str) -> bool:
        """
        Check if a receipt with this file hash already exists for the user.

        Args:
            user_id: User UUID
            file_hash: SHA-256 hash of file content

        Returns:
            True if duplicate exists, False otherwise
        """
        try:
            response = self.supabase.table('receipts').select('id').eq(
                'user_id', user_id
            ).eq('file_hash', file_hash).limit(1).execute()

            return len(response.data) > 0

        except Exception as e:
            logger.warning("Error checking duplicate receipt", extra={
                "user_id": user_id,
                "file_hash": file_hash,
                "error": str(e)
            })
            return False

    def _check_semantic_duplicate(
        self,
        user_id: str,
        vendor: Optional[str],
        amount: Optional[Decimal],
        date: Optional[str]
    ) -> bool:
        """
        Check if a semantically identical receipt exists (same vendor + amount + date).

        This catches cases where the same receipt is sent as multiple different files
        (e.g., "Invoice.pdf" and "Receipt.pdf" with identical content but different PDFs).

        Args:
            user_id: User UUID
            vendor: Vendor name
            amount: Receipt amount
            date: Receipt date (YYYY-MM-DD)

        Returns:
            True if semantic duplicate exists, False otherwise
        """
        # Need at least 2 of 3 fields to check for semantic duplicates
        fields_present = sum([
            vendor is not None,
            amount is not None,
            date is not None
        ])

        if fields_present < 2:
            return False  # Not enough data to determine semantic duplicate

        try:
            # Build query
            query = self.supabase.table('receipts').select('id').eq('user_id', user_id)

            if vendor is not None:
                query = query.eq('vendor', vendor)
            if amount is not None:
                query = query.eq('amount', str(amount))
            if date is not None:
                query = query.eq('date', date)

            response = query.limit(1).execute()

            if len(response.data) > 0:
                logger.info("Found semantic duplicate", extra={
                    "user_id": user_id,
                    "vendor": vendor,
                    "amount": str(amount) if amount else None,
                    "date": date
                })
                return True

            return False

        except Exception as e:
            logger.warning("Error checking semantic duplicate", extra={
                "user_id": user_id,
                "error": str(e)
            })
            return False

    def process_email(self, message_id: str, user_id: str) -> Dict:
        """
        Process a single email message with state machine and idempotent operations.

        State transitions: processing → success | no_receipts | failed

        Args:
            message_id: Gmail message ID
            user_id: Supabase user ID

        Returns:
            Dictionary with processing results
        """
        result = {
            'message_id': message_id,
            'success': False,
            'status': 'failed',
            'receipts_created': [],
            'receipts_skipped': 0,
            'errors': []
        }

        try:
            # Get full message
            message = self.email_service.get_message(message_id)
            if not message:
                error_msg = "Failed to fetch message from Gmail"
                result['errors'].append(error_msg)
                self.email_service.mark_message_processed(
                    message_id, user_id, 'failed',
                    failure_reason=error_msg
                )
                return result

            # Extract metadata
            metadata = self.email_service.extract_email_metadata(message)

            # Mark as processing (UPSERT with status='processing')
            self.email_service.mark_message_processing(
                message_id, user_id, metadata['received_at']
            )

            logger.info("Processing email", extra={
                "message_id": message_id,
                "user_id": user_id,
                "subject": metadata.get('subject', 'No subject')
            })

            # Extract attachments (recursive MIME tree walk)
            attachments = self.email_service.extract_attachments(message)

            # Process attachments first
            for idx, (filename, file_data, mime_type) in enumerate(attachments):
                try:
                    if not self._is_receipt_file(filename, mime_type):
                        logger.debug("Skipping non-receipt file", extra={
                            "filename": filename,
                            "mime_type": mime_type
                        })
                        continue

                    # Check file hash for idempotency BEFORE uploading
                    file_hash = self.storage_service.calculate_file_hash(file_data)

                    if self._check_duplicate_by_hash(user_id, file_hash):
                        logger.info("Skipping duplicate receipt", extra={
                            "file_hash": file_hash,
                            "filename": filename
                        })
                        result['receipts_skipped'] += 1
                        continue

                    # Process this source
                    receipt_id = self._process_source(
                        user_id=user_id,
                        message_id=message_id,
                        source_type='attachment',
                        attachment_index=idx,
                        filename=filename,
                        file_data=file_data,
                        mime_type=mime_type,
                        file_hash=file_hash,
                        email_metadata=metadata
                    )

                    if receipt_id:
                        result['receipts_created'].append(receipt_id)
                        logger.info("Processed attachment", extra={
                            "filename": filename,
                            "receipt_id": receipt_id
                        })
                    else:
                        result['errors'].append(f"Failed to process {filename}")

                except Exception as e:
                    error_msg = f"Error processing attachment {filename}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    result['errors'].append(error_msg)

            # Process email body if no attachments or no receipts from attachments
            if not attachments or len(result['receipts_created']) == 0:
                logger.debug("Checking email body for receipt data")

                try:
                    html_body, text_body = self.email_service.extract_email_body(message)

                    if html_body or text_body:
                        # Convert HTML to text
                        body_text = html_body if html_body else text_body
                        if html_body:
                            body_text = self.email_service.convert_html_to_text(html_body)

                        # Create synthetic "file" from body text
                        body_bytes = body_text.encode('utf-8')
                        file_hash = self.storage_service.calculate_file_hash(body_bytes)

                        # Check duplicate
                        if not self._check_duplicate_by_hash(user_id, file_hash):
                            # Process body as receipt (with pre-parsed text to skip OCR)
                            receipt_id = self._process_source(
                                user_id=user_id,
                                message_id=message_id,
                                source_type='body',
                                attachment_index=None,
                                filename=f"email_{message_id[:8]}.txt",
                                file_data=body_bytes,
                                mime_type='text/plain',
                                file_hash=file_hash,
                                pre_parsed_text=body_text,
                                email_metadata=metadata
                            )

                            if receipt_id:
                                result['receipts_created'].append(receipt_id)
                                logger.info("Processed email body as receipt", extra={
                                    "receipt_id": receipt_id
                                })
                        else:
                            logger.info("Skipping duplicate email body receipt")
                            result['receipts_skipped'] += 1

                except Exception as e:
                    error_msg = f"Error processing email body: {str(e)}"
                    logger.warning(error_msg, exc_info=True)
                    result['errors'].append(error_msg)

            # Determine final status
            receipt_count = len(result['receipts_created'])

            if receipt_count > 0:
                result['status'] = 'success'
                result['success'] = True
            elif result['receipts_skipped'] > 0:
                # Duplicates were skipped, but this is still successful processing
                result['status'] = 'success'
                result['success'] = True
            else:
                result['status'] = 'no_receipts'
                result['success'] = True  # Successfully processed, just no receipts found

            # Mark final status
            self.email_service.mark_message_processed(
                message_id, user_id, result['status'], receipt_count
            )

            logger.info("Email processing complete", extra={
                "message_id": message_id,
                "status": result['status'],
                "receipts_created": receipt_count,
                "receipts_skipped": result['receipts_skipped']
            })

            return result

        except Exception as e:
            error_msg = f"Error processing email: {str(e)}"
            logger.error(error_msg, extra={
                "message_id": message_id,
                "user_id": user_id
            }, exc_info=True)

            result['errors'].append(error_msg)
            result['status'] = 'failed'

            # Mark as failed
            self.email_service.mark_message_processed(
                message_id, user_id, 'failed',
                failure_reason=error_msg
            )

            return result

    def _process_source(
        self,
        user_id: str,
        message_id: str,
        source_type: str,
        attachment_index: Optional[int],
        filename: str,
        file_data: bytes,
        mime_type: str,
        file_hash: str,
        pre_parsed_text: Optional[str] = None,
        email_metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Process a single receipt source (attachment or body).

        Orchestration: upload → OCR (if needed) → parse → UPSERT receipt

        Args:
            user_id: User UUID
            message_id: Gmail message ID
            source_type: 'attachment' or 'body'
            attachment_index: Index in attachment list (None for body)
            filename: Original filename
            file_data: Raw file bytes
            mime_type: MIME type
            file_hash: Pre-computed SHA-256 hash
            pre_parsed_text: If provided, skip OCR and use this text

        Returns:
            Receipt ID if successful, None otherwise
        """
        file_path = None

        try:
            # Step 1: Upload to storage (idempotent, content-addressed)
            returned_hash, file_path = self.storage_service.upload_receipt(
                user_id=user_id,
                filename=filename,
                file_data=file_data,
                mime_type=mime_type
            )

            if not file_path:
                logger.error("Storage upload failed", extra={
                    "filename": filename,
                    "user_id": user_id
                })
                return None

            # Verify hash matches
            if returned_hash != file_hash:
                logger.error("File hash mismatch after upload", extra={
                    "expected": file_hash,
                    "got": returned_hash
                })
                return None

            # Step 2: Extract text (OCR or use pre-parsed)
            if pre_parsed_text:
                text = pre_parsed_text
                logger.debug("Using pre-parsed text (skipping OCR)")
            else:
                logger.debug("Running OCR", extra={"filename": filename})
                text = self.ocr_service.extract_and_normalize(
                    file_data=file_data,
                    mime_type=mime_type,
                    filename=filename
                )

            if not text:
                logger.warning("No text extracted", extra={"filename": filename})
                # Still create receipt record with empty fields
                parsed_data = {}
            else:
                # Step 3: Parse receipt data with context hints
                logger.debug("Parsing receipt data", extra={
                    "text_length": len(text)
                })

                # Create ParseContext from email metadata
                context = None
                if email_metadata:
                    # Extract sender domain and name from 'from' field
                    # Format: "Name <email@domain.com>" or just "email@domain.com"
                    sender_from = email_metadata.get('from', '')
                    sender_domain = None
                    sender_name = None

                    if sender_from:
                        # Extract email address
                        import re
                        email_match = re.search(r'<([^>]+)>|([^\s<>]+@[^\s<>]+)', sender_from)
                        if email_match:
                            email_addr = email_match.group(1) or email_match.group(2)
                            if '@' in email_addr:
                                sender_domain = email_addr.split('@')[1]

                        # Extract name (text before <email>)
                        name_match = re.match(r'([^<]+)\s*<', sender_from)
                        if name_match:
                            sender_name = name_match.group(1).strip().strip('"')
                        elif not email_match:
                            # No email format, treat whole thing as name
                            sender_name = sender_from.strip()

                    context = ParseContext(
                        sender_domain=sender_domain,
                        sender_name=sender_name,
                        subject=email_metadata.get('subject'),
                        user_locale=None,  # TODO: Get from user preferences
                        user_currency=None,  # TODO: Get from user preferences
                        billing_country=None  # TODO: Get from user profile
                    )

                parsed_data = self.parser.parse(text, context=context)

            # Step 3.5: Check for semantic duplicates (same vendor + amount + date)
            # This catches cases like "Invoice.pdf" and "Receipt.pdf" that are different files
            # but represent the same transaction
            if parsed_data:
                is_semantic_duplicate = self._check_semantic_duplicate(
                    user_id=user_id,
                    vendor=parsed_data.get('vendor'),
                    amount=parsed_data.get('amount'),
                    date=parsed_data.get('date')
                )

                if is_semantic_duplicate:
                    logger.info("Skipping semantic duplicate receipt", extra={
                        "vendor": parsed_data.get('vendor'),
                        "amount": str(parsed_data.get('amount')) if parsed_data.get('amount') else None,
                        "date": parsed_data.get('date'),
                        "filename": filename
                    })
                    return None  # Skip this receipt

            # Step 4: Create receipt record (UPSERT with UNIQUE constraint on file_hash)
            receipt_id = self._upsert_receipt_record(
                user_id=user_id,
                file_path=file_path,
                file_hash=file_hash,
                file_name=filename,
                mime_type=mime_type,
                source_message_id=message_id,
                source_type=source_type,
                attachment_index=attachment_index,
                parsed_data=parsed_data
            )

            if receipt_id:
                logger.debug("Receipt record created", extra={
                    "receipt_id": receipt_id,
                    "vendor": parsed_data.get('vendor'),
                    "amount": parsed_data.get('amount')
                })

            return receipt_id

        except Exception as e:
            logger.error("Error processing source", extra={
                "filename": filename,
                "source_type": source_type,
                "error": str(e)
            }, exc_info=True)

            # Orphan cleanup: if file was uploaded but DB insert failed, delete it
            if file_path:
                logger.warning("Cleaning up orphaned file", extra={"file_path": file_path})
                self.storage_service.delete_file(file_path)

            return None

    def _upsert_receipt_record(
        self,
        user_id: str,
        file_path: str,
        file_hash: str,
        file_name: str,
        mime_type: str,
        source_message_id: str,
        source_type: str,
        attachment_index: Optional[int],
        parsed_data: Dict
    ) -> Optional[str]:
        """
        Create or update receipt record in database (idempotent UPSERT).

        Uses UNIQUE constraint on (user_id, file_hash) for deduplication.

        Args:
            user_id: User UUID
            file_path: Storage path
            file_hash: SHA-256 hash
            file_name: Original filename
            mime_type: File MIME type
            source_message_id: Gmail message ID
            source_type: 'attachment' or 'body'
            attachment_index: Index in attachment list
            parsed_data: Parsed receipt data from parser

        Returns:
            Receipt ID if successful, None otherwise
        """
        try:
            # Smart currency defaulting with provenance tracking
            currency = parsed_data.get('currency')
            currency_source = 'parsed'

            if currency is None:
                # No currency detected by parser - use smart defaulting
                # TODO: Check user preferences (billing_country, preferred_currency)
                # For now, default to USD
                currency = 'USD'
                currency_source = 'defaulted_to_usd'

                # Record warning in debug metadata
                debug = parsed_data.get('debug', {})
                if 'warnings' not in debug:
                    debug['warnings'] = []
                debug['warnings'].append(f'Currency defaulted to {currency} (no strong evidence found)')
                parsed_data['debug'] = debug

                logger.debug("Currency defaulted", extra={
                    'source': currency_source,
                    'currency': currency
                })

            # Record currency source in debug metadata
            if parsed_data.get('debug'):
                parsed_data['debug']['currency_source'] = currency_source

            # Review flagging for low-confidence receipts
            confidence = parsed_data.get('confidence', 0.0)
            needs_review = False
            review_reason = None

            if confidence < 0.7:
                needs_review = True
                reasons = []

                # Determine specific reasons for review
                if not parsed_data.get('vendor'):
                    reasons.append('missing vendor')
                if not parsed_data.get('amount'):
                    reasons.append('missing amount')
                if not parsed_data.get('date'):
                    reasons.append('missing date')
                if currency_source == 'defaulted_to_usd':
                    reasons.append('defaulted currency')
                if confidence < 0.5:
                    reasons.append(f'low confidence ({confidence:.2f})')
                elif confidence < 0.7:
                    reasons.append(f'medium confidence ({confidence:.2f})')

                review_reason = '; '.join(reasons) if reasons else 'low confidence extraction'

                logger.info("Receipt flagged for review", extra={
                    'confidence': confidence,
                    'reason': review_reason,
                    'file_name': file_name
                })

            # Build receipt data (preserving Decimal precision)
            receipt_data = {
                'user_id': user_id,
                'file_path': file_path,
                'file_hash': file_hash,
                'file_name': file_name,
                'mime_type': mime_type,
                'source_message_id': source_message_id,
                'source_type': source_type,
                'attachment_index': attachment_index,
                'vendor': parsed_data.get('vendor'),
                'amount': self._decimal_to_str(parsed_data.get('amount')),
                'currency': currency,
                'date': parsed_data.get('date'),
                'tax': self._decimal_to_str(parsed_data.get('tax')),
                'needs_review': needs_review,
                'review_reason': review_reason,
                'ingestion_debug': parsed_data.get('debug')
            }

            # UPSERT: insert or do nothing if constraint violated (idempotent)
            response = self.supabase.table('receipts').upsert(
                receipt_data,
                on_conflict='user_id,file_hash',
                ignore_duplicates=True
            ).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]['id']

            # If ignore_duplicates=True and conflict occurred, response.data may be empty
            # This is expected and means the receipt already exists
            logger.debug("Receipt UPSERT returned no data (likely duplicate)", extra={
                "file_hash": file_hash
            })
            return None

        except Exception as e:
            logger.error("Error upserting receipt record", extra={
                "user_id": user_id,
                "file_hash": file_hash,
                "error": str(e)
            }, exc_info=True)
            return None

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
            'receipts_skipped': 0,
            'errors': []
        }

        try:
            # Get unprocessed messages (N+1 fix: single query)
            messages = self.email_service.get_unprocessed_messages(
                user_id=user_id,
                days_back=days_back,
                max_results=50
            )

            summary['messages_checked'] = len(messages)
            logger.info("Starting email sync", extra={
                "user_id": user_id,
                "unprocessed_count": len(messages)
            })

            # Process each message
            for msg in messages:
                result = self.process_email(msg['id'], user_id)

                if result['success']:
                    summary['messages_processed'] += 1
                    summary['receipts_created'] += len(result['receipts_created'])
                    summary['receipts_skipped'] += result['receipts_skipped']

                if result['errors']:
                    summary['errors'].extend(result['errors'])

            logger.info("Email sync complete", extra={
                "user_id": user_id,
                "messages_processed": summary['messages_processed'],
                "receipts_created": summary['receipts_created']
            })

            return summary

        except Exception as e:
            error_msg = f"Sync failed: {str(e)}"
            logger.error(error_msg, extra={"user_id": user_id}, exc_info=True)
            summary['errors'].append(error_msg)
            return summary
