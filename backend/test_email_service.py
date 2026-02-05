"""
Test script for Gmail API connection.
Run this after setting up Gmail OAuth credentials.

Usage:
    python test_email_service.py
"""

from app.services.email import EmailService
from app.config import settings


def test_gmail_connection():
    """Test Gmail API connection and list recent messages."""

    print("=" * 60)
    print("Gmail API Connection Test")
    print("=" * 60)

    # Check configuration
    print("\n1. Checking configuration...")
    print(f"   Gmail Client ID: {'✓ Set' if settings.GMAIL_CLIENT_ID else '✗ Missing'}")
    print(f"   Gmail Client Secret: {'✓ Set' if settings.GMAIL_CLIENT_SECRET else '✗ Missing'}")
    print(f"   Gmail Refresh Token: {'✓ Set' if settings.GMAIL_REFRESH_TOKEN else '✗ Missing'}")
    print(f"   Intake Email: {settings.INTAKE_EMAIL or '✗ Not configured'}")

    if not all([settings.GMAIL_CLIENT_ID, settings.GMAIL_CLIENT_SECRET, settings.GMAIL_REFRESH_TOKEN]):
        print("\n✗ Gmail API not fully configured!")
        print("\nPlease follow these steps:")
        print("1. Run: python get_gmail_token.py")
        print("2. Update backend/.env with the credentials")
        return

    # Test connection
    print("\n2. Connecting to Gmail API...")
    try:
        email_service = EmailService()
        print("   ✓ Gmail service initialized")
    except Exception as e:
        print(f"   ✗ Failed to initialize: {str(e)}")
        return

    # List recent messages
    print("\n3. Fetching recent messages...")
    try:
        messages = email_service.list_messages(max_results=10)
        print(f"   ✓ Found {len(messages)} recent messages")

        if messages:
            print("\n   Recent messages:")
            for i, msg in enumerate(messages[:5], 1):
                full_msg = email_service.get_message(msg['id'])
                if full_msg:
                    metadata = email_service.extract_email_metadata(full_msg)
                    print(f"   {i}. {metadata.get('subject', 'No subject')[:50]}")
                    print(f"      From: {metadata.get('from', 'Unknown')[:50]}")

    except Exception as e:
        print(f"   ✗ Failed to fetch messages: {str(e)}")
        return

    # Test attachment detection
    print("\n4. Checking for messages with attachments...")
    try:
        messages_with_attachments = email_service.list_messages(
            query="has:attachment",
            max_results=5
        )
        print(f"   ✓ Found {len(messages_with_attachments)} messages with attachments")

        if messages_with_attachments:
            print("\n   Messages with attachments:")
            for i, msg in enumerate(messages_with_attachments, 1):
                full_msg = email_service.get_message(msg['id'])
                if full_msg:
                    metadata = email_service.extract_email_metadata(full_msg)
                    attachments = email_service.extract_attachments(full_msg)
                    print(f"   {i}. {metadata.get('subject', 'No subject')[:50]}")
                    print(f"      Attachments: {len(attachments)}")
                    for att_name, _, att_type in attachments:
                        print(f"      - {att_name} ({att_type})")

    except Exception as e:
        print(f"   ✗ Failed to check attachments: {str(e)}")
        return

    # Success
    print("\n" + "=" * 60)
    print("✓ Gmail API connection successful!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Forward a receipt email to your Gmail account")
    print("2. Test the ingestion service")
    print("3. Check that files are uploaded to Supabase storage")


if __name__ == "__main__":
    test_gmail_connection()
