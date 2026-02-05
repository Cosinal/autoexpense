"""
Test script for email sync without needing a real user ID.
This creates a temporary test user and syncs their emails.

Usage:
    python test_sync.py
"""

import uuid
from app.services.ingestion import IngestionService
from app.config import settings


def test_sync():
    """Test email sync with a temporary user."""

    print("=" * 60)
    print("Email Sync Test")
    print("=" * 60)

    # Check Gmail configuration first
    print("\n1. Checking Gmail configuration...")
    if not all([settings.GMAIL_CLIENT_ID, settings.GMAIL_CLIENT_SECRET, settings.GMAIL_REFRESH_TOKEN]):
        print("\n✗ Gmail API not configured!")
        print("\nPlease complete these steps first:")
        print("1. Follow GMAIL_API_SETUP.md to enable Gmail API")
        print("2. Run: python get_gmail_token.py")
        print("3. Update backend/.env with Gmail credentials")
        return

    print("   ✓ Gmail credentials configured")
    print(f"   Intake email: {settings.INTAKE_EMAIL}")

    # For testing, we'll use a dummy user ID
    # In production, this would come from Supabase Auth
    test_user_id = "00000000-0000-0000-0000-000000000000"
    print(f"\n2. Using test user ID: {test_user_id}")
    print("   Note: This is for testing only. Real users will have proper auth.")

    # Initialize ingestion service
    print("\n3. Initializing ingestion service...")
    try:
        ingestion = IngestionService()
        print("   ✓ Services initialized")
    except Exception as e:
        print(f"   ✗ Failed to initialize: {str(e)}")
        print("\n   Troubleshooting:")
        print("   - Check that Gmail credentials are correct in .env")
        print("   - Make sure you ran get_gmail_token.py successfully")
        return

    # Sync emails
    print("\n4. Syncing emails from Gmail...")
    print("   Looking for messages with attachments from last 7 days...")

    try:
        summary = ingestion.sync_emails(
            user_id=test_user_id,
            days_back=7
        )

        print("\n" + "=" * 60)
        print("Sync Results")
        print("=" * 60)
        print(f"Messages checked: {summary['messages_checked']}")
        print(f"Messages processed: {summary['messages_processed']}")
        print(f"Receipts created: {summary['receipts_created']}")

        if summary['errors']:
            print(f"\nErrors ({len(summary['errors'])}):")
            for error in summary['errors']:
                print(f"  - {error}")
        else:
            print("\n✓ No errors")

        if summary['receipts_created'] > 0:
            print("\n✓ Success! Check Supabase:")
            print("  1. Go to Storage → receipts bucket")
            print(f"  2. Look for folder: {test_user_id}/")
            print("  3. Go to Table Editor → receipts table")
            print("  4. You should see new receipt records")
        else:
            print("\nNo receipts were created.")
            print("\nTips:")
            print("- Forward an email with a PDF/image attachment to your Gmail")
            print("- Make sure the email has an attachment")
            print("- Wait a moment and run this script again")

    except Exception as e:
        print(f"\n✗ Sync failed: {str(e)}")
        print("\nTroubleshooting:")
        print("- Check Gmail API credentials")
        print("- Verify Supabase connection")
        print("- Check backend logs for details")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_sync()
