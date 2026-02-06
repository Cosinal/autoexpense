"""
Detailed analysis of parser issues and proposed solutions.
"""

import re
from decimal import Decimal

# Sample text from Uber receipt
uber_text = """HST| $1.09"""

# Sample amounts from Air Canada PDF
air_canada_amounts = [
    "$126.07",  # Actual total
    "$75,000",  # Incorrectly extracted (likely from text like "$75,000" for baggage limits)
]

print("="*80)
print("ISSUE #1: UBER RECEIPT - HST TAX NOT EXTRACTED")
print("="*80)
print(f"\nActual line in receipt: '{uber_text}'")
print("\nCurrent tax patterns:")

current_patterns = [
    r'vat[\s:()%\d]*[$€£¥]?\s+(\d{1,3}(?:,\d{3})*\.\d{2})',
    r'tax[\s:]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
    r'(?:sales tax|hst|gst)[\s:()%]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
]

for i, pattern in enumerate(current_patterns, 1):
    match = re.search(pattern, uber_text, re.IGNORECASE)
    print(f"\n  Pattern {i}:")
    print(f"    Regex: {pattern}")
    print(f"    Match: {match.group(1) if match else 'NO MATCH'}")

print("\n" + "-"*80)
print("PROBLEM: Current patterns expect ':' or whitespace after HST/tax keyword,")
print("         but the Uber receipt uses a PIPE character '|' as separator")
print("-"*80)

print("\nProposed new pattern:")
new_pattern = r'(?:hst|gst|tax|vat)\s*\|\s*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'
match = re.search(new_pattern, uber_text, re.IGNORECASE)
print(f"  Regex: {new_pattern}")
print(f"  Match: {match.group(1) if match else 'NO MATCH'}")
print(f"  ✓ SUCCESS! Extracts: ${match.group(1)}")

print("\n" + "="*80)
print("ISSUE #2: AIR CANADA PDF - WRONG AMOUNT EXTRACTED ($75,000 vs $126.07)")
print("="*80)

# Simulate full Air Canada text
air_canada_sample = """
Booking Reference: AOU65V
Amount paid: $126.07
Total before options (per passenger)$12607
GRAND TOTAL (Canadian dollars)49,700 pts
$12607

Baggage allowance: $75,000 maximum liability
"""

print("\nSample text from Air Canada PDF:")
print(air_canada_sample)

print("\nCurrent amount extraction:")
amount_patterns = [
    r'[$€£¥]\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
    r'€\s+(\d{1,3}(?:,\d{3})*\.\d{2})',
    r'(?:total|amount|sum|paid)[\s:]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
    r'(\d{1,3}(?:,\d{3})*\.\d{2})\s*$',
]

all_amounts = []
for pattern in amount_patterns:
    matches = re.findall(pattern, air_canada_sample, re.IGNORECASE | re.MULTILINE)
    for match in matches:
        amount_str = match.replace(',', '').replace('$', '').strip()
        try:
            amount = Decimal(amount_str)
            if amount > 0:
                all_amounts.append(amount)
        except:
            pass

print(f"  All amounts found: {sorted(set(all_amounts))}")
print(f"  Max amount (currently extracted): ${max(all_amounts)}")
print(f"  ✗ PROBLEM: $75,000 is extracted, but it's from 'baggage liability' text")

print("\n" + "-"*80)
print("PROBLEM ANALYSIS:")
print("-"*80)
print("1. Parser extracts ALL dollar amounts and returns the MAX")
print("2. Large amounts from non-price contexts (liability limits, insurance, etc.)")
print("   get incorrectly extracted as the total")
print("3. Need to prioritize context-aware patterns over generic dollar amounts")

print("\n" + "-"*80)
print("PROPOSED SOLUTIONS:")
print("-"*80)
print("\n1. PRIORITIZE CONTEXT-SPECIFIC PATTERNS:")
print("   - Look for 'Total', 'Amount paid', 'Grand total' FIRST")
print("   - Only fall back to generic $ amounts if no context found")
print("")
print("2. ADD SANITY CHECKS:")
print("   - Flag amounts > $10,000 for manual review")
print("   - Exclude amounts near common limit values ($75k, $100k)")
print("")
print("3. IMPROVE CONTEXT PATTERNS:")

improved_amount_patterns = [
    # Highest priority - explicit payment/total lines
    r'(?:amount\s+paid|total\s+paid|grand\s+total|final\s+total)[\s:]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
    # High priority - total/amount with context
    r'(?:total|amount|sum)[\s:]+[$€£¥]\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
    # Medium priority - currency symbol with amount
    r'[$€£¥]\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
]

