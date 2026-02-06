# Visual Pattern Examples

This document shows the EXACT text patterns found in failed receipts and what regex patterns match them.

---

## 1. SEPHORA - Multiple Tax Lines

### What the Parser Sees:
```
| Subtotal: $52.20
---
CANADA GST/TPS (5%): $2.62      ← Tax line 1 (GST)
NOVA SCOTIA HST (9%): $4.70     ← Tax line 2 (HST)
**Total: $59.52**
```

### Current Pattern (FAILS):
```python
r'tax[\s:]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'
```
Matches: Nothing (no simple "tax:" label)

### New Pattern (WORKS):
```python
r'(?:[A-Z\s]+\s+)?(?:gst|hst|pst)(?:/[A-Z]+)?\s*\([^\)]+\):\s*\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'
```
Matches:
- `CANADA GST/TPS (5%): $2.62` → `2.62`
- `NOVA SCOTIA HST (9%): $4.70` → `4.70`

### Fix Required:
Sum both matches: `2.62 + 4.70 = 7.32`

---

## 2. URBAN OUTFITTERS - Order Summary Format

### What the Parser Sees:
```
#### Out From Under Bec Low-Rise Micro Mini Skort
Style No. 82587676
Color: Washed Black
Size: XS
C$ 54.00                        ← WRONG! (item price)
|  1  |  C$ 54.00

[... more items ...]

## Order Summary
---
Subtotal: | C$83.00
Shipping: | C$0.00
Tax: | C$10.79                  ← Tax (with pipe)
Return Fee: | C$0
Total: | C$93.79                ← CORRECT! (total)
```

### Current Pattern (FAILS):
```python
# Priority 3: Generic total/amount
(3, r'(?:total|amount|sum|paid)[\s:\|]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})')
```
Matches: `C$ 54.00` FIRST (item price wins because it appears earlier)

### New Patterns (WORK):
```python
# Priority 1: Order Summary context + Total with pipe
(1, r'(?:order\s+summary|payment\s+summary)[\s\S]{0,200}?total:\s*\|\s*[A-Z]{0,2}\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),

# Priority 1: Total with pipe and C$ currency
(1, r'total:\s*\|\s*C\$\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),
```
Matches: `Total: | C$93.79` → `93.79`

### Tax Pattern Needed:
```python
r'tax:\s*\|\s*[A-Z]{0,2}\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'
```
Matches: `Tax: | C$10.79` → `10.79`

---

## 3. FLIGHTHUB - Multiple Receipts

### What the Parser Sees:
```
## RECEIPTS

|  RECEIPT NUMBER #218086592  |  Paid: November 6, 2022    ← Receipt 1 header
---|---
| Passenger(s) | Item | Amount
---|---|---
**Ruby May Brubaker Plitt** |  Air Transportation Charges  |  $2,081.21
**Ruby May Brubaker Plitt** |  Taxes & Fees  |  $209.76
|  **Payment method: MASTERCARD ****3955** |  **Total: $2,290.97 CAD**    ← Receipt 1 total

|  RECEIPT NUMBER #221738781  |  Paid: January 13, 2023    ← Receipt 2 header
---|---
| Passenger(s) | Item | Amount
---|---|---
**Ruby May Brubaker Plitt** |  Air Transportation Charges  |  $1.90
|  **Payment method: MASTERCARD ****3955** |  **Total: $1.90 CAD**        ← Receipt 2 total
```

### Split Pattern:
```python
r'RECEIPT NUMBER #\d+'
```
Matches:
- Position 0: `RECEIPT NUMBER #218086592`
- Position 1: `RECEIPT NUMBER #221738781`

### Split Logic:
```python
def split_multi_receipts(text):
    matches = list(re.finditer(r'RECEIPT NUMBER #\d+', text))
    if len(matches) <= 1:
        return [text]

    receipts = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        receipts.append(text[start:end])

    return receipts
```

Result: 2 separate receipts to parse

---

## 4. PSA CANADA - Subtotal vs Total

### What the Parser Sees:
```
INVOICE
Collectors Universe Canada Invoice  #: 13609    ← Line 2 (too verbose for vendor)
1658 Bedford Hwy  Unit #200 Date: Jan 6th 2026
Bedford, NS   B4A 2X9
psacanada@collectors.com                        ← Email hint: "psa"
PSA Submission #: 13619356                      ← "PSA" keyword

[...]

Service Level Quanity Price Total
TCG 5 26.99 $134.95                             ← WRONG! (line item subtotal)
Shipping 0 65.00 $0.00
Shipping Additional 0 1.50 $0.00
Payment Options Total SUBTOTAL $134.95          ← Labeled "SUBTOTAL"
TAX RATE 0.14
Option #1:  E-Transfer, Wire Transfer $153.84 SALES TAX $18.89    ← Contains actual total
Option #2: Credit Card (+ 3% Admin Fee) $158.46 TOTAL CAD $ $153.84    ← CORRECT!
```

