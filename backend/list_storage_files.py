"""
Script to list all files in Supabase storage for a user.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.utils.supabase import get_supabase_client
from app.config import settings

USER_ID = "407b70ad-8e64-43a1-81b4-da0977066e6d"

def list_user_files():
    """List all files for a user in Supabase storage."""
    print(f"Listing files for user: {USER_ID}")
    print("="*80)

    supabase = get_supabase_client()

    try:
        # List files in the user's folder
        response = supabase.storage.from_(settings.RECEIPT_BUCKET).list(USER_ID)

        print(f"\nFound {len(response)} files:\n")

        for file in response:
            print(f"  Name: {file['name']}")
            print(f"  ID: {file.get('id', 'N/A')}")
            print(f"  Size: {file.get('metadata', {}).get('size', 'N/A')} bytes")
            print(f"  Updated: {file.get('updated_at', 'N/A')}")
            print("-" * 80)

        # Look for specific files
        print("\nSearching for Steam and Lovable files...")
        steam_files = [f for f in response if 'steam' in f['name'].lower() or 'email_19c30b1e' in f['name'].lower()]
        lovable_files = [f for f in response if 'lovable' in f['name'].lower() or 'NEQQK5NF' in f['name'] or '2556-3007' in f['name']]

        print(f"\nSteam files ({len(steam_files)}):")
        for f in steam_files:
            print(f"  - {f['name']}")

        print(f"\nLovable files ({len(lovable_files)}):")
        for f in lovable_files:
            print(f"  - {f['name']}")

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    list_user_files()
