# Receipt Parser Failure Analysis

## Executive Summary

Analyzed 5 failed receipts to identify specific parser pattern deficiencies. This document provides detailed analysis of each failure, the actual text patterns present, and specific regex improvements needed.

---

## 1. SEPHORA (email_19c33910.txt)

### Issue Summary
- **Extracted**: $59.52 ✓, NO TAX ✗
- **Actual**: Total $59.52 ✓, HST $2.62 + GST $4.70 = $7.32 total tax
- **Problem**: Parser missed MULTIPLE tax lines with different labels (GST and HST)

### Actual Text Analysis
```
| Subtotal: $52.20
---
CANADA GST/TPS (5%): $2.62
NOVA SCOTIA HST (9%): $4.70
**Total: $59.52**
```

### Why Tax Extraction Failed
1. **Multiple tax lines**: Receipt has BOTH GST and HST
2. **Label format**: `CANADA GST/TPS (5%): $2.62` - includes country prefix and percentage
3. **Current parser**: Only captures ONE tax amount, not multiple
4. **No summation logic**: Parser returns first match, doesn't sum multiple taxes

### Required Fixes

#### Pattern Improvements Needed
```python
# Add pattern for "COUNTRY TAX_TYPE" format
r'(?:canada\s+)?(?:gst|hst)(?:/[a-z]+)?\s*\([^\)]+\):\s*\$?\s*(\d+\.\d{2})'
# Matches: "CANADA GST/TPS (5%): $2.62" or "NOVA SCOTIA HST (9%): $4.70"
```

#### Logic Change Required
**CRITICAL**: Change `extract_tax()` to:
1. Find ALL tax matches (not just first one)
2. Sum multiple tax amounts
3. Return total tax paid

### Priority: HIGH
Multiple tax jurisdictions are common in Canada (GST+HST, GST+PST, etc.)

---

## 2. URBAN OUTFITTERS (email_19c33917.txt)

### Issue Summary
- **Extracted**: $54.00 ✗ (WRONG - got subtotal)
- **Actual**: Total $93.79, Tax $10.79
- **Problem**: Parser extracted ITEM PRICE instead of ORDER TOTAL

### Actual Text Analysis
```
#### Out From Under Bec Low-Rise Micro Mini Skort
---
Style No. 82587676
Color: Washed Black
Size: XS
C$ 54.00          <-- Parser incorrectly grabbed this
|  1  |  C$ 54.00

[... more items ...]

## Order Summary
---
Subtotal: | C$83.00
Shipping: | C$0.00
Tax: | C$10.79
Return Fee: | C$0
Total: | C$93.79    <-- Should have grabbed this
```

### Why Amount Extraction Failed
1. **First currency match wins**: Parser found `C$ 54.00` (item price) before the total
2. **Weak "Total" pattern**: Pattern should prioritize "Order Summary" section
3. **Missing context**: No pattern for `Total: | C$93.79` format (with pipe separator)

### Required Fixes

#### Pattern Improvements Needed
```python
# Priority 1: Order summary total with pipe
(1, r'(?:order\s+summary|payment\s+summary)[\s\S]{0,200}?total:\s*\|\s*[A-Z]{0,2}\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),

# Priority 1: Total with pipe separator and currency code
(1, r'total:\s*\|\s*([A-Z]{2,3})\$\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),

# Priority 2: Standalone Total line (existing pattern needs higher priority)
```

#### Tax Pattern for Pipe Format
```python
# Add pattern for "Tax: | $10.79"
r'tax:\s*\|\s*[A-Z]{0,2}\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'
```

### Priority: CRITICAL
Getting wrong amount is worse than getting no amount. This breaks expense tracking completely.

---

## 3. FLIGHTHUB (email_19c3391e.txt)

### Issue Summary
- **Extracted**: $2,290.97 (Nov 6 2022), Date Jan 13 2023
- **Actual**: TWO receipts - $2,290.97 (Nov 6 2022) AND $1.90 (Jan 13 2023)
- **Problem**: Multiple receipts in one email, only found first one

### Actual Text Analysis
```
## RECEIPTS

|  |
---
|  RECEIPT NUMBER #218086592  |  Paid: November 6, 2022
---|---
| Passenger(s) | Item | Amount
---|---|---
**Ruby May Brubaker Plitt** |  Air Transportation Charges  |  $2,081.21
**Ruby May Brubaker Plitt** |  Taxes & Fees  |  $209.76
|  **Payment method: MASTERCARD ****3955** |  **Total: $2,290.97 CAD**

|  RECEIPT NUMBER #221738781  |  Paid: January 13, 2023
---|---
| Passenger(s) | Item | Amount
---|---|---
**Ruby May Brubaker Plitt** |  Air Transportation Charges  |  $1.90
|  **Payment method: MASTERCARD ****3955** |  **Total: $1.90 CAD**
```

