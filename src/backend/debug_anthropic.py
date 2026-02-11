#!/usr/bin/env python3
"""Debug Anthropic Receipt - Full OCR"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.services.ocr import OCRService
from pathlib import Path

pdf_path = Path('tests/data/receipts/failed/Receipt-2816-7512-1147 (1).pdf')
with open(pdf_path, 'rb') as f:
    file_data = f.read()

ocr = OCRService()
text = ocr.extract_text_from_file(file_data, 'application/pdf', pdf_path.name)

print("="*80)
print("FULL OCR TEXT - Receipt-2816-7512-1147 (1).pdf")
print("="*80)
print(f"\nTotal characters: {len(text)}")
print("\nFull text with line numbers:")
print("-"*80)

lines = text.split('\n')
for i, line in enumerate(lines):
    print(f"{i:4d}: {line}")

print("\n" + "="*80)
print("SEARCHING FOR KEY TERMS")
print("="*80)

search_terms = ['3.92', 'HST', 'Canada', 'October', '2025', 'Date', 'paid', 'CA$', 'anthropic']

for term in search_terms:
    found = False
    for i, line in enumerate(lines):
        if term.lower() in line.lower():
            print(f"\n'{term}' found at line {i}: {line}")
            found = True
    if not found:
        print(f"\n'{term}' - NOT FOUND")
