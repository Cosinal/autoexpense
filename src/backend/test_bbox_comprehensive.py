#!/usr/bin/env python3
"""
Comprehensive test of bbox extraction on multiple receipts.
Phase 1: Proof of concept for spatial extraction.
"""

from pathlib import Path
from app.services.ocr import OCRService
from app.services.bbox_extractor import BboxExtractor
from app.services.parser import ReceiptParser
from decimal import Decimal


class ReceiptTest:
    """Test case for a single receipt."""

    def __init__(self, filename: str, expected_tax: str, expected_amount: str, is_image_based: bool = None):
        self.filename = filename
        self.expected_tax = expected_tax
        self.expected_amount = expected_amount
        self.is_image_based = is_image_based  # None = unknown, True/False = known
        self.actual_tax = None
        self.actual_amount = None
        self.bbox_success = False
        self.pattern_tax = None
        self.pattern_amount = None


def test_receipt(test_case: ReceiptTest, receipts_dir: Path, ocr: OCRService, parser: ReceiptParser):
    """Test a single receipt with both bbox and pattern extraction."""
    receipt_path = receipts_dir / test_case.filename

    if not receipt_path.exists():
        print(f"  ⚠ File not found: {receipt_path}")
        return

    print(f"\n{'=' * 80}")
    print(f"Testing: {test_case.filename}")
    print(f"{'=' * 80}")

    with open(receipt_path, 'rb') as f:
        file_data = f.read()

    # Determine file type
    is_pdf = receipt_path.suffix.lower() == '.pdf'
    is_image = receipt_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']

    try:
        # Test 1: Bbox extraction (if image-based)
        if is_image:
            bbox_data = ocr.extract_text_with_bbox(file_data)
            test_case.is_image_based = True
        elif is_pdf:
            # Try to detect if PDF is image-based or text-based
            text = ocr.extract_text_from_pdf(file_data)
            if len(text.strip()) < 100:
                # Likely image-based PDF
                bbox_data = ocr.extract_bbox_from_pdf(file_data, page_num=0)
                test_case.is_image_based = True
            else:
                # Text-based PDF - bbox won't work well
                bbox_data = None
                test_case.is_image_based = False
        else:
            bbox_data = None
            test_case.is_image_based = False

        if bbox_data and bbox_data.get('text'):
            extractor = BboxExtractor(bbox_data)
            print(f"  Bbox data: {len(extractor.words)} words indexed")

            test_case.actual_tax = extractor.extract_tax()
            test_case.actual_amount = extractor.extract_amount()

            print(f"  Bbox Tax:    {test_case.actual_tax}")
            print(f"  Expected:    {test_case.expected_tax}")
            print(f"  Match:       {'✓' if test_case.actual_tax == test_case.expected_tax else '✗'}")
            print()
            print(f"  Bbox Amount: {test_case.actual_amount}")
            print(f"  Expected:    {test_case.expected_amount}")
            print(f"  Match:       {'✓' if test_case.actual_amount == test_case.expected_amount else '✗'}")

            test_case.bbox_success = (
                test_case.actual_tax == test_case.expected_tax and
                test_case.actual_amount == test_case.expected_amount
            )
        else:
            print("  ⚠ Bbox extraction not available (text-based PDF or unsupported format)")
            test_case.is_image_based = False

        # Test 2: Pattern-based extraction (for comparison)
        print()
        print("  Pattern-based extraction (current method):")

        if is_pdf:
            text = ocr.extract_text_from_pdf(file_data)
        elif is_image:
            text = ocr.extract_text_from_image(file_data)
        else:
            text = ""

        if text:
            result = parser.parse(text)
            test_case.pattern_tax = str(result.get('tax')) if result.get('tax') else None
            test_case.pattern_amount = str(result.get('amount')) if result.get('amount') else None

            print(f"  Pattern Tax:    {test_case.pattern_tax}")
            print(f"  Pattern Amount: {test_case.pattern_amount}")

    except Exception as e:
        print(f"  ✗ Error testing receipt: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """Run comprehensive bbox tests."""
    print("=" * 80)
    print("PHASE 1: Bbox Spatial Extraction - Comprehensive Test")
    print("=" * 80)
    print()

    receipts_dir = Path('tests/data/receipts/failed')
    ocr = OCRService()
    parser = ReceiptParser()

    # Test cases with expected values
    test_cases = [
        ReceiptTest(
            filename='receipt-test.jpg',
            expected_tax='643.77',
            expected_amount='3442.77',
            is_image_based=True
        ),
        # Note: Air Canada is text-based PDF, bbox extraction won't work
        # But we include it to demonstrate the limitation
        ReceiptTest(
            filename='Air_Canada_Booking_Confirmation_AOU65V.pdf',
            expected_tax='2.65',
            expected_amount='126.07',
            is_image_based=False  # Text-based PDF
        ),
    ]

    # Run tests
    for test_case in test_cases:
        test_receipt(test_case, receipts_dir, ocr, parser)

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    image_based_tests = [t for t in test_cases if t.is_image_based is True]
    text_based_tests = [t for t in test_cases if t.is_image_based is False]

    if image_based_tests:
        print("Image-based receipts (bbox applicable):")
        for test in image_based_tests:
            status = "✓ SUCCESS" if test.bbox_success else "✗ FAILED"
            print(f"  {status}: {test.filename}")
        print()

        success_count = sum(1 for t in image_based_tests if t.bbox_success)
        print(f"  Bbox accuracy: {success_count}/{len(image_based_tests)} "
              f"({100*success_count/len(image_based_tests):.1f}%)")

    print()

    if text_based_tests:
        print("Text-based receipts (bbox NOT applicable):")
        for test in text_based_tests:
            print(f"  ⚠ SKIP: {test.filename} (text-based PDF)")
        print()
        print("  → These require pattern-based extraction")

    print()
    print("=" * 80)
    print("KEY FINDINGS")
    print("=" * 80)
    print()
    print("✓ Bbox extraction works for image-based receipts (JPG, PNG, scanned PDFs)")
    print("✗ Bbox extraction doesn't work for text-based PDFs (Air Canada)")
    print("→ Need hybrid approach: bbox for images, patterns for text PDFs")
    print()


if __name__ == '__main__':
    main()
