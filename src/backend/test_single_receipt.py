#!/usr/bin/env python3
"""Reprocess a single receipt by ID."""

import sys
sys.path.insert(0, '/Users/jordanshaw/Desktop/expense-reporting/src/backend')

from app.utils.supabase import get_supabase_client

# LinkedIn receipt ID
RECEIPT_ID = "c426120b-c5fe-476e-ac5b-3ab6e28e9481"
USER_ID = "407b70ad-8e64-43a1-81b4-da0977066e6d"

# Delete the LinkedIn receipt
supabase = get_supabase_client()
print("Deleting LinkedIn receipt...")
supabase.table('receipts').delete().eq('id', RECEIPT_ID).execute()
print(f"✓ Deleted receipt {RECEIPT_ID}")

# Now reprocess the LinkedIn email
from app.services.email import EmailService
from app.services.ingestion import IngestionService

email_service = EmailService()
ingestion = IngestionService()

# LinkedIn message ID (from earlier output)
LINKEDIN_MESSAGE_ID = "19c34ad841793476"

print(f"\nReprocessing LinkedIn email {LINKEDIN_MESSAGE_ID}...")
result = ingestion.process_email(
    message_id=LINKEDIN_MESSAGE_ID,
    user_id=USER_ID
)

if result['success'] and result['receipts_created']:
    print(f"✓ Created receipt!")

    # Get the receipt details
    response = supabase.table('receipts').select('*').eq('user_id', USER_ID).order('created_at', desc=True).limit(1).execute()
    receipt = response.data[0]

    print(f"\nReceipt Details:")
    print(f"  Vendor: {receipt['vendor']}")
    print(f"  Amount: ${receipt['amount']} {receipt['currency']}")
    print(f"  Tax: ${receipt['tax']}" if receipt['tax'] else "  Tax: None")
    print(f"  Date: {receipt['date']}")

    if receipt['tax'] == 1.19:
        print("\n✓ LinkedIn tax extraction fix verified!")
    else:
        print(f"\n✗ Expected tax $1.19, got ${receipt['tax']}")
else:
    print("✗ Failed to create receipt")
    print(f"Errors: {result['errors']}")
