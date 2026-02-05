"""
Debug script to see what OCR actually extracted.
"""

from app.services.ocr import OCRService
from app.services.parser import ReceiptParser
from app.utils.supabase import get_supabase_client

# Get the most recent receipt
supabase = get_supabase_client()
response = supabase.table('receipts').select('*').order('created_at', desc=True).limit(1).execute()

if response.data:
    receipt = response.data[0]
    print("="*60)
    print(f"Receipt: {receipt['file_name']}")
    print("="*60)

    # Download the file
    import requests
    from app.services.storage import StorageService

    file_url = receipt['file_url']
    path_parts = file_url.split('/receipts/')
    if len(path_parts) > 1:
        file_path = path_parts[1].split('?')[0]  # Remove query params

        storage_service = StorageService()
        signed_url = storage_service.create_signed_url(file_path, expires_in=300)

        if signed_url:
            response_file = requests.get(signed_url)
            file_data = response_file.content

            # Run OCR
            ocr_service = OCRService()
            text = ocr_service.extract_and_normalize(
                file_data=file_data,
                mime_type=receipt['mime_type'],
                filename=receipt['file_name']
            )

            print("\nEXTRACTED TEXT:")
            print("-"*60)
            print(text)
            print("-"*60)
            print(f"\nText length: {len(text)} characters")

            # Try parsing
            print("\n" + "="*60)
            print("PARSING ATTEMPT:")
            print("="*60)
            parser = ReceiptParser()
            parsed = parser.parse(text)

            print(f"\nVendor: {parsed.get('vendor')}")
            print(f"Amount: {parsed.get('amount')}")
            print(f"Currency: {parsed.get('currency')}")
            print(f"Date: {parsed.get('date')}")
            print(f"Tax: {parsed.get('tax')}")
            print(f"Confidence: {parsed.get('confidence')}")

else:
    print("No receipts found")
