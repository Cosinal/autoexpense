"""
Test OCR and parsing on existing receipts.
Downloads a receipt from Supabase and tests extraction.

Usage:
    python test_ocr_parsing.py
"""

from app.services.ocr import OCRService
from app.services.parser import ReceiptParser
from app.services.storage import StorageService
from app.utils.supabase import get_supabase_client
import requests


def test_ocr_and_parsing():
    """Test OCR and parsing on existing receipts."""

    print("=" * 60)
    print("OCR & Parsing Test")
    print("=" * 60)

    # Initialize services
    ocr_service = OCRService()
    parser = ReceiptParser()
    supabase = get_supabase_client()

    # Get a recent receipt from the database
    print("\n1. Fetching a recent receipt from database...")
    try:
        response = supabase.table('receipts').select('*').limit(1).order(
            'created_at', desc=True
        ).execute()

        if not response.data:
            print("✗ No receipts found in database")
            print("\nPlease run test_sync.py first to create some receipts.")
            return

        receipt = response.data[0]
        print(f"✓ Found receipt: {receipt['file_name']}")
        print(f"  File URL: {receipt['file_url']}")
        print(f"  Current data:")
        print(f"    Vendor: {receipt.get('vendor', 'NULL')}")
        print(f"    Amount: {receipt.get('amount', 'NULL')}")
        print(f"    Date: {receipt.get('date', 'NULL')}")

    except Exception as e:
        print(f"✗ Error fetching receipt: {str(e)}")
        return

    # Download the file
    print("\n2. Downloading file from storage...")
    try:
        # Extract file path from URL
        file_url = receipt['file_url']

        # Download file using requests
        # Note: For private buckets, we'd need a signed URL
        # For now, we'll try direct download
        response_file = requests.get(file_url)

        if response_file.status_code == 200:
            file_data = response_file.content
            print(f"✓ Downloaded {len(file_data)} bytes")
        else:
            # Try alternative: get from storage directly
            print("  Direct download failed, trying Supabase storage...")

            # Parse the path from URL
            # URL format: https://xxx.supabase.co/storage/v1/object/public/receipts/path
            path_parts = file_url.split('/receipts/')
            if len(path_parts) > 1:
                file_path = path_parts[1]

                storage_service = StorageService()
                signed_url = storage_service.create_signed_url(file_path, expires_in=300)

                if signed_url:
                    response_file = requests.get(signed_url)
                    file_data = response_file.content
                    print(f"✓ Downloaded {len(file_data)} bytes via signed URL")
                else:
                    print("✗ Could not get signed URL")
                    return
            else:
                print("✗ Could not parse file path from URL")
                return

    except Exception as e:
        print(f"✗ Error downloading file: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # Run OCR
    print("\n3. Running OCR...")
    try:
        text = ocr_service.extract_and_normalize(
            file_data=file_data,
            mime_type=receipt['mime_type'],
            filename=receipt['file_name']
        )

        print(f"✓ Extracted {len(text)} characters")
        print("\nExtracted text (first 500 chars):")
        print("-" * 60)
        print(text[:500])
        print("-" * 60)

    except Exception as e:
        print(f"✗ Error running OCR: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # Parse the text
    print("\n4. Parsing receipt data...")
    try:
        parsed_data = parser.parse(text)

        print("\nParsed Data:")
        print("=" * 60)
        print(f"Vendor:     {parsed_data.get('vendor', 'Not found')}")
        print(f"Amount:     {parsed_data.get('currency', 'USD')} {parsed_data.get('amount', 'Not found')}")
        print(f"Date:       {parsed_data.get('date', 'Not found')}")
        print(f"Tax:        {parsed_data.get('tax', 'Not found')}")
        print(f"Confidence: {parsed_data.get('confidence', 0):.0%}")
        print("=" * 60)

        # Update the receipt in the database
        print("\n5. Updating receipt in database...")
        update_data = {
            'vendor': parsed_data.get('vendor'),
            'amount': float(parsed_data['amount']) if parsed_data.get('amount') else None,
            'currency': parsed_data.get('currency', 'USD'),
            'date': parsed_data.get('date'),
            'tax': float(parsed_data['tax']) if parsed_data.get('tax') else None,
        }

        supabase.table('receipts').update(update_data).eq('id', receipt['id']).execute()
        print("✓ Receipt updated successfully")

        print("\n" + "=" * 60)
        print("✓ OCR and Parsing Test Complete!")
        print("=" * 60)
        print("\nCheck Supabase:")
        print("Go to Table Editor → receipts table")
        print("The receipt should now have vendor, amount, and date populated")

    except Exception as e:
        print(f"✗ Error parsing or updating: {str(e)}")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    test_ocr_and_parsing()