### Amount Pattern Needed:
```python
(1, r'total\s+cad\s+\$\s*\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})')
```
Matches: `TOTAL CAD $ $153.84` → `153.84`

### Subtotal Filter:
```python
# Check preceding text for "SUBTOTAL" label
preceding_text = text[max(0, match.start() - 100):match.start()].lower()
if 'subtotal' in preceding_text:
    continue  # Skip this match
```
Prevents: Matching `SUBTOTAL $134.95`

### Vendor Email Hint:
```python
email_match = re.search(r'([a-z]+)@[\w\.]+\.com', text[:500], re.IGNORECASE)
if email_match and 'psa' in email_match.group(1).lower():
    return 'PSA Canada'
```
Matches: `psacanada@collectors.com` → Vendor = "PSA Canada"

---

## 5. GEOGUESSR - Multi-Line Tax & Payment Processor

### What the Parser Sees:
```
Tax invoice
PAID
23rd November 2025 -                            ← Date (ordinal format)
CA$6.99
via Paddle.com
Invoice to
Jorden Shaw
Invoice from
Paddle.com Market Ltd                           ← WRONG vendor (payment processor)
Judd House 18-29 Mora Street
[...]

Transaction
Product
Qty
Unit price
Tax rate
Amount
GeoGuessr Unlimited                             ← CORRECT vendor (product name)
23rd November 2025 - 23rd December 2025
1
CA$6.66
5%
CA$6.66
Subtotal
CA$6.66
Sales Tax                                       ← Tax label (line 1)
CA$0.33                                         ← Tax amount (line 2)
Total
CA$6.99
[...]
PADDLE.NET* GEOGUESSR                          ← Statement line (alternative vendor)
```

### Multi-Line Tax Pattern:
```python
r'(?:sales\s+tax|tax\s+total)\s*\n\s*([A-Z]{2,3})?\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'
```
Matches:
```
Sales Tax
CA$0.33
```
→ `0.33`

### Ordinal Date Pattern:
```python
r'(\d{1,2}(?:st|nd|rd|th)\s+[A-Za-z]{3,9}\s+\d{4})'
```
Matches: `23rd November 2025` → `23rd November 2025`

Then parse:
```python
# Remove ordinal suffix
date_str = re.sub(r'(\d+)(?:st|nd|rd|th)', r'\1', date_str)
# "23rd November 2025" → "23 November 2025"
datetime.strptime(date_str, '%d %B %Y')  # Works!
```

### Product Name Vendor Pattern:
```python
r'(?:Product|Description)\s*\n\s*([A-Z][a-zA-Z\s]{2,30}?)(?:\s+(?:Unlimited|Subscription|Pro)|\n)'
```
Matches:
```
Product
GeoGuessr Unlimited
```
→ Vendor = "GeoGuessr"

### Statement Line Vendor Pattern:
```python
r'(?:statement|bank|card)\s+as:\s*([A-Z][A-Z\s\.\*]+)'
```
Matches: `PADDLE.NET* GEOGUESSR` → Extract "GEOGUESSR"

---

## PATTERN PRIORITY VISUALIZATION

### How Priority Works:

```
RECEIPT TEXT:
  C$ 54.00           ← Priority 4 pattern matches here
  ...
  Total: | C$93.79   ← Priority 1 pattern matches here
```

**Priority 1 patterns run first** and return immediately when found.
**Priority 4 patterns** only run if Priority 1-3 find nothing.

This is why adding high-priority patterns fixes the Urban Outfitters issue.

---

## CONTEXT WINDOW VISUALIZATION

### Current Implementation (BAD):
```python
context_window = text[match.start() - 50:match.end() + 50]
# Gets ±50 chars around the match
```

Example:
```
[... some text ...]  ITEM: Widget  Price: $134.95  Qty: 1
                                          ^^^^^^^^
                     [-----context window-----]
```

Problem: "ITEM" is far from the match, might miss it.

### Improved Implementation (GOOD):
```python
preceding_text = text[max(0, match.start() - 100):match.start()]
# Gets 100 chars BEFORE the match
```

Example:
```
SUBTOTAL $134.95  ← "SUBTOTAL" is in preceding text
         ^^^^^^^^
[----preceding----]
```

Much more reliable for detecting labels like "SUBTOTAL".

---

## PAYMENT PROCESSOR DETECTION FLOW

### Current (BAD):
```
Text: "Paddle.com Market Ltd"
       ↓
Vendor Extraction: "Paddle.com Market Ltd"  ← WRONG (payment processor)
       ↓
Result: Vendor = "Paddle.com Market Ltd"
```