### Why Parser Failed
1. **Single-receipt assumption**: Parser returns ONE result, not multiple
2. **Date mismatch**: Extracted date from second receipt but amount from first
3. **No receipt boundary detection**: No logic to detect "RECEIPT NUMBER" headers

### Architecture Decision Required

**Option A: Split into multiple receipts** (RECOMMENDED)
- Detect "RECEIPT NUMBER" pattern
- Split text into separate receipt sections
- Create separate database entries for each
- Pro: Accurate, matches user expectation
- Con: More complex implementation

**Option B: Combine receipts**
- Sum all totals: $2,290.97 + $1.90 = $2,292.87
- Use latest date: Jan 13 2023
- Pro: Simple, one database entry
- Con: Loses detail, harder to reconcile

**Recommendation**: Option A - Split into multiple receipts

### Implementation Approach
```python
def split_multi_receipts(text: str) -> List[str]:
    """Split email containing multiple receipts."""
    # Look for "RECEIPT NUMBER #" pattern
    receipt_pattern = r'RECEIPT NUMBER #\d+'
    matches = list(re.finditer(receipt_pattern, text))

    if len(matches) <= 1:
        return [text]  # Single receipt

    # Split text at each receipt boundary
    receipts = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        receipts.append(text[start:end])

    return receipts
```

### Priority: MEDIUM-HIGH
Multi-receipt emails are less common but cause significant data loss when they occur.

---

## 4. PSA CANADA (PDF)

### Issue Summary
- **Extracted**: Vendor "Invoice Collectors Universe Canada Invoice", Amount $134.95 (WRONG), Tax $18.89 ✓
- **Actual**: Vendor should be "PSA Canada" or "PSA", Amount $153.84 (got subtotal), Tax $18.89 ✓
- **Problems**:
  1. Vendor name garbled (extracted too much text)
  2. Got SUBTOTAL not TOTAL

### Actual Text Analysis
```
INVOICE
Collectors Universe Canada Invoice  #: 13609    <-- Too much vendor text
1658 Bedford Hwy  Unit #200 Date: Jan 6th 2026
Bedford, NS   B4A 2X9
psacanada@collectors.com PSA Submission #: 13619356

[...]

Service Level Quanity Price Total
TCG 5 26.99 $134.95                <-- Parser got this (subtotal)
Shipping 0 65.00 $0.00
Shipping Additional 0 1.50 $0.00
Payment Options Total SUBTOTAL $134.95
TAX RATE 0.14
Option #1:  E-Transfer, Wire Transfer $153.84 SALES TAX $18.89    <-- Should get $153.84
Option #2: Credit Card (+ 3% Admin Fee) $158.46 TOTAL CAD $ $153.84
```

### Why Vendor Extraction Failed
1. **Second line problem**: Vendor is on line 2, but "Collectors Universe Canada Invoice" is too verbose
2. **Email domain hint**: `psacanada@collectors.com` suggests vendor is "PSA"
3. **No PSA detection**: "PSA Submission #" appears but vendor parser doesn't use it

### Why Amount Extraction Failed
1. **First amount wins**: Parser grabbed first `$134.95` without checking for "SUBTOTAL" label
2. **Missing "TOTAL CAD $" pattern**: Format is `TOTAL CAD $ $153.84` (unusual)
3. **Blacklist ineffective**: Should skip amounts preceded by "SUBTOTAL"

### Required Fixes

#### Vendor Pattern Improvements
```python
# Check for email domain hints first (before line-by-line scan)
email_match = re.search(r'(\w+)@', text[:500])  # First 500 chars
if email_match:
    domain_prefix = email_match.group(1)
    # psacanada -> PSA Canada
    if 'psa' in domain_prefix.lower():
        return 'PSA Canada'

# Also check for "PSA Submission #" or "PSA Invoice"
psa_pattern = r'\bPSA\s+(?:Submission|Invoice|Canada)\b'
if re.search(psa_pattern, text[:500]):
    return 'PSA Canada'
```

#### Amount Pattern Improvements
```python
# Add pattern for "TOTAL CAD $" format
(1, r'total\s+cad\s+\$\s*\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),

# Improve subtotal blacklist check
# Change from checking context window to checking PRECEDING text only
# In extract_amount(), check if amount is preceded by "SUBTOTAL" keyword
```

