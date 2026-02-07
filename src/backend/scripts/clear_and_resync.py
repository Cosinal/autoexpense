#!/usr/bin/env python3
"""
Clear database receipts and reprocess emails with updated parser.
"""

import sys
sys.path.insert(0, '/Users/jordanshaw/Desktop/expense-reporting/src/backend')

from app.utils.supabase import get_supabase_client
from app.services.ingestion import IngestionService

# User ID from tests
USER_ID = "407b70ad-8e64-43a1-81b4-da0977066e6d"

def clear_receipts(user_id: str):
    """Delete all receipts for a user from database and storage."""
    print(f"\n{'='*60}")
    print("Clearing Receipts from Database")
    print(f"{'='*60}")

    supabase = get_supabase_client()

    # Get all receipts for this user
    response = supabase.table('receipts').select('*').eq('user_id', user_id).execute()
    receipts = response.data

    print(f"\nFound {len(receipts)} receipts to delete")

    if len(receipts) == 0:
        print("No receipts to delete!")
        return

    # Delete files from storage
    print("\nDeleting files from storage...")
    storage_client = supabase.storage.from_('receipts')

    for receipt in receipts:
        file_name = receipt.get('file_name')
        if file_name:
            # Storage path is user_id/uuid_filename
            # Extract the full path from file_url or construct it
            try:
                # File is stored as: user_id/uuid_filename
                # We need to find the actual storage path
                # Let's list files in user folder and delete them
                pass  # We'll delete by listing all files
            except Exception as e:
                print(f"  Error deleting file {file_name}: {e}")

    # Delete all files in user folder
    try:
        files = storage_client.list(user_id)
        if files:
            print(f"  Deleting {len(files)} files from storage...")
            for file in files:
                try:
                    storage_client.remove([f"{user_id}/{file['name']}"])
                    print(f"    ✓ Deleted {file['name']}")
                except Exception as e:
                    print(f"    ✗ Error deleting {file['name']}: {e}")
    except Exception as e:
        print(f"  Warning: Could not list/delete storage files: {e}")

    # Delete receipts from database
    print("\nDeleting receipts from database...")
    delete_response = supabase.table('receipts').delete().eq('user_id', user_id).execute()

    print(f"✓ Deleted {len(receipts)} receipts from database")
    print(f"{'='*60}\n")

def resync_emails(user_id: str, days_back: int = 30):
    """Re-sync emails to reprocess with updated parser."""
    print(f"\n{'='*60}")
    print("Re-syncing Emails with Updated Parser")
    print(f"{'='*60}")
    print(f"\nUser ID: {user_id}")
    print(f"Days back: {days_back}")

    ingestion = IngestionService()
    summary = ingestion.sync_emails(user_id=user_id, days_back=days_back)

    print(f"\n{'='*60}")
    print("Sync Complete!")
    print(f"{'='*60}")
    print(f"Messages checked: {summary['messages_checked']}")
    print(f"Messages processed: {summary['messages_processed']}")
    print(f"Receipts created: {summary['receipts_created']}")

    if summary['errors']:
        print(f"\nErrors ({len(summary['errors'])}):")
        for error in summary['errors'][:5]:  # Show first 5 errors
            print(f"  - {error}")
        if len(summary['errors']) > 5:
            print(f"  ... and {len(summary['errors']) - 5} more")
    else:
        print("\n✓ No errors!")

    print(f"{'='*60}\n")

    return summary

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Clear Database & Resync Script")
    print("="*60)
    print("\nThis will:")
    print("1. Delete all receipts from the database")
    print("2. Delete all files from storage")
    print("3. Re-sync emails to reprocess with the updated parser")
    print(f"\nUser ID: {USER_ID}")

    response = input("\nContinue? (y/n): ").strip().lower()
    if response != 'y':
        print("Cancelled.")
        sys.exit(0)

    # Step 1: Clear receipts
    clear_receipts(USER_ID)

    # Step 2: Resync emails
    summary = resync_emails(USER_ID, days_back=30)

    # Step 3: Show results
    if summary['receipts_created'] > 0:
        print("\n" + "="*60)
        print("Success! Receipts have been reprocessed.")
        print("="*60)
        print("\nYou can now check the receipts with the updated parser:")
        print(f"  curl \"http://localhost:8000/receipts?user_id={USER_ID}&limit=10\"")
    else:
        print("\n⚠️  No receipts were created during resync.")
        print("This might mean all emails were already processed.")
        print("Check the errors above for details.")
