"""
Test script to verify Supabase connection.
Run with: python test_connection.py
"""

from app.utils.supabase import get_supabase_client
from app.config import settings

def test_supabase_connection():
    print("Testing Supabase connection...")
    print(f"URL: {settings.SUPABASE_URL}")

    try:
        client = get_supabase_client()

        # Try to list tables (should work if connection is successful)
        response = client.table('receipts').select("*").limit(1).execute()

        print("✓ Connection successful!")
        print(f"Response: {response}")

    except Exception as e:
        print(f"✗ Connection failed: {str(e)}")
        print("\nMake sure you have:")
        print("1. Created a Supabase project")
        print("2. Updated the .env file with your credentials")
        print("3. Created the 'receipts' table (see Phase 1)")

if __name__ == "__main__":
    test_supabase_connection()