### Priority: HIGH
- Vendor name issue is cosmetic but confusing
- Wrong amount is critical error

---

## 5. GEOGUESSR (PDF)

### Issue Summary
- **Extracted**: Vendor "Market Ltd", Amount $6.99 ✓, Tax MISSING, Date MISSING
- **Actual**: Vendor "GeoGuessr" or "Paddle.net", Amount $6.99 ✓, Tax $0.33, Date Nov 23 2025
- **Problems**:
  1. Wrong vendor (extracted payment processor not actual merchant)
  2. Missing tax
  3. Missing date

### Actual Text Analysis
```
Tax invoice
PAID
23rd November 2025 -     <-- Date present but not extracted
CA$6.99
via Paddle.com
Invoice to
Jorden Shaw
Invoice from
Paddle.com Market Ltd    <-- Parser grabbed this (payment processor)
[...]
Invoice details
Invoice reference: 184-324336
Billing period: 23rd November 2025 - 23rd December 2025

Transaction
Product
Qty
Unit price
Tax rate
Amount
GeoGuessr Unlimited      <-- Actual vendor (product name)
23rd November 2025 - 23rd December 2025
1
CA$6.66
5%
CA$6.66
Subtotal
CA$6.66
Sales Tax
CA$0.33              <-- Tax present but not extracted
Total
CA$6.99
[...]
PADDLE.NET* GEOGUESSR    <-- Alternative vendor identification
```

### Why Vendor Extraction Failed
1. **Payment processor confusion**: Parser found "Paddle.com Market Ltd" (payment processor) instead of "GeoGuessr" (actual merchant)
2. **Product name context**: Real vendor is in "Product" column as "GeoGuessr Unlimited"
3. **Missing Paddle.net detection**: Footer shows `PADDLE.NET* GEOGUESSR` but parser doesn't check there

### Why Tax Extraction Failed
1. **Line break issue**: Format is:
   ```
   Sales Tax
   CA$0.33
   ```
   Tax amount on separate line from label
2. **Current patterns**: Expect "Tax: $0.33" format (label and amount on same line)

### Why Date Extraction Failed
1. **"rd" suffix**: Date is "23rd November 2025" not "23 November 2025"
2. **Dash separator**: `23rd November 2025 - ` has trailing dash
3. **Current patterns**: Don't handle ordinal suffixes (1st, 2nd, 3rd, 23rd)

### Required Fixes

#### Vendor Pattern Improvements
```python
# Priority 1: Check for "Product" line with company name
product_pattern = r'(?:Product|Description)\s*\n\s*([A-Z][a-zA-Z\s]{3,30}?)(?:\s+Unlimited|\s+Subscription|\s+Pro|\n)'
# Matches: "Product\nGeoGuessr Unlimited" -> extracts "GeoGuessr"

# Priority 2: Check statement line
statement_pattern = r'(?:statement|bank|card)\s+as:\s*([A-Z][A-Z\s\.\*]+)'
# Matches: "PADDLE.NET* GEOGUESSR" -> extracts company

# Priority 3: Known payment processors - extract actual merchant
payment_processors = {
    'paddle.com market ltd': lambda text: extract_paddle_merchant(text),
    'stripe': lambda text: extract_stripe_merchant(text),
}
```

#### Tax Pattern Improvements
```python
# Add multi-line tax pattern (label on one line, amount on next)
r'(?:sales\s+tax|tax)\s*\n\s*([A-Z]{2,3})?\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'

# Also need to handle standalone "Sales Tax" label
r'sales\s+tax\s*\n[^\d]*(\d+\.\d{2})'
```

#### Date Pattern Improvements
```python
# Add ordinal suffix support
r'(\d{1,2}(?:st|nd|rd|th)\s+[A-Za-z]{3,9}\s+\d{4})'

# Parse format: "23rd November 2025"
formats = [
    '%dst %B %Y', '%dnd %B %Y', '%drd %B %Y', '%dth %B %Y',  # Won't work!
]

# Need custom parsing:
def parse_ordinal_date(date_str):
    # Remove ordinal suffix: "23rd November 2025" -> "23 November 2025"
    clean = re.sub(r'(\d+)(?:st|nd|rd|th)', r'\1', date_str)
    return datetime.strptime(clean, '%d %B %Y')
```

### Priority: HIGH
- Wrong vendor name is confusing
- Missing tax is significant for expense reporting
- Missing date is critical for chronological tracking

