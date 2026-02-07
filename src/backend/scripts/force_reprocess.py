#!/usr/bin/env python3
"""
Force reprocess all emails from the last 30 days, ignoring processed status.
"""

import sys
sys.path.insert(0, '/Users/jordanshaw/Desktop/expense-reporting/src/backend')

from app.services.email import EmailService
from app.services.ingestion import IngestionService
from datetime import datetime, timedelta

# User ID from tests
USER_ID = "407b70ad-8e64-43a1-81b4-da0977066e6d"

def force_reprocess(user_id: str, days_back: int = 30):
    """Force reprocess all emails, ignoring processed status."""
    print(f"\n{'='*60}")
    print("Force Reprocess Emails")
    print(f"{'='*60}")
    print(f"User ID: {user_id}")
    print(f"Days back: {days_back}\n")

    try:
        # Initialize services
        email_service = EmailService()
        ingestion = IngestionService()

        # Get ALL messages from the last N days (not just unprocessed)
        after_date = datetime.now() - timedelta(days=days_back)
        print(f"Fetching all messages after {after_date.strftime('%Y-%m-%d')}...")

        messages = email_service.list_messages(
            query="",
            max_results=100,
            after_date=after_date
        )

        print(f"Found {len(messages)} total messages\n")

        if len(messages) == 0:
            print("⚠️  No messages found!")
            print("This could mean:")
            print("  1. No emails in the last 30 days")
            print("  2. Gmail API credentials are not configured")
            print("  3. Email service is not initialized properly")
            return

        # Process each message
        processed = 0
        created = 0
        errors = []

        for i, msg in enumerate(messages):
            msg_id = msg['id']
            print(f"Processing message {i+1}/{len(messages)}: {msg_id}")

            # Check if already processed (just for info, we'll process anyway)
            already_processed = email_service.is_message_processed(msg_id, user_id)
            if already_processed:
                print(f"  ℹ  Message was previously processed (reprocessing anyway)")

            # Process the message
            try:
                result = ingestion.process_email(
                    message_id=msg_id,
                    user_id=user_id
                )

                if result['success'] and result['receipts_created']:
                    print(f"  ✓ Created {len(result['receipts_created'])} receipt(s)")
                    created += len(result['receipts_created'])
                elif result['success']:
                    print(f"  - Processed but no receipts created")
                else:
                    print(f"  ✗ Processing failed: {', '.join(result['errors'])}")
                    errors.extend(result['errors'])

                processed += 1

            except Exception as e:
                print(f"  ✗ Error: {str(e)}")
                errors.append(f"Error processing {msg_id}: {str(e)}")

        # Summary
        print(f"\n{'='*60}")
        print("Processing Complete!")
        print(f"{'='*60}")
        print(f"Total messages: {len(messages)}")
        print(f"Processed: {processed}")
        print(f"Receipts created: {created}")
        print(f"Errors: {len(errors)}")

        if errors:
            print(f"\nFirst 5 errors:")
            for error in errors[:5]:
                print(f"  - {error}")

        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n✗ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    force_reprocess(USER_ID, days_back=30)
