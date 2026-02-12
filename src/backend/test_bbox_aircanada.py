#!/usr/bin/env python3
"""
Test bbox extraction on Air Canada receipt.

This script demonstrates Phase 1 of bbox-based spatial extraction.
"""

from pathlib import Path
from app.services.ocr import OCRService
from app.services.bbox_extractor import BboxExtractor


def test_air_canada_receipt():
    """Test bbox extraction on Air Canada receipt that has the RT00012.65 issue."""
    print("=" * 80)
    print("PHASE 1: Bbox Spatial Extraction - Air Canada Receipt Test")
    print("=" * 80)
    print()

    # Load Air Canada receipt
    pdf_path = Path('tests/data/receipts/failed/Air_Canada_Booking_Confirmation_AOU65V.pdf')

    if not pdf_path.exists():
        print(f"ERROR: Receipt not found at {pdf_path}")
        return False

    print(f"Loading receipt: {pdf_path.name}")
    print()

    # Extract with bbox
    ocr = OCRService()
    with open(pdf_path, 'rb') as f:
        file_data = f.read()

    print("Extracting OCR text and bounding boxes...")
    bbox_data = ocr.extract_bbox_from_pdf(file_data, page_num=0)

    # Check if we got data
    if not bbox_data or 'text' not in bbox_data or len(bbox_data['text']) == 0:
        print("ERROR: No bbox data extracted")
        return False

    print(f"  Detected {len(bbox_data['text'])} text elements")
    print()

    # Create extractor
    extractor = BboxExtractor(bbox_data)
    print(f"  Built word index: {len(extractor.words)} words")
    print()

    # Show first few words for debugging
    print("First 30 words detected:")
    print(extractor.visualize_words(max_words=30))
    print()

    # Extract tax using bbox
    print("-" * 80)
    print("Extracting tax field using spatial search...")
    print("-" * 80)
    tax = extractor.extract_tax()

    print(f"Extracted tax: {tax}")
    print(f"Expected tax:  2.65")
    print()

    # Check success
    success = tax == '2.65'
    if success:
        print("SUCCESS: Bbox extraction correctly identified tax amount!")
    else:
        print(f"FAILED: Expected '2.65', got '{tax}'")

    print()

    # Extract amount as well
    print("-" * 80)
    print("Extracting amount field using spatial search...")
    print("-" * 80)
    amount = extractor.extract_amount()

    print(f"Extracted amount: {amount}")
    print(f"Expected amount:  126.07")
    print()

    amount_success = amount == '126.07'
    if amount_success:
        print("SUCCESS: Bbox extraction correctly identified total amount!")
    else:
        print(f"PARTIAL: Expected '126.07', got '{amount}'")

    print()
    print("=" * 80)

    return success


if __name__ == '__main__':
    test_air_canada_receipt()
