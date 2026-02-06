#!/usr/bin/env python3
"""
Download specific failed receipts from Supabase storage for analysis.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_SERVICE_KEY")  # Fixed: was SUPABASE_SERVICE_ROLE_KEY
supabase: Client = create_client(url, key)

USER_ID = "407b70ad-8e64-43a1-81b4-da0977066e6d"

# List of failed receipts to download (with actual storage filenames)
FAILED_RECEIPTS = [
    {
        "name": "Sephora",
        "filename": "473cdf47-5d76-42f1-8e12-8febea5d5936_email_19c33910.txt",
        "short_name": "email_19c33910.txt"
    },
    {
        "name": "Urban Outfitters",
        "filename": "a80b116e-6033-4a02-a20d-fea2585ce471_email_19c33917.txt",
        "short_name": "email_19c33917.txt"
    },
    {
        "name": "Flighthub",
        "filename": "686636ee-cffe-4371-9468-44b137157991_email_19c3391e.txt",
        "short_name": "email_19c3391e.txt"
    },
    {
        "name": "PSA Canada",
        "filename": "41a4b1f9-2e49-41cc-b289-9b6ea1e8c421_Jorden Shaw - Collectors Universe Canada Invoice  - Jan 6th 2026.pdf",
        "short_name": "PSA_Canada.pdf"
    },
    {
        "name": "GeoGuessr",
        "filename": "70e8da1a-111a-45b2-844c-3981401a34af_invoice_184-324336_GeoGuessr.pdf",
        "short_name": "GeoGuessr.pdf"
    }
]

def download_receipt(filename: str, short_name: str):
    """Download a receipt from Supabase storage."""
    try:
        # Construct the storage path
        storage_path = f"{USER_ID}/{filename}"

        print(f"\n{'='*80}")
        print(f"Downloading: {filename}")
        print(f"Path: {storage_path}")
        print(f"{'='*80}")

        # Download the file
        response = supabase.storage.from_("receipts").download(storage_path)

        # Save locally with short name
        local_path = f"/Users/jordanshaw/Desktop/expense-reporting/backend/failed_receipts/{short_name}"
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        with open(local_path, 'wb') as f:
            f.write(response)

        print(f"✓ Downloaded to: {local_path}")
        print(f"  Size: {len(response)} bytes")

        return local_path

    except Exception as e:
        print(f"✗ Error downloading {filename}: {str(e)}")
        return None

def main():
    print("DOWNLOADING FAILED RECEIPTS FOR ANALYSIS")
    print("="*80)

    downloaded = []
    failed = []

    for receipt in FAILED_RECEIPTS:
        local_path = download_receipt(receipt["filename"], receipt["short_name"])
        if local_path:
            downloaded.append((receipt["name"], local_path))
        else:
            failed.append(receipt["name"])

    print(f"\n{'='*80}")
    print("DOWNLOAD SUMMARY")
    print(f"{'='*80}")
    print(f"✓ Successfully downloaded: {len(downloaded)}")
    for name, path in downloaded:
        print(f"  - {name}: {path}")

    if failed:
        print(f"\n✗ Failed to download: {len(failed)}")
        for name in failed:
            print(f"  - {name}")

if __name__ == "__main__":
    main()
