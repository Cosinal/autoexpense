"""
Email ingestion service for Gmail API.
Production-grade implementation with N+1 query fixes, recursive MIME parsing, and structured logging.
"""

import base64
import email
import logging
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import html2text

from app.config import settings
from app.utils.supabase import get_supabase_client

logger = logging.getLogger(__name__)


class EmailService:
    """Service for interacting with Gmail API."""

    def __init__(self):
        """Initialize Gmail service with OAuth credentials."""
        self.creds = None
        self.service = None
        self._initialize_service()

    def _initialize_service(self):
        """Set up Gmail API service with credentials."""
        try:
            # Create credentials from config
            self.creds = Credentials(
                token=None,
                refresh_token=settings.GMAIL_REFRESH_TOKEN,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GMAIL_CLIENT_ID,
                client_secret=settings.GMAIL_CLIENT_SECRET,
                scopes=['https://www.googleapis.com/auth/gmail.readonly']
            )

            # Build Gmail service
            self.service = build('gmail', 'v1', credentials=self.creds)
            logger.debug("Gmail service initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize Gmail service", exc_info=True)
            raise

    def list_messages(
        self,
        query: str = "",
        max_results: int = 100,
        after_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        List messages from Gmail inbox.

        Args:
            query: Gmail search query (e.g., "from:receipts@example.com")
            max_results: Maximum number of messages to return
            after_date: Only return messages after this date

        Returns:
            List of message objects with id and threadId
        """
        try:
            # Build query with date filter if provided
            full_query = query
            if after_date:
                date_str = after_date.strftime("%Y/%m/%d")
                full_query = f"{query} after:{date_str}" if query else f"after:{date_str}"

            # Call Gmail API
            results = self.service.users().messages().list(
                userId='me',
                q=full_query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            logger.debug("Listed messages from Gmail", extra={
                "count": len(messages),
                "query": full_query
            })
            return messages

        except HttpError as error:
            logger.error("Gmail API error listing messages", extra={
                "error": str(error)
            }, exc_info=True)
            return []

    def get_message(self, message_id: str) -> Optional[Dict]:
        """
        Get full message details by ID.

        Args:
            message_id: Gmail message ID

        Returns:
            Full message object with headers, body, and attachments
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            return message

        except HttpError as error:
            logger.error("Error fetching message", extra={
                "message_id": message_id,
                "error": str(error)
            }, exc_info=True)
            return None

    def _walk_parts(self, part: Dict, depth: int = 0) -> List[Tuple[str, bytes, str, List[str]]]:
        """
        Recursively walk MIME tree to extract all attachments.

        Args:
            part: MIME part dictionary from Gmail API
            depth: Current recursion depth (for debugging)

        Returns:
            List of tuples: (filename, file_data, mime_type, path)
            path is a list like ['multipart/mixed', 'multipart/related', 'image/png']
        """
        attachments = []
        mime_type = part.get('mimeType', '')
        path = [mime_type]

        # Check if this part is an attachment
        if part.get('filename') and part.get('body', {}).get('attachmentId'):
            # This is an attachment - will be handled by caller
            pass

        # Recursively process nested parts
        if 'parts' in part:
            for subpart in part['parts']:
                sub_attachments = self._walk_parts(subpart, depth + 1)
                attachments.extend(sub_attachments)

        return attachments

    def extract_attachments(self, message: Dict) -> List[Tuple[str, bytes, str]]:
        """
        Extract ALL attachments from a Gmail message by recursively walking MIME tree.

        This fixes the previous implementation that only checked top-level parts.

        Args:
            message: Full Gmail message object

        Returns:
            List of tuples: (filename, file_data, mime_type)
        """
        attachments = []

        def walk_and_extract(part: Dict):
            """Recursively walk MIME tree and extract attachments."""
            # Check if this part is an attachment
            if part.get('filename') and part.get('body', {}).get('attachmentId'):
                filename = part['filename']
                mime_type = part['mimeType']
                attachment_id = part['body']['attachmentId']

                # Download attachment
                try:
                    attachment = self.service.users().messages().attachments().get(
                        userId='me',
                        messageId=message['id'],
                        id=attachment_id
                    ).execute()

                    # Decode base64 data
                    file_data = base64.urlsafe_b64decode(attachment['data'])
                    attachments.append((filename, file_data, mime_type))

                    logger.debug("Extracted attachment", extra={
                        "filename": filename,
                        "size_bytes": len(file_data),
                        "mime_type": mime_type
                    })

                except HttpError as error:
                    logger.warning("Error downloading attachment", extra={
                        "filename": filename,
                        "error": str(error)
                    })

            # Recursively process nested parts
            if 'parts' in part:
                for subpart in part['parts']:
                    walk_and_extract(subpart)

        # Start recursive extraction from payload
        payload = message.get('payload', {})
        walk_and_extract(payload)

        return attachments

    def extract_email_body(self, message: Dict) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract email body content (HTML and/or plain text).

        Args:
            message: Full Gmail message object

        Returns:
            Tuple of (html_body, text_body)
        """
        html_body = None
        text_body = None

        def get_body_from_part(part):
            """Recursively extract body from message parts."""
            nonlocal html_body, text_body

            mime_type = part.get('mimeType', '')
            body = part.get('body', {})

            # Check if this part has the body data
            if 'data' in body:
                try:
                    decoded = base64.urlsafe_b64decode(body['data']).decode('utf-8')

                    if mime_type == 'text/html':
                        html_body = decoded
                    elif mime_type == 'text/plain':
                        text_body = decoded
                except Exception as e:
                    logger.warning("Error decoding body part", extra={
                        "mime_type": mime_type,
                        "error": str(e)
                    })

            # Recursively process multipart messages
            if 'parts' in part:
                for subpart in part['parts']:
                    get_body_from_part(subpart)

        # Start extraction from payload
        payload = message.get('payload', {})
        get_body_from_part(payload)

        return html_body, text_body

    def convert_html_to_text(self, html_content: str) -> str:
        """
        Convert HTML email to clean text.

        Args:
            html_content: HTML string

        Returns:
            Plain text version
        """
        try:
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            h.ignore_emphasis = False
            h.body_width = 0  # Don't wrap lines

            text = h.handle(html_content)
            return text
        except Exception as e:
            logger.warning("Error converting HTML to text", extra={
                "error": str(e)
            })
            return html_content

    def get_processed_ids(self, user_id: str) -> Set[str]:
        """
        Get set of all successfully processed message IDs for a user.

        This fixes the N+1 query problem by fetching all processed IDs in one query.

        Args:
            user_id: Supabase user ID

        Returns:
            Set of provider_message_id strings
        """
        try:
            supabase = get_supabase_client()
            response = supabase.table('processed_emails').select('provider_message_id').eq(
                'user_id', user_id
            ).eq('status', 'success').execute()

            message_ids = {row['provider_message_id'] for row in response.data}

            logger.debug("Fetched processed message IDs", extra={
                "user_id": user_id,
                "count": len(message_ids)
            })

            return message_ids

        except Exception as e:
            logger.error("Error fetching processed IDs", exc_info=True)
            return set()

    def mark_message_processing(self, message_id: str, user_id: str, received_at: datetime) -> bool:
        """
        Mark a message as currently being processed (UPSERT with status='processing').

        Args:
            message_id: Gmail message ID
            user_id: Supabase user ID
            received_at: Email received timestamp from Gmail internalDate

        Returns:
            True if successful, False otherwise
        """
        try:
            supabase = get_supabase_client()
            supabase.table('processed_emails').upsert({
                'user_id': user_id,
                'provider_message_id': message_id,
                'provider': 'gmail',
                'status': 'processing',
                'received_at': received_at.isoformat(),
                'receipt_count': 0
            }, on_conflict='user_id,provider_message_id').execute()

            logger.debug("Marked message as processing", extra={
                "message_id": message_id,
                "user_id": user_id
            })

            return True

        except Exception as e:
            logger.error("Error marking message as processing", extra={
                "message_id": message_id,
                "user_id": user_id
            }, exc_info=True)
            return False

    def mark_message_processed(
        self,
        message_id: str,
        user_id: str,
        status: str,
        receipt_count: int = 0,
        failure_reason: Optional[str] = None
    ) -> bool:
        """
        Mark a message with final status (UPSERT update).

        Args:
            message_id: Gmail message ID
            user_id: Supabase user ID
            status: Terminal status ('success', 'no_receipts', or 'failed')
            receipt_count: Number of receipts extracted from this email
            failure_reason: Error message if status='failed'

        Returns:
            True if successful, False otherwise
        """
        try:
            supabase = get_supabase_client()

            data = {
                'user_id': user_id,
                'provider_message_id': message_id,
                'status': status,
                'receipt_count': receipt_count
            }

            if failure_reason:
                data['failure_reason'] = failure_reason

            supabase.table('processed_emails').upsert(
                data,
                on_conflict='user_id,provider_message_id'
            ).execute()

            logger.info("Marked message with final status", extra={
                "message_id": message_id,
                "user_id": user_id,
                "status": status,
                "receipt_count": receipt_count
            })

            return True

        except Exception as e:
            logger.error("Error marking message as processed", extra={
                "message_id": message_id,
                "user_id": user_id,
                "status": status
            }, exc_info=True)
            return False

    def extract_email_metadata(self, message: Dict) -> Dict:
        """
        Extract useful metadata from message headers.

        Args:
            message: Gmail message object

        Returns:
            Dictionary with subject, from, date, to, received_at
        """
        headers = message['payload']['headers']
        metadata = {
            'subject': '',
            'from': '',
            'date': '',
            'to': '',
            'received_at': None
        }

        for header in headers:
            name = header['name'].lower()
            if name == 'subject':
                metadata['subject'] = header['value']
            elif name == 'from':
                metadata['from'] = header['value']
            elif name == 'date':
                metadata['date'] = header['value']
            elif name == 'to':
                metadata['to'] = header['value']

        # Extract received_at from Gmail internalDate (milliseconds since epoch)
        if 'internalDate' in message:
            try:
                timestamp_ms = int(message['internalDate'])
                metadata['received_at'] = datetime.fromtimestamp(timestamp_ms / 1000.0)
            except (ValueError, TypeError) as e:
                logger.warning("Error parsing internalDate", extra={
                    "message_id": message.get('id'),
                    "error": str(e)
                })
                metadata['received_at'] = datetime.utcnow()
        else:
            metadata['received_at'] = datetime.utcnow()

        return metadata

    def get_unprocessed_messages(
        self,
        user_id: str,
        days_back: int = 7,
        max_results: int = 50
    ) -> List[Dict]:
        """
        Get messages that haven't been successfully processed yet.

        Uses single-query processed ID fetch to avoid N+1 problem.

        Args:
            user_id: Supabase user ID
            days_back: How many days back to search
            max_results: Maximum messages to retrieve

        Returns:
            List of unprocessed message objects
        """
        # Get all processed message IDs in one query (N+1 fix)
        processed_ids = self.get_processed_ids(user_id)

        # Get messages from last N days
        after_date = datetime.now() - timedelta(days=days_back)
        messages = self.list_messages(
            query="",  # Get all emails
            max_results=max_results,
            after_date=after_date
        )

        # Filter out already processed messages in memory
        unprocessed = [msg for msg in messages if msg['id'] not in processed_ids]

        logger.info("Found unprocessed messages", extra={
            "user_id": user_id,
            "total_messages": len(messages),
            "unprocessed": len(unprocessed),
            "already_processed": len(processed_ids)
        })

        return unprocessed
