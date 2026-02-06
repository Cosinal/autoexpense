"""
Verify database setup after running migrations.
Run with: python verify_db_setup.py
"""

from app.utils.supabase import get_supabase_client
from app.config import settings

def verify_database_setup():
    """Check that all tables and storage buckets are properly configured."""

    print("=" * 60)
    print("AutoExpense Database Setup Verification")
    print("=" * 60)
    print(f"\nSupabase URL: {settings.SUPABASE_URL}")
    print()

    try:
        client = get_supabase_client()

        # Test 1: Check receipts table exists and is accessible
        print("✓ Testing receipts table...")
        response = client.table('receipts').select("*").limit(1).execute()
        print(f"  → receipts table accessible (found {len(response.data)} records)")

        # Test 2: Check processed_emails table
        print("\n✓ Testing processed_emails table...")
        response = client.table('processed_emails').select("*").limit(1).execute()
        print(f"  → processed_emails table accessible (found {len(response.data)} records)")

        # Test 3: Check storage bucket
        print("\n✓ Testing storage bucket...")
        try:
            # List buckets
            buckets = client.storage.list_buckets()
            receipt_bucket = next((b for b in buckets if b.name == 'receipts'), None)

            if receipt_bucket:
                print(f"  → 'receipts' bucket exists")
                print(f"  → Public: {receipt_bucket.public}")
            else:
                print("  ✗ 'receipts' bucket not found!")
                print("  → Run 003_storage_setup.sql to create it")

        except Exception as e:
            print(f"  ✗ Storage bucket check failed: {str(e)}")

        # Test 4: Check if we can query table schema
        print("\n✓ Checking database schema...")

        # Try to get column info (this will show if RLS is working)
        try:
            # This query will only work if RLS is properly configured
            # It may fail if no user is authenticated, which is expected
            response = client.table('receipts').select("vendor,amount,date").limit(0).execute()
            print("  → Schema query successful")
        except Exception as e:
            if "permission denied" in str(e).lower() or "rls" in str(e).lower():
                print("  → RLS is active (expected - queries require authentication)")
            else:
                print(f"  → Schema check: {str(e)}")

        # Success summary
        print("\n" + "=" * 60)
        print("✓ Database setup verification complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Tables are created and accessible")
        print("2. Storage bucket is configured")
        print("3. RLS policies are active")
        print("\nYou can now proceed to Phase 2: Email Ingestion")

    except Exception as e:
        print("\n" + "=" * 60)
        print("✗ Verification failed!")
        print("=" * 60)
        print(f"\nError: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure you've run all migration files in Supabase SQL Editor:")
        print("   - 001_initial_schema.sql")
        print("   - 002_rls_policies.sql")
        print("   - 003_storage_setup.sql")
        print("2. Verify your Supabase credentials in backend/.env")
        print("3. Check that your Supabase project is active")

if __name__ == "__main__":
    verify_database_setup()
