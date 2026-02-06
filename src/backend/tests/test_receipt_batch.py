#!/usr/bin/env python3
"""
Batch receipt testing tool.
Syncs emails and provides detailed analysis of parser performance.
"""

from app.services.ingestion import IngestionService
from app.utils.supabase import get_supabase_client
from datetime import datetime
import sys

def test_receipt_batch(user_id: str, days_back: int = 1):
    """
    Sync receipts and analyze parser performance.

    Args:
        user_id: User ID
        days_back: How many days back to check for emails
    """
    print("=" * 80)
    print("RECEIPT BATCH TEST")
    print("=" * 80)
    print(f"User ID: {user_id}")
    print(f"Days back: {days_back}")
    print()

    # Get receipts before sync
    supabase = get_supabase_client()
    before_response = supabase.table('receipts').select('id').eq('user_id', user_id).execute()
    receipts_before = len(before_response.data)

    # Sync emails
    print("Syncing emails...")
    print("-" * 80)
    ingestion = IngestionService()
    summary = ingestion.sync_emails(user_id=user_id, days_back=days_back)

    print()
    print("SYNC SUMMARY:")
    print(f"  Messages checked: {summary['messages_checked']}")
    print(f"  Messages processed: {summary['messages_processed']}")
    print(f"  Receipts created: {summary['receipts_created']}")
    print(f"  Errors: {len(summary['errors'])}")

    if summary['errors']:
        print("\n  Errors encountered:")
        for error in summary['errors']:
            print(f"    - {error}")

    print()

    # Get receipts after sync
    after_response = supabase.table('receipts').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
    receipts_after = len(after_response.data)
    new_receipts = receipts_after - receipts_before

    print("=" * 80)
    print(f"NEW RECEIPTS ANALYZED: {new_receipts}")
    print("=" * 80)
    print()

    if new_receipts == 0:
        print("No new receipts to analyze.")
        return

    # Analyze new receipts
    new_receipt_data = after_response.data[:new_receipts]

    # Stats
    has_vendor = sum(1 for r in new_receipt_data if r.get('vendor'))
    has_amount = sum(1 for r in new_receipt_data if r.get('amount'))
    has_date = sum(1 for r in new_receipt_data if r.get('date'))
    has_tax = sum(1 for r in new_receipt_data if r.get('tax'))

    print("EXTRACTION RATES:")
    print(f"  Vendor:  {has_vendor}/{new_receipts} ({has_vendor/new_receipts*100:.1f}%)")
    print(f"  Amount:  {has_amount}/{new_receipts} ({has_amount/new_receipts*100:.1f}%)")
    print(f"  Date:    {has_date}/{new_receipts} ({has_date/new_receipts*100:.1f}%)")
    print(f"  Tax:     {has_tax}/{new_receipts} ({has_tax/new_receipts*100:.1f}%)")
    print()

    # Detailed results
    print("DETAILED RESULTS:")
    print("-" * 80)

    for i, receipt in enumerate(new_receipt_data, 1):
        vendor = receipt.get('vendor', 'None')
        amount = receipt.get('amount')
        amount_str = f"${amount:.2f}" if amount else "None"
        tax = receipt.get('tax')
        tax_str = f"${tax:.2f}" if tax else "None"
        date = receipt.get('date', 'None')
        currency = receipt.get('currency', 'USD')
        file_name = receipt.get('file_name', 'Unknown')

        # Quality score
        score = 0
        if vendor and vendor != 'None': score += 25
        if amount: score += 25
        if date and date != 'None': score += 25
        if tax: score += 25

        # Status emoji
        if score >= 75:
            status = "✓ GOOD"
        elif score >= 50:
            status = "⚠ OK"
        else:
            status = "✗ POOR"

        print(f"\n{i}. {file_name[:50]}")
        print(f"   {status} (Score: {score}/100)")
        print(f"   Vendor: {vendor[:40]}")
        print(f"   Amount: {amount_str} {currency}")
        print(f"   Tax:    {tax_str}")
        print(f"   Date:   {date}")

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    # Summary recommendations
    issues = []
    if has_vendor < new_receipts * 0.8:
        issues.append("- Low vendor extraction rate - check for new receipt formats")
    if has_amount < new_receipts * 0.8:
        issues.append("- Low amount extraction rate - may need new amount patterns")
    if has_date < new_receipts * 0.5:
        issues.append("- Low date extraction rate - consider if dates are critical")

    if issues:
        print("\nRECOMMENDATIONS:")
        for issue in issues:
            print(issue)
    else:
        print("\n✓ All metrics look good! Parser is performing well.")

    print()

if __name__ == "__main__":
    user_id = "407b70ad-8e64-43a1-81b4-da0977066e6d"

    if len(sys.argv) > 1:
        days_back = int(sys.argv[1])
    else:
        days_back = 1

    test_receipt_batch(user_id, days_back)