---

## SUMMARY: Priority-Ordered Fixes

### CRITICAL (Fix Immediately)
1. **Urban Outfitters - Wrong Amount**: Getting wrong amount breaks everything
   - Add "Order Summary" context patterns with high priority
   - Add pipe-separated total patterns
   - Ensure item prices don't override totals

### HIGH (Fix Soon)
2. **Sephora - Multiple Tax Support**: Very common in Canada
   - Modify `extract_tax()` to sum multiple tax lines
   - Add country-prefix tax patterns

3. **PSA Canada - Subtotal vs Total**: Common failure mode
   - Improve SUBTOTAL blacklist (check preceding text)
   - Add "TOTAL CAD $" pattern
   - Improve vendor extraction (email domain hints, PSA detection)

4. **GeoGuessr - Missing Tax/Date/Vendor**: Multiple issues
   - Multi-line tax patterns
   - Ordinal date support
   - Payment processor vs merchant detection

### MEDIUM (Architectural)
5. **Flighthub - Multi-Receipt Handling**: Less common but important
   - Implement receipt boundary detection
   - Split multi-receipt emails
   - Create separate database entries

---

## REGEX PATTERNS TO ADD

### Amount Patterns (Priority Order)
```python
# Priority 1: Order Summary Total with pipe
(1, r'(?:order\s+summary|payment\s+summary)[\s\S]{0,200}?total:\s*\|\s*[A-Z]{0,2}\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),

# Priority 1: Total with pipe and currency code
(1, r'total:\s*\|\s*([A-Z]{2,3})\$\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),

# Priority 1: TOTAL CAD $ format
(1, r'total\s+cad\s+\$\s*\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),
```

### Tax Patterns
```python
# Multi-line tax (label on one line, amount on next)
r'(?:sales\s+tax|tax)\s*\n\s*([A-Z]{2,3})?\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',

# Country-prefix tax (CANADA GST/TPS)
r'(?:[A-Z\s]+\s+)?(?:gst|hst|pst)(?:/[A-Z]+)?\s*\([^\)]+\):\s*\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',

# Tax with pipe separator
r'tax:\s*\|\s*[A-Z]{0,2}\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
```

### Date Patterns
```python
# Ordinal dates (1st, 2nd, 3rd, 23rd)
r'(\d{1,2}(?:st|nd|rd|th)\s+[A-Za-z]{3,9}\s+\d{4})',
```

### Vendor Patterns
```python
# Product line in invoice
r'(?:Product|Description)\s*\n\s*([A-Z][a-zA-Z\s]{3,30}?)(?:\s+(?:Unlimited|Subscription|Pro)|\n)',

# Statement line
r'(?:statement|bank|card)\s+as:\s*([A-Z][A-Z\s\.\*]+)',

# Email domain hint
r'(\w+)@[\w\.]+\.com',  # Extract prefix, e.g., "psacanada@" -> "PSA Canada"
```

---

## LOGIC CHANGES REQUIRED

### 1. Tax Extraction - Sum Multiple Taxes
```python
def extract_tax(self, text: str) -> Optional[Decimal]:
    """Extract tax amount, summing multiple tax lines if present."""
    taxes = []

    for pattern in self.tax_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                tax_str = match.replace(',', '').replace('$', '').strip()
                tax = Decimal(tax_str)
                if tax > 0:
                    taxes.append(tax)
            except (InvalidOperation, ValueError):
                continue

    # Return sum of all taxes found
    return sum(taxes) if taxes else None
```

### 2. Amount Extraction - Better Subtotal Filtering
```python
# In extract_amount(), improve context checking:
# Check PRECEDING text (before match) for "SUBTOTAL" keyword
# Get 100 chars BEFORE the match
preceding_text = text[max(0, match.start() - 100):match.start()].lower()
if 'subtotal' in preceding_text and 'grand' not in preceding_text:
    continue  # Skip this match
```

### 3. Multi-Receipt Detection
```python
def parse(self, text: str) -> List[Dict[str, Any]]:
    """Parse receipt text, returning multiple receipts if present."""
    # Check for multiple receipts
    receipt_texts = self._split_multi_receipts(text)

    if len(receipt_texts) > 1:
        print(f"Detected {len(receipt_texts)} receipts in one document")

    results = []
    for receipt_text in receipt_texts:
        result = self._parse_single_receipt(receipt_text)
        results.append(result)

    return results
```

