#!/usr/bin/env python3
"""Debug Pattern Matching Issues - Phase 1 Analysis - CORRECTED"""

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


# ============================================================================
# PATTERN 2: Louis Vuitton - GST/HST Tax (CORRECTED FILENAME)
# ============================================================================
print("\n" + "="*80)
print("PATTERN 2: Louis Vuitton - GST/HST Tax")
print("="*80)

text, expected = load_receipt("Customer_2024-07-15_150501645")
print(f"\nExpected tax: {expected.get('tax')}")
print(f"Expected vendor: {expected.get('vendor')}")

print("\n--- Searching for '19.75' ---")
results = search_context(text, '19.75', context_lines=3)
for line_num, start, end, context in results:
    print(f"\nFound at line {line_num}:")
    for i, line in enumerate(context, start):
        marker = " >>> " if i == line_num else "     "
        print(f"{marker}Line {i}: {line}")

print("\n--- Testing GST/HST pattern WITHOUT parentheses ---")
# The OCR shows: "5% GST/HST       19.75"
# Pattern needs to match GST/HST followed by amount
pattern = r'(?:gst|hst)(?:/[A-Z]+)?[\s:]*(\d{1,3}(?:,\d{3})*\.\d{2})'
matches = list(re.finditer(pattern, text, re.IGNORECASE))
print(f"Pattern: {pattern}")
print(f"Matches: {len(matches)}")
for m in matches:
    print(f"  Full: '{m.group(0)}'")
    print(f"  Tax amount: '{m.group(1)}'")


# ============================================================================
# PATTERN 3: Anthropic - Country Prefix Tax (CORRECTED FILENAME)
# ============================================================================
print("\n\n" + "="*80)
print("PATTERN 3: Anthropic - Country Prefix Tax")
print("="*80)

text, expected = load_receipt("Receipt-2816-7512-1147 (1)")
print(f"\nExpected tax: {expected.get('tax')}")
print(f"Expected vendor: {expected.get('vendor')}")

print("\n--- Searching for '3.92' ---")
results = search_context(text, '3.92', context_lines=3)
for line_num, start, end, context in results:
    print(f"\nFound at line {line_num}:")
    for i, line in enumerate(context, start):
        marker = " >>> " if i == line_num else "     "
        print(f"{marker}Line {i}: {line}")

print("\n--- Searching for 'HST' or 'Canada' ---")
results = search_context(text, 'hst', context_lines=2)
results += search_context(text, 'canada', context_lines=2)
for line_num, start, end, context in results[:3]:  # Limit to first 3
    print(f"\nFound at line {line_num}:")
    for i, line in enumerate(context, start):
        marker = " >>> " if i == line_num else "     "
        print(f"{marker}Line {i}: {line}")


# ============================================================================
# PATTERN 4: Anthropic - Date Paid (SAME FILE)
# ============================================================================
print("\n\n" + "="*80)
print("PATTERN 4: Anthropic - Date Paid")
print("="*80)

print(f"\nExpected date: {expected.get('date')}")

print("\n--- Searching for 'Date' ---")
results = search_context(text, 'date', context_lines=2)[:5]  # First 5
for line_num, start, end, context in results:
    print(f"\nFound at line {line_num}:")
    for i, line in enumerate(context, start):
        marker = " >>> " if i == line_num else "     "
        print(f"{marker}Line {i}: {line}")

print("\n--- Searching for 'October' ---")
results = search_context(text, 'october', context_lines=2)
for line_num, start, end, context in results:
    print(f"\nFound at line {line_num}:")
    for i, line in enumerate(context, start):
        marker = " >>> " if i == line_num else "     "
        print(f"{marker}Line {i}: {line}")

print("\n\n" + "="*80)
print("DEBUG COMPLETE")
print("="*80)
