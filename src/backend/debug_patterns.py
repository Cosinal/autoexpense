#!/usr/bin/env python3
"""Debug Pattern Matching Issues - Phase 1 Analysis"""

import sys
import os
import re
import json
sys.path.insert(0, os.path.dirname(__file__))

from app.services.ocr import OCRService
from pathlib import Path


def load_receipt(receipt_name):
    """Load PDF and extract OCR text."""
    pdf_path = Path(f'tests/data/receipts/failed/{receipt_name}.pdf')
    json_path = Path(f'tests/data/receipts/failed/{receipt_name}.json')

    with open(pdf_path, 'rb') as f:
        file_data = f.read()

    ocr = OCRService()
    text = ocr.extract_text_from_file(file_data, 'application/pdf', pdf_path.name)

    expected = {}
    if json_path.exists():
        with open(json_path) as f:
            expected = json.load(f)

    return text, expected


def search_context(text, search_term, context_lines=3):
    """Search for term and show context."""
    lines = text.split('\n')
    results = []

    for i, line in enumerate(lines):
        if search_term.lower() in line.lower():
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)
            results.append((i, start, end, lines[start:end]))

    return results


def test_pattern(pattern, text, flags=re.IGNORECASE):
    """Test pattern and return matches."""
    return list(re.finditer(pattern, text, flags))


# ============================================================================
# PATTERN 1: Air Canada - Harmonized Sales Tax
# ============================================================================
print("\n" + "="*80)
print("PATTERN 1: Air Canada - Harmonized Sales Tax")
print("="*80)

text, expected = load_receipt("Air_Canada_Booking_Confirmation_AOU65V")
print(f"\nExpected tax: {expected.get('tax')}")

print("\n--- Searching for 'harmonized sales tax' ---")
results = search_context(text, 'harmonized sales tax', context_lines=4)
for line_num, start, end, context in results:
    print(f"\nFound at line {line_num}:")
    for i, line in enumerate(context, start):
        marker = " >>> " if i == line_num else "     "
        print(f"{marker}Line {i}: {line}")

print("\n--- Searching for '2.65' ---")
results = search_context(text, '2.65', context_lines=2)
for line_num, start, end, context in results:
    print(f"\nFound at line {line_num}:")
    for i, line in enumerate(context, start):
        marker = " >>> " if i == line_num else "     "
        print(f"{marker}Line {i}: {line}")

print("\n--- Testing CURRENT pattern (single-line) ---")
pattern = r'harmonized\s+sales\s+tax[\s\-A-Za-z0-9]*?[\s:]+([\d,]+\.\d{2})'
matches = test_pattern(pattern, text)
print(f"Pattern: {pattern}")
print(f"Flags: re.IGNORECASE")
print(f"Matches: {len(matches)}")
for m in matches:
    print(f"  Full: '{m.group(0)}'")
    print(f"  Captured: '{m.group(1)}'")