### 4. Vendor Extraction - Payment Processor Detection
```python
PAYMENT_PROCESSORS = {
    'paddle.com market ltd': 'paddle',
    'paddle.com': 'paddle',
    'paddle': 'paddle',
    'stripe': 'stripe',
}

def extract_vendor(self, text: str) -> Optional[str]:
    # ... existing logic ...

    # If vendor is a payment processor, try to find real merchant
    if vendor and vendor.lower() in PAYMENT_PROCESSORS:
        real_merchant = self._extract_real_merchant(text)
        if real_merchant:
            return real_merchant

    return vendor

def _extract_real_merchant(self, text: str) -> Optional[str]:
    """Extract actual merchant when vendor is a payment processor."""
    # Check statement line
    statement_match = re.search(r'(?:statement|bank|card)\s+as:\s*([A-Z][A-Z\s\.\*]+)', text, re.IGNORECASE)
    if statement_match:
        # "PADDLE.NET* GEOGUESSR" -> "GeoGuessr"
        statement = statement_match.group(1)
        parts = statement.split('*')
        if len(parts) > 1:
            return parts[-1].strip().title()

    # Check product name
    product_match = re.search(r'(?:Product|Description)\s*\n\s*([A-Z][a-zA-Z\s]{3,30}?)(?:\s+(?:Unlimited|Subscription|Pro)|\n)', text)
    if product_match:
        return product_match.group(1).strip()

    return None
```

---

## TESTING RECOMMENDATIONS

### Regression Test Suite
Create test cases for all 5 failed receipts:

```python
def test_sephora_multi_tax():
    """Test Sephora receipt with GST + HST."""
    text = load_receipt('email_19c33910.txt')
    result = parser.parse(text)
    assert result['amount'] == Decimal('59.52')
    assert result['tax'] == Decimal('7.32')  # 2.62 + 4.70
    assert result['vendor'] == 'Sephora'

def test_urban_outfitters_order_summary():
    """Test Urban Outfitters order summary total."""
    text = load_receipt('email_19c33917.txt')
    result = parser.parse(text)
    assert result['amount'] == Decimal('93.79')  # NOT 54.00
    assert result['tax'] == Decimal('10.79')
    assert result['vendor'] == 'Urban Outfitters'

def test_flighthub_multi_receipt():
    """Test Flighthub email with 2 receipts."""
    text = load_receipt('email_19c3391e.txt')
    results = parser.parse(text)
    assert len(results) == 2
    assert results[0]['amount'] == Decimal('2290.97')
    assert results[0]['date'] == '2022-11-06'
    assert results[1]['amount'] == Decimal('1.90')
    assert results[1]['date'] == '2023-01-13'

def test_psa_canada_total_not_subtotal():
    """Test PSA Canada gets total not subtotal."""
    text = load_receipt('PSA_Canada.txt')
    result = parser.parse(text)
    assert result['amount'] == Decimal('153.84')  # NOT 134.95
    assert result['tax'] == Decimal('18.89')
    assert result['vendor'] in ['PSA', 'PSA Canada']

def test_geoguessr_paddle_merchant():
    """Test GeoGuessr with Paddle payment processor."""
    text = load_receipt('GeoGuessr.txt')
    result = parser.parse(text)
    assert result['amount'] == Decimal('6.99')
    assert result['tax'] == Decimal('0.33')
    assert result['vendor'] in ['GeoGuessr', 'Geoguessr']
    assert result['date'] == '2025-11-23'
```

---

## ESTIMATED IMPACT

### If All Fixes Implemented
- **Sephora**: Tax $0 → $7.32 ✓
- **Urban Outfitters**: Amount $54.00 → $93.79 ✓, Tax $0 → $10.79 ✓
- **Flighthub**: 1 receipt → 2 receipts ✓, Correct dates ✓
- **PSA Canada**: Amount $134.95 → $153.84 ✓, Vendor "Invoice..." → "PSA Canada" ✓
- **GeoGuessr**: Vendor "Market Ltd" → "GeoGuessr" ✓, Tax $0 → $0.33 ✓, Date added ✓

**Total improvement**: 5/5 receipts fixed (100%)

---

## IMPLEMENTATION ORDER

1. **Day 1**: Urban Outfitters fix (wrong amount - critical)
2. **Day 2**: Sephora multi-tax support
3. **Day 3**: PSA Canada subtotal vs total + vendor improvements
4. **Day 4**: GeoGuessr missing fields (tax, date, vendor)
5. **Day 5**: Flighthub multi-receipt architecture + testing

**Total time estimate**: 3-5 days for complete implementation and testing
