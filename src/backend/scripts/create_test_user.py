"""
Create a test user in Supabase for development/testing.
This creates a user directly in the auth system.

Usage:
    python create_test_user.py
"""

from app.utils.supabase import get_supabase_client
from app.config import settings
import uuid


def create_test_user():
    """Create a test user in Supabase auth."""

    print("=" * 60)
    print("Create Test User for AutoExpense")
    print("=" * 60)

    supabase = get_supabase_client()

    # Test user details
    test_email = "test@autoexpense.local"
    test_password = "TestPassword123!"

    print(f"\nCreating test user:")
    print(f"  Email: {test_email}")
    print(f"  Password: {test_password}")
    print()

    try:
        # Try to sign up the user
        print("Attempting to create user in Supabase Auth...")

        response = supabase.auth.sign_up({
            "email": test_email,
            "password": test_password
        })

        if response.user:
            user_id = response.user.id
            print(f"\n✓ User created successfully!")
            print(f"  User ID: {user_id}")
            print()
            print("=" * 60)
            print("Test User Credentials")
            print("=" * 60)
            print(f"Email: {test_email}")
            print(f"Password: {test_password}")
            print(f"User ID: {user_id}")
            print()
            print("Save this User ID for testing:")
            print("-" * 60)
            print(f"TEST_USER_ID={user_id}")
            print("-" * 60)
            print()
            print("Next steps:")
            print("1. Add this to your backend/.env file")
            print("2. Run test_sync.py again")
            print("3. Or use this user ID in API calls")

            return user_id

        else:
            print("✗ Failed to create user - no user returned")

            # Try alternative: create a dummy user directly in auth.users
            print("\nTrying alternative method...")
            print("Creating user with UUID directly...")

            # Generate a UUID
            user_id = str(uuid.uuid4())

            # Note: We can't directly insert into auth.users without admin privileges
            # So we'll use a workaround for testing
            print(f"\nGenerated test User ID: {user_id}")
            print()
            print("⚠️  Note: This user won't have auth credentials.")
            print("For testing Phase 2, you can temporarily disable the foreign key.")
            print()
            print("To disable the foreign key temporarily:")
            print("Run this in Supabase SQL Editor:")
            print("-" * 60)
            print("ALTER TABLE receipts DROP CONSTRAINT IF EXISTS fk_user;")
            print("ALTER TABLE processed_emails DROP CONSTRAINT IF EXISTS fk_user_email;")
            print("-" * 60)
            print()
            print("After Phase 2 testing, re-enable with:")
            print("-" * 60)
            print("ALTER TABLE receipts ADD CONSTRAINT fk_user")
            print("  FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;")
            print("ALTER TABLE processed_emails ADD CONSTRAINT fk_user_email")
            print("  FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;")
            print("-" * 60)

            return None

    except Exception as e:
        error_msg = str(e)
        print(f"\n✗ Error: {error_msg}")

        if "already registered" in error_msg or "already exists" in error_msg:
            print("\n✓ Test user already exists!")
            print("\nTo get the user ID, check Supabase dashboard:")
            print("1. Go to Authentication → Users")
            print(f"2. Find user: {test_email}")
            print("3. Copy the User ID")
            print()
            print("Or run this query in SQL Editor:")
            print("-" * 60)
            print(f"SELECT id FROM auth.users WHERE email = '{test_email}';")
            print("-" * 60)
        else:
            print("\nQuick workaround for Phase 2 testing:")
            print("Temporarily disable foreign key constraints.")
            print("\nRun in Supabase SQL Editor:")
            print("-" * 60)
            print("ALTER TABLE receipts DROP CONSTRAINT IF EXISTS fk_user;")
            print("ALTER TABLE processed_emails DROP CONSTRAINT IF EXISTS fk_user_email;")
            print("-" * 60)
            print("\nThen you can use any user ID for testing.")
            print("Re-enable constraints after Phase 2 testing.")

        return None


if __name__ == "__main__":
    create_test_user()
