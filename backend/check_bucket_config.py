"""
Check bucket configuration and test file access.
"""

from app.utils.supabase import get_supabase_client
from app.config import settings

def check_bucket():
    """Check bucket configuration."""
    supabase = get_supabase_client()
    bucket_name = settings.RECEIPT_BUCKET

    print(f"Checking bucket: {bucket_name}")

    try:
        # Get bucket details
        buckets = supabase.storage.list_buckets()

        for bucket in buckets:
            if bucket.name == bucket_name:
                print(f"\nBucket: {bucket.name}")
                print(f"ID: {bucket.id}")
                print(f"Public: {bucket.public}")
                print(f"Created: {bucket.created_at}")

                if not bucket.public:
                    print("\n⚠️  ISSUE: Bucket is PRIVATE")
                    print("\nTo fix this, make the bucket public:")
                    print(f"1. Go to: {settings.SUPABASE_URL}/project/default/storage/buckets")
                    print(f"2. Click on the '{bucket_name}' bucket")
                    print(f"3. Click 'Configuration' or settings icon")
                    print(f"4. Toggle 'Public bucket' to ON")
                    print(f"5. Save changes")
                else:
                    print("\n✓ Bucket is PUBLIC")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    check_bucket()
