#!/usr/bin/env python3
"""Debug Anthropic Receipt - Spaced OCR Issue"""

import sys
import os
import re
sys.path.insert(0, os.path.dirname(__file__))

from app.services.ocr import OCRService
from pathlib import Path

pdf_path = Path('tests/data/receipts/failed/Receipt-2816-7512-1147 (1).pdf')
with open(pdf_path, 'rb') as f:
    file_data = f.read()

ocr = OCRService()
text = ocr.extract_text_from_file(file_data, 'application/pdf', pdf_path.name)

print("="*80)
print("ANTHROPIC RECEIPT - SPACED OCR ANALYSIS")
print("="*80)

lines = text.split('\n')

print("\n--- KEY LINES ---")
print(f"Line 2 (Date paid): {lines[2]}")
print(f"Line 28 (HST Canada): {lines[28]}")
print(f"Line 29 (Total): {lines[29]}")

print("\n--- TESTING PATTERNS ON SPACED TEXT ---")

# Test date pattern on spaced text
date_pattern = r'D\s*a\s*t\s*e\s+p\s*a\s*i\s*d\s+(.*?)$'
match = re.search(date_pattern, lines[2], re.IGNORECASE)
if match:
    print(f"\nDate pattern MATCHED:")
    print(f"  Pattern: {date_pattern}")
    print(f"  Captured: '{match.group(1)}'")

    # The captured text is "O c t o b e r  2 6 ,  2 0 2 5"
    # Need to extract the actual date
    spaced_date = match.group(1)
    print(f"  Spaced date: '{spaced_date}'")

    # Remove spaces to get "October26,2025"
    unspaced = spaced_date.replace(' ', '')
    print(f"  Unspaced: '{unspaced}'")
else:
    print(f"\nDate pattern FAILED")

# Test HST pattern on spaced text
hst_pattern = r'H\s*S\s*T.*?C\s*A\s*\$\s*([\d\s\.]+)'
match = re.search(hst_pattern, lines[28], re.IGNORECASE)
if match:
    print(f"\nHST pattern MATCHED:")
    print(f"  Pattern: {hst_pattern}")
    print(f"  Captured: '{match.group(1)}'")

    # Remove spaces
    tax_amount = match.group(1).replace(' ', '')
    print(f"  Tax amount (unspaced): '{tax_amount}'")
else:
    print(f"\nHST pattern FAILED")

print("\n--- TESTING SIMPLER APPROACH: Remove all spaces first ---")
# Collapse multi-space sequences to single space
normalized_text = re.sub(r'\s{2,}', ' ', text)
print(f"Original length: {len(text)}")
print(f"Normalized length: {len(normalized_text)}")

# Show sample lines after normalization
norm_lines = normalized_text.split('\n')
print(f"\nNumber of normalized lines: {len(norm_lines)}")
if len(norm_lines) > 2:
    print(f"Normalized line 2: {norm_lines[2]}")
if len(norm_lines) > 28:
    print(f"Normalized line 28: {norm_lines[28]}")

# Test patterns on normalized text
date_pattern_norm = r'Date\s+paid\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})'
match = re.search(date_pattern_norm, normalized_text, re.IGNORECASE)
if match:
    print(f"\nDate pattern on NORMALIZED text: MATCHED")
    print(f"  Captured: '{match.group(1)}'")

hst_pattern_norm = r'HST.*?CA\$\s*([\d,]+\.?\d{0,2})'
match = re.search(hst_pattern_norm, normalized_text, re.IGNORECASE)
if match:
    print(f"\nHST pattern on NORMALIZED text: MATCHED")
    print(f"  Captured: '{match.group(1)}'")