### Improved (GOOD):
```
Text: "Paddle.com Market Ltd ... Product: GeoGuessr Unlimited ... PADDLE.NET* GEOGUESSR"
       ↓
Vendor Extraction: "Paddle.com Market Ltd"
       ↓
Check if payment processor: YES (in PAYMENT_PROCESSORS dict)
       ↓
Extract real merchant: Check statement line → "GEOGUESSR"
       ↓
Result: Vendor = "GeoGuessr"
```

---

## MULTI-TAX SUMMATION FLOW

### Current (BAD):
```
Text: "CANADA GST/TPS (5%): $2.62  NOVA SCOTIA HST (9%): $4.70"
       ↓
Tax Pattern Matches: ["2.62", "4.70"]
       ↓
Return: First match only → 2.62  ← WRONG (missing $4.70)
```

### Improved (GOOD):
```
Text: "CANADA GST/TPS (5%): $2.62  NOVA SCOTIA HST (9%): $4.70"
       ↓
Tax Pattern Matches: ["2.62", "4.70"]
       ↓
Collect all: taxes = [Decimal("2.62"), Decimal("4.70")]
       ↓
Sum: sum(taxes) = 7.32  ← CORRECT!
```

---

## REGEX TESTING EXAMPLES

You can test these patterns in Python:

```python
import re

# Test Sephora tax pattern
text = "CANADA GST/TPS (5%): $2.62"
pattern = r'(?:[A-Z\s]+\s+)?(?:gst|hst|pst)(?:/[A-Z]+)?\s*\([^\)]+\):\s*\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'
match = re.search(pattern, text, re.IGNORECASE)
print(match.group(1))  # Output: 2.62

# Test Urban Outfitters order summary
text = """## Order Summary
---
Subtotal: | C$83.00
Total: | C$93.79"""
pattern = r'(?:order\s+summary)[\s\S]{0,200}?total:\s*\|\s*[A-Z]{0,2}\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'
match = re.search(pattern, text, re.IGNORECASE)
print(match.group(1))  # Output: 93.79

# Test GeoGuessr multi-line tax
text = """Sales Tax
CA$0.33"""
pattern = r'(?:sales\s+tax)\s*\n\s*([A-Z]{2,3})?\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'
match = re.search(pattern, text, re.IGNORECASE)
print(match.group(2))  # Output: 0.33

# Test ordinal date
text = "23rd November 2025"
pattern = r'(\d{1,2}(?:st|nd|rd|th)\s+[A-Za-z]{3,9}\s+\d{4})'
match = re.search(pattern, text)
print(match.group(1))  # Output: 23rd November 2025
```

---

## SUMMARY TABLE

| Receipt | Pattern Type | What It Looks Like | Regex Pattern |
|---------|-------------|-------------------|---------------|
| **Sephora** | Multi-tax | `CANADA GST/TPS (5%): $2.62` | `r'(?:[A-Z\s]+\s+)?(?:gst\|hst\|pst)(?:/[A-Z]+)?\s*\([^\)]+\):\s*\$?\s*(\d+\.\d{2})'` |
| **Urban Outfitters** | Pipe total | `Total: \| C$93.79` | `r'total:\s*\|\s*C\$\s*(\d+\.\d{2})'` |
| **Urban Outfitters** | Pipe tax | `Tax: \| C$10.79` | `r'tax:\s*\|\s*[A-Z]{0,2}\$?\s*(\d+\.\d{2})'` |
| **Flighthub** | Receipt split | `RECEIPT NUMBER #218086592` | `r'RECEIPT NUMBER #\d+'` |
| **PSA Canada** | CAD format | `TOTAL CAD $ $153.84` | `r'total\s+cad\s+\$\s*\$?\s*(\d+\.\d{2})'` |
| **PSA Canada** | Email vendor | `psacanada@collectors.com` | `r'([a-z]+)@[\w\.]+\.com'` |
| **GeoGuessr** | Multi-line tax | `Sales Tax\nCA$0.33` | `r'sales\s+tax\s*\n\s*([A-Z]{2,3})?\$?\s*(\d+\.\d{2})'` |
| **GeoGuessr** | Ordinal date | `23rd November 2025` | `r'(\d{1,2}(?:st\|nd\|rd\|th)\s+[A-Za-z]{3,9}\s+\d{4})'` |
| **GeoGuessr** | Product vendor | `Product\nGeoGuessr Unlimited` | `r'Product\s*\n\s*([A-Z][a-zA-Z\s]{2,30}?)(?:\s+Unlimited\|\n)'` |

---

This visual guide should help understand exactly what text patterns are present and why the current parser fails on them.