print("\n--- Testing MULTI-LINE pattern (with \\s+ to match newlines) ---")
pattern_ml = r'harmonized\s+sales\s+tax[\s\-A-Za-z0-9]*[\s:]*([\d,]+\.\d{2})'
matches = test_pattern(pattern_ml, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
print(f"Pattern: {pattern_ml}")
print(f"Flags: re.IGNORECASE | re.MULTILINE | re.DOTALL")
print(f"Matches: {len(matches)}")
for m in matches:
    print(f"  Full: '{m.group(0)[:100]}'")
    print(f"  Captured: '{m.group(1)}'")


# ============================================================================
# PATTERN 2: Louis Vuitton - GST/HST Tax
# ============================================================================
print("\n\n" + "="*80)
print("PATTERN 2: Louis Vuitton - GST/HST Tax")
print("="*80)

text, expected = load_receipt("Receipt-2816-7512-1147 (1)")
print(f"\nExpected tax: {expected.get('tax')} (should be 19.75)")
print(f"Actual parsed: 29.50 (WRONG!)")

print("\n--- Searching for '19.75' ---")
results = search_context(text, '19.75', context_lines=2)
for line_num, start, end, context in results:
    print(f"\nFound at line {line_num}:")
    for i, line in enumerate(context, start):
        marker = " >>> " if i == line_num else "     "
        print(f"{marker}Line {i}: {line}")

print("\n--- Searching for '29.50' ---")
results = search_context(text, '29.50', context_lines=2)
for line_num, start, end, context in results:
    print(f"\nFound at line {line_num}:")
    for i, line in enumerate(context, start):
        marker = " >>> " if i == line_num else "     "
        print(f"{marker}Line {i}: {line}")

print("\n--- Searching for 'GST' or 'HST' ---")
results = search_context(text, 'gst', context_lines=1)
results += search_context(text, 'hst', context_lines=1)
for line_num, start, end, context in results:
    print(f"\nFound at line {line_num}:")
    for i, line in enumerate(context, start):
        marker = " >>> " if i == line_num else "     "
        print(f"{marker}Line {i}: {line}")

print("\n--- Testing CURRENT pattern ---")
pattern = r'(?:gst|hst)(?:\s+(?:rate|tax))?\s*\(?(\d{1,2}(?:\.\d{1,2})?)\s*%\)?[\s:]*(?:CA)?\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'
matches = test_pattern(pattern, text)
print(f"Pattern: {pattern}")
print(f"Matches: {len(matches)}")
for m in matches:
    print(f"  Full: '{m.group(0)}'")
    print(f"  Groups: {m.groups()}")
    print(f"  Tax amount (group 2): '{m.group(2)}'")


# ============================================================================
# PATTERN 3: Anthropic - Country Prefix Tax
# ============================================================================
print("\n\n" + "="*80)
print("PATTERN 3: Anthropic - Country Prefix Tax")
print("="*80)

text, expected = load_receipt("Customer_2024-07-15_150501645")
print(f"\nExpected tax: {expected.get('tax')} (should be 3.92)")

print("\n--- Searching for '3.92' ---")
results = search_context(text, '3.92', context_lines=2)
for line_num, start, end, context in results:
    print(f"\nFound at line {line_num}:")
    for i, line in enumerate(context, start):
        marker = " >>> " if i == line_num else "     "
        print(f"{marker}Line {i}: {line}")

print("\n--- Searching for 'HST' ---")
results = search_context(text, 'hst', context_lines=2)
for line_num, start, end, context in results:
    print(f"\nFound at line {line_num}:")
    for i, line in enumerate(context, start):
        marker = " >>> " if i == line_num else "     "
        print(f"{marker}Line {i}: {line}")

print("\n--- Testing CURRENT pattern ---")
pattern = r'(?:[A-Z\s]+\s+)?(?:gst|hst|pst)(?:/[A-Z]+)?\s*\([^\)]+\)[\s:]*(?:[A-Z]{2,3})?\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'
matches = test_pattern(pattern, text)
print(f"Pattern: {pattern}")
print(f"Matches: {len(matches)}")
for m in matches:
    print(f"  Full: '{m.group(0)}'")
    print(f"  Captured: '{m.group(1)}'")


# ============================================================================
# PATTERN 4: Anthropic - Date Paid
# ============================================================================
print("\n\n" + "="*80)
print("PATTERN 4: Anthropic - Date Paid")
print("="*80)

# Same receipt as pattern 3
print(f"\nExpected date: {expected.get('date')} (should be 2025-10-26)")

print("\n--- Searching for 'Date paid' ---")
results = search_context(text, 'date paid', context_lines=2)
for line_num, start, end, context in results:
    print(f"\nFound at line {line_num}:")
    for i, line in enumerate(context, start):
        marker = " >>> " if i == line_num else "     "
        print(f"{marker}Line {i}: {line}")

print("\n--- Searching for 'October' ---")
results = search_context(text, 'october', context_lines=1)
for line_num, start, end, context in results:
    print(f"\nFound at line {line_num}:")
    for i, line in enumerate(context, start):
        marker = " >>> " if i == line_num else "     "
        print(f"{marker}Line {i}: {line}")

print("\n--- Testing CURRENT pattern ---")
pattern = r'date\s+(?:paid|issued|of\s+issue)[\s:]*([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})'
matches = test_pattern(pattern, text)
print(f"Pattern: {pattern}")
print(f"Matches: {len(matches)}")
for m in matches:
    print(f"  Full: '{m.group(0)}'")
    print(f"  Captured: '{m.group(1)}'")


# ============================================================================
# PATTERN 5: Air Canada - Vendor Extraction
# ============================================================================
print("\n\n" + "="*80)
print("PATTERN 5: Air Canada - Vendor Extraction")
print("="*80)

text, expected = load_receipt("Air_Canada_Booking_Confirmation_AOU65V")
print(f"\nExpected vendor: {expected.get('vendor')} (should be 'Air Canada')")
print(f"Actual parsed: 'And Applicable Tariffsopens' (WRONG!)")

print("\n--- Searching for 'Air Canada' ---")
results = search_context(text, 'air canada', context_lines=2)
for line_num, start, end, context in results:
    print(f"\nFound at line {line_num}:")
    for i, line in enumerate(context, start):
        marker = " >>> " if i == line_num else "     "
        print(f"{marker}Line {i}: {line}")

print("\n--- Searching for 'Tariffsopens' ---")
results = search_context(text, 'tariffsopens', context_lines=2)
for line_num, start, end, context in results:
    print(f"\nFound at line {line_num}:")
    for i, line in enumerate(context, start):
        marker = " >>> " if i == line_num else "     "
        print(f"{marker}Line {i}: {line}")

print("\n--- First 10 lines of OCR ---")
lines = text.split('\n')
for i in range(min(10, len(lines))):
    print(f"Line {i}: {lines[i]}")


# ============================================================================
# PATTERN 6: Apple Store - Vendor Extraction
# ============================================================================
print("\n\n" + "="*80)
print("PATTERN 6: Apple Store - Vendor Extraction")
print("="*80)

text, expected = load_receipt("Shaw, Jorden Contacts Invoice")
print(f"\nExpected vendor: {expected.get('vendor')} (should be 'Apple Store')")
print(f"Actual parsed: 'Patrick Cusack' (WRONG!)")

print("\n--- Searching for 'Apple' ---")
results = search_context(text, 'apple', context_lines=2)
for line_num, start, end, context in results:
    print(f"\nFound at line {line_num}:")
    for i, line in enumerate(context, start):
        marker = " >>> " if i == line_num else "     "
        print(f"{marker}Line {i}: {line}")

print("\n--- Searching for 'Patrick Cusack' ---")
results = search_context(text, 'patrick cusack', context_lines=2)
for line_num, start, end, context in results:
    print(f"\nFound at line {line_num}:")
    for i, line in enumerate(context, start):
        marker = " >>> " if i == line_num else "     "
        print(f"{marker}Line {i}: {line}")

print("\n--- First 10 lines of OCR ---")
lines = text.split('\n')
for i in range(min(10, len(lines))):
    print(f"Line {i}: {lines[i]}")


print("\n\n" + "="*80)
print("DEBUG COMPLETE")
print("="*80)
