#!/usr/bin/env python3
"""
Extract text from PDF files using OCR for analysis.
"""

import sys
sys.path.insert(0, '/Users/jordanshaw/Desktop/expense-reporting/backend')

from app.services.ocr import OCRService

def extract_pdf_text(pdf_path: str, output_path: str):
    """Extract text from a PDF file using OCR."""
    print(f"\n{'='*80}")
    print(f"Extracting text from: {pdf_path}")
    print(f"{'='*80}")

    ocr = OCRService()

    # Read the PDF file
    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()

    text = ocr.extract_text_from_pdf(pdf_data)

    # Save to output file
    with open(output_path, 'w') as f:
        f.write(text)

    print(f"\n✓ Text extracted successfully")
    print(f"  Length: {len(text)} characters")
    print(f"  Saved to: {output_path}")
    print(f"\nFirst 500 characters:")
    print("-" * 80)
    print(text[:500])
    print("-" * 80)

    return text

if __name__ == "__main__":
    # Extract PSA Canada PDF
    extract_pdf_text(
        "/Users/jordanshaw/Desktop/expense-reporting/backend/failed_receipts/PSA_Canada.pdf",
        "/Users/jordanshaw/Desktop/expense-reporting/backend/failed_receipts/PSA_Canada.txt"
    )

    # Extract GeoGuessr PDF
    extract_pdf_text(
        "/Users/jordanshaw/Desktop/expense-reporting/backend/failed_receipts/GeoGuessr.pdf",
        "/Users/jordanshaw/Desktop/expense-reporting/backend/failed_receipts/GeoGuessr.txt"
    )