print("\n   Priority 1 - Explicit payment terms:")
for pattern in improved_amount_patterns[:1]:
    matches = re.findall(pattern, air_canada_sample, re.IGNORECASE)
    print(f"     Pattern: {pattern[:60]}...")
    print(f"     Matches: {matches}")

print("\n4. EXTRACT BOTH PRE-TAX AND POST-TAX AMOUNTS:")
print("   - Store 'subtotal' separately from 'total'")
print("   - Can validate: subtotal + tax ≈ total")

print("\n" + "="*80)
print("RECOMMENDED PARSER IMPROVEMENTS")
print("="*80)

improvements = """
1. TAX EXTRACTION IMPROVEMENTS:
   ✓ Add pattern for pipe separator: HST| $1.09
   ✓ Add pattern for HST/GST without colon
   ✓ Test patterns: HST $1.09, GST| $2.50, Tax| $5.00

2. AMOUNT EXTRACTION IMPROVEMENTS:
   ✓ Use priority-based pattern matching (highest to lowest confidence)
   ✓ Add maximum amount sanity check (flag if > $10,000)
   ✓ Exclude amounts from known non-price contexts:
     - "liability", "coverage", "insurance", "limit"
   ✓ Return confidence score with amount

3. ADDITIONAL DATA FIELDS:
   ✓ Extract subtotal (pre-tax amount)
   ✓ Extract tax amount (already exists but needs pattern fixes)
   ✓ Validate: subtotal + tax ≈ total (within $0.02 tolerance)
   ✓ Flag receipts where validation fails for manual review

4. PATTERN TESTING:
   ✓ Add unit tests for common receipt formats:
     - Email receipts (Uber, Lyft, DoorDash)
     - PDF receipts (Airlines, hotels)
     - Image receipts (retail stores)

5. CONTEXT-AWARE FILTERING:
   ✓ Ignore amounts in footer/legal text
   ✓ Ignore amounts > 5x median amount in receipt
   ✓ Prefer amounts near dates/vendor names
"""

print(improvements)

print("\n" + "="*80)
print("SPECIFIC REGEX PATTERNS TO ADD")
print("="*80)

new_tax_patterns = [
    # Existing patterns...
    r'vat[\s:()%\d]*[$€£¥]?\s+(\d{1,3}(?:,\d{3})*\.\d{2})',
    r'tax[\s:]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
    r'(?:sales tax|hst|gst)[\s:()%]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
    # NEW patterns for pipe separator and other formats
    r'(?:hst|gst|tax|vat)\s*\|\s*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
    r'(?:hst|gst)\s+[$€£¥]\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
]

print("\nNew tax_patterns list:")
for i, pattern in enumerate(new_tax_patterns, 1):
    print(f"  {i}. {pattern}")

new_amount_patterns = [
    # Priority 1: Explicit total/payment indicators
    r'(?:amount\s+paid|total\s+paid|grand\s+total|final\s+total)[\s:]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
    # Priority 2: Total with strong context
    r'total[\s:]+[$€£¥]\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
    # Priority 3: Generic total/amount
    r'(?:total|amount|sum|paid)[\s:]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
    # Priority 4: Currency symbol (last resort)
    r'[$€£¥]\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
]

print("\nImproved amount_patterns list (priority order):")
for i, pattern in enumerate(new_amount_patterns, 1):
    print(f"  {i}. [Priority {i}] {pattern}")

print("\n" + "="*80)
print("IMPLEMENTATION STRATEGY")
print("="*80)

strategy = """
1. Update parser.py with new patterns
   - Add new tax patterns for pipe separator
   - Reorder amount patterns by priority
   - Add amount validation logic

2. Add new parser methods:
   - extract_subtotal() - get pre-tax amount
   - validate_amounts() - check subtotal + tax ≈ total
   - get_confidence_details() - explain what was/wasn't found

3. Add sanity checks:
   - Flag amounts > $10,000 with low confidence
   - Exclude amounts from blacklisted contexts
   - Return extraction confidence with detailed reasoning

4. Testing:
   - Create test_parser.py with unit tests
   - Test against known receipts (Uber, Air Canada, etc.)
   - Validate accuracy improvements

5. Database schema updates (optional):
   - Add 'subtotal' field to receipts table
   - Add 'extraction_confidence' field
   - Add 'needs_review' boolean flag
"""

print(strategy)
