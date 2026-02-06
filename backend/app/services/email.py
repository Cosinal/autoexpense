"""
Email ingestion service for Gmail API.
Handles fetching emails, extracting attachments, and tracking processed messages.
"""

import base64
import email
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import html2text

from app.config import settings
from app.utils.supabase import get_supabase_client


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

        except Exception as e:
            print(f"Failed to initialize Gmail service: {str(e)}")
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
            return messages

        except HttpError as error:
            print(f"Gmail API error: {error}")
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
            print(f"Error fetching message {message_id}: {error}")
            return None

    def extract_attachments(self, message: Dict) -> List[Tuple[str, bytes, str]]:
        """
        Extract attachments from a Gmail message.

        Args:
            message: Full Gmail message object

        Returns:
            List of tuples: (filename, file_data, mime_type)
        """
        attachments = []

        if 'parts' not in message['payload']:
            return attachments

        for part in message['payload']['parts']:
            # Check if part is an attachment
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

                except HttpError as error:
                    print(f"Error downloading attachment {filename}: {error}")

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
                    print(f"Error decoding body part: {e}")

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
            print(f"Error converting HTML to text: {e}")
            return html_content

    def is_message_processed(self, message_id: str, user_id: str) -> bool:
        """
        Check if a message has already been processed.

        Args:
            message_id: Gmail message ID
            user_id: Supabase user ID

        Returns:
            True if message has been processed, False otherwise
        """
        try:
            supabase = get_supabase_client()
            response = supabase.table('processed_emails').select('id').eq(
                'provider_message_id', message_id
            ).eq('user_id', user_id).execute()

            return len(response.data) > 0

        except Exception as e:
            print(f"Error checking processed status: {e}")
            return False

    def mark_message_processed(
        self,
        message_id: str,
        user_id: str,
        receipt_count: int = 0
    ) -> bool:
        """
        Mark a message as processed in the database.

        Args:
            message_id: Gmail message ID
            user_id: Supabase user ID
            receipt_count: Number of receipts extracted from this email

        Returns:
            True if successful, False otherwise
        """
        try:
            supabase = get_supabase_client()
            supabase.table('processed_emails').insert({
                'user_id': user_id,
                'provider_message_id': message_id,
                'received_at': datetime.utcnow().isoformat(),
                'receipt_count': receipt_count
            }).execute()

            return True

        except Exception as e:
            print(f"Error marking message as processed: {e}")
            return False

    def extract_email_metadata(self, message: Dict) -> Dict:
        """
        Extract useful metadata from message headers.

        Args:
            message: Gmail message object

        Returns:
            Dictionary with subject, from, date, etc.
        """
        headers = message['payload']['headers']
        metadata = {
            'subject': '',
            'from': '',
            'date': '',
            'to': ''
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

        return metadata

    def get_unprocessed_messages(
        self,
        user_id: str,
        days_back: int = 7,
        max_results: int = 50
    ) -> List[Dict]:
        """
        Get messages that haven't been processed yet.
        Includes both emails with attachments AND emails without attachments
        (for processing email body as receipt).

        Args:
            user_id: Supabase user ID
            days_back: How many days back to search
            max_results: Maximum messages to retrieve

        Returns:
            List of unprocessed message objects
        """
        # Get messages from last N days (no longer filtering by attachment)
        # This allows processing of HTML receipt emails (Uber, Amazon, etc.)
        after_date = datetime.now() - timedelta(days=days_back)
        messages = self.list_messages(
            query="",  # Get all emails, not just those with attachments
            max_results=max_results,
            after_date=after_date
        )

        # Filter out already processed messages
        unprocessed = []
        for msg in messages:
            if not self.is_message_processed(msg['id'], user_id):
                unprocessed.append(msg)

        return unprocessed
