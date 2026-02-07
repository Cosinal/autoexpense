#!/usr/bin/env python3
"""Debug LinkedIn tax extraction in full processing."""

import sys
sys.path.insert(0, '/Users/jordanshaw/Desktop/expense-reporting/src/backend')

from app.services.ocr import OCRService
from app.services.parser import ReceiptParser
import re
from decimal import Decimal

# Extract text from LinkedIn receipt
ocr = OCRService()
with open('/tmp/linkedin_receipt.pdf', 'rb') as f:
    pdf_data = f.read()
text = ocr.extract_text_from_pdf(pdf_data)

print("="*60)
print("Testing Tax Extraction Step by Step")
print("="*60)

parser = ReceiptParser()

# Manually test each pattern
taxes = []
for i, pattern in enumerate(parser.tax_patterns):
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        print(f"\nPattern {i+1} matched: {pattern[:60]}...")
        print(f"  Raw matches: {matches}")

        for match in matches:
            # Handle tuple results from patterns with multiple groups
            if isinstance(match, tuple):
                print(f"  Tuple match: {match}")
                match = match[-1]  # Take last group (the amount)
                print(f"  After taking last group: {match}")

            tax_str = match.replace(',', '').replace('$', '').strip()
            print(f"  Cleaned tax string: '{tax_str}'")

            try:
                tax = Decimal(tax_str)
                if tax > 0:
                    taxes.append(tax)
                    print(f"  ✓ Added tax: ${tax}")
            except Exception as e:
                print(f"  ✗ Error: {e}")

print(f"\n{'='*60}")
print(f"Total taxes found: {taxes}")
print(f"Sum: ${sum(taxes) if taxes else 'None'}")
print(f"{'='*60}")

# Now test with the actual parser method
print("\nTesting parser.extract_tax()...")
tax_result = parser.extract_tax(text)
print(f"Result: ${tax_result}")
