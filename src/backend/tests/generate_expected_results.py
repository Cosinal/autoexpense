#!/usr/bin/env python3
"""
Generate Expected Results Helper - Auto-generates JSON metadata from PDFs

This script:
1. Finds all PDF files in tests/data/receipts/ without matching JSON files
2. Runs OCR + parser on each PDF
3. Generates JSON files with extracted values
4. User reviews and corrects as needed

Usage:
    python3 tests/generate_expected_results.py
    python3 tests/generate_expected_results.py --folder failed
    python3 tests/generate_expected_results.py --overwrite  # Regenerate existing JSONs
"""

import sys
import os
import json
import argparse
import mimetypes
from pathlib import Path
from decimal import Decimal
from typing import Dict, Any, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.ocr import OCRService
from app.services.parser import ReceiptParser


def generate_json_for_pdf(pdf_path: Path, ocr_service: OCRService,
                          parser: ReceiptParser, overwrite: bool = False) -> bool:
    """Generate expected results JSON for a single PDF."""

    json_path = pdf_path.with_suffix('.json')

    # Skip if JSON already exists (unless overwrite=True)
    if json_path.exists() and not overwrite:
        print(f"  ⏭️  Skipping {pdf_path.name} - JSON already exists")
        return False

    print(f"\n{'='*80}")
    print(f"Processing: {pdf_path.name}")
    print(f"{'='*80}")

    try:
        # Read file as bytes
        with open(pdf_path, 'rb') as f:
            file_data = f.read()

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(str(pdf_path))
        if not mime_type:
            # Default to PDF if can't detect
            mime_type = 'application/pdf'

        # Run OCR
        print(f"\n1. Running OCR... (MIME type: {mime_type})")
        ocr_text = ocr_service.extract_text_from_file(
            file_data=file_data,
            mime_type=mime_type,
            filename=pdf_path.name
        )

        if not ocr_text or ocr_text.strip() == '':
            print(f"  ✗ OCR extracted no text - skipping")
            return False

        print(f"   ✓ OCR extracted {len(ocr_text)} characters")

        # Parse
        print(f"\n2. Parsing extracted text...")
        parsed = parser.parse(ocr_text)

        # Convert Decimal to string for JSON serialization
        def serialize_value(value):
            if value is None:
                return None
            if isinstance(value, Decimal):
                return str(value)
            return value

        # Build expected results
        expected = {
            "vendor": serialize_value(parsed.get('vendor')),
            "amount": serialize_value(parsed.get('amount')),
            "date": serialize_value(parsed.get('date')),
            "currency": serialize_value(parsed.get('currency')),
            "tax": serialize_value(parsed.get('tax')),
            "notes": "Auto-generated - please review and correct"
        }

        # Show what was extracted
        print(f"\n3. Extracted values:")
        for field, value in expected.items():
            if field != 'notes':
                print(f"   {field}: {value}")

        # Write JSON file
        print(f"\n4. Writing JSON to {json_path.name}...")
        with open(json_path, 'w') as f:
            json.dump(expected, f, indent=2)

        print(f"   ✓ JSON file created")
        print(f"\n{'='*80}")
        print(f"✓ SUCCESS - Review {json_path.name} and correct any errors")
        print(f"{'='*80}")

        return True

    except Exception as e:
        print(f"\n✗ Error processing {pdf_path.name}: {e}")
        return False


def find_receipts_without_json(receipts_dir: Path, folder: str = None) -> List[Path]:
    """Find all receipt files (PDFs and images) that don't have matching JSON files."""

    if folder:
        search_dirs = [receipts_dir / folder]
    else:
        search_dirs = [
            receipts_dir / 'passed',
            receipts_dir / 'failed',
            receipts_dir / 'edge_cases'
        ]

    receipts_without_json = []

    # Look for PDFs and common image formats
    extensions = ['*.pdf', '*.jpg', '*.jpeg', '*.png']

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        for ext in extensions:
            for receipt_path in search_dir.glob(ext):
                json_path = receipt_path.with_suffix('.json')
                if not json_path.exists():
                    receipts_without_json.append(receipt_path)

    return receipts_without_json


def main():
    parser_args = argparse.ArgumentParser(
        description='Auto-generate expected results JSON files from PDFs'
    )
    parser_args.add_argument(
        '--folder', '-f', type=str,
        help='Process only PDFs in specific folder (passed/failed/edge_cases)'
    )
    parser_args.add_argument(
        '--overwrite', '-o', action='store_true',
        help='Regenerate JSON files even if they already exist'
    )
    args = parser_args.parse_args()

    # Find receipts directory
    tests_dir = Path(__file__).parent
    receipts_dir = tests_dir / 'data' / 'receipts'

    if not receipts_dir.exists():
        print(f"Error: Receipts directory not found: {receipts_dir}")
        sys.exit(1)

    # Find receipt files without JSON files
    if args.overwrite:
        # Find all receipt files (will overwrite existing JSONs)
        if args.folder:
            search_dirs = [receipts_dir / args.folder]
        else:
            search_dirs = [
                receipts_dir / 'passed',
                receipts_dir / 'failed',
                receipts_dir / 'edge_cases'
            ]

        receipt_files = []
        extensions = ['*.pdf', '*.jpg', '*.jpeg', '*.png']
        for search_dir in search_dirs:
            if search_dir.exists():
                for ext in extensions:
                    receipt_files.extend(search_dir.glob(ext))
    else:
        receipt_files = find_receipts_without_json(receipts_dir, folder=args.folder)

    if not receipt_files:
        print("\n✓ No receipt files found without JSON files")
        print("\nAll receipt files already have expected results JSON files.")
        print("Use --overwrite to regenerate existing JSON files.")
        return

    print(f"\n{'='*80}")
    print(f"GENERATE EXPECTED RESULTS - {len(receipt_files)} files")
    print(f"{'='*80}")
    print(f"\nFound {len(receipt_files)} receipt file(s) without JSON files:")
    for receipt_path in sorted(receipt_files):
        print(f"  - {receipt_path.name}")

    # Initialize services
    ocr_service = OCRService()
    parser = ReceiptParser()

    # Process each receipt file
    success_count = 0
    skip_count = 0
    error_count = 0

    for receipt_path in sorted(receipt_files):
        result = generate_json_for_pdf(
            receipt_path, ocr_service, parser, overwrite=args.overwrite
        )
        if result:
            success_count += 1
        elif not args.overwrite:
            skip_count += 1
        else:
            error_count += 1

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"\nTotal receipt files processed: {len(receipt_files)}")
    print(f"  ✓ JSON files created: {success_count}")
    if skip_count > 0:
        print(f"  ⏭️  Skipped (JSON exists): {skip_count}")
    if error_count > 0:
        print(f"  ✗ Errors: {error_count}")

    print(f"\n{'='*80}")
    print("NEXT STEPS")
    print(f"{'='*80}")
    print("\n1. Review each generated JSON file")
    print("2. Correct any extraction errors")
    print("3. Update 'notes' field with description")
    print("4. Run: python3 tests/test_parser_bulk.py")
    print(f"\n{'='*80}\n")


if __name__ == '__main__':
    main()
