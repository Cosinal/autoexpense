#!/usr/bin/env python3
"""Debug LinkedIn tax extraction."""

import sys
sys.path.insert(0, '/Users/jordanshaw/Desktop/expense-reporting/src/backend')

from app.services.ocr import OCRService
from app.services.parser import ReceiptParser

# Extract text from LinkedIn receipt
ocr = OCRService()
with open('/tmp/linkedin_receipt.pdf', 'rb') as f:
    pdf_data = f.read()
text = ocr.extract_text_from_pdf(pdf_data)

print("="*60)
print("LinkedIn Receipt Text")
print("="*60)
print(text)
print("\n" + "="*60)
print("Parser Results")
print("="*60)

# Parse the receipt
parser = ReceiptParser()
result = parser.parse(text)

print(f"Vendor: {result['vendor']}")
print(f"Amount: {result['amount']} {result['currency']}")
print(f"Tax: {result['tax']}")
print(f"Date: {result['date']}")

# Test tax extraction specifically
print("\n" + "="*60)
print("Testing Tax Patterns")
print("="*60)

import re
for pattern in parser.tax_patterns:
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        print(f"\nPattern matched: {pattern}")
        print(f"Matches: {matches}")
