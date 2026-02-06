"""
Setup script to create and configure Supabase storage bucket.
"""

from app.utils.supabase import get_supabase_client
from app.config import settings

def setup_storage_bucket():
    """Create and configure the receipts storage bucket."""
    supabase = get_supabase_client()
    bucket_name = settings.RECEIPT_BUCKET

    print(f"Setting up storage bucket: {bucket_name}")

    try:
        # Try to list buckets
        buckets = supabase.storage.list_buckets()
        existing_buckets = [b.name for b in buckets]

        print(f"Existing buckets: {existing_buckets}")

        if bucket_name in existing_buckets:
            print(f"✓ Bucket '{bucket_name}' already exists")
        else:
            print(f"Creating bucket '{bucket_name}'...")

            # Create bucket with public access
            result = supabase.storage.create_bucket(
                bucket_name,
                options={
                    "public": True,
                    "file_size_limit": 10485760  # 10MB
                }
            )

            print(f"✓ Bucket '{bucket_name}' created successfully")

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        print("\nIf you get a permission error, you'll need to create the bucket manually:")
        print(f"1. Go to: {settings.SUPABASE_URL}/project/default/storage/buckets")
        print(f"2. Click 'New bucket'")
        print(f"3. Name: {bucket_name}")
        print(f"4. Set 'Public bucket' to ON")
        print(f"5. Click 'Create bucket'")
        return False

    return True

if __name__ == "__main__":
    setup_storage_bucket()
