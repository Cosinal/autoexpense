# Parser Fixes - Quick Reference

## Ready-to-Add Regex Patterns

### AMOUNT PATTERNS (Add to `self.amount_patterns`)

```python
# Add these at the TOP (Priority 1)

# Urban Outfitters fix: Order Summary with pipe separator
(1, r'(?:order\s+summary|payment\s+summary)[\s\S]{0,200}?total:\s*\|\s*[A-Z]{0,2}\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),

# Urban Outfitters fix: Total with pipe and currency code
(1, r'total:\s*\|\s*C\$\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),

# PSA Canada fix: TOTAL CAD $ format
(1, r'total\s+cad\s+\$\s*\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),
```

### TAX PATTERNS (Add to `self.tax_patterns`)

```python
# Sephora fix: Country-prefix tax (CANADA GST/TPS (5%): $2.62)
r'(?:[A-Z\s]+\s+)?(?:gst|hst|pst)(?:/[A-Z]+)?\s*\([^\)]+\):\s*\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',

# Urban Outfitters fix: Tax with pipe separator
r'tax:\s*\|\s*[A-Z]{0,2}\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',

# GeoGuessr fix: Multi-line tax (Sales Tax on one line, amount on next)
r'(?:sales\s+tax|tax\s+total)\s*\n\s*([A-Z]{2,3})?\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
```

### DATE PATTERNS (Add to `self.date_patterns`)

```python
# GeoGuessr fix: Ordinal dates (23rd November 2025)
r'(\d{1,2}(?:st|nd|rd|th)\s+[A-Za-z]{3,9}\s+\d{4})',
```

---

## LOGIC CHANGES

### 1. Multi-Tax Support (Sephora Fix)

**File**: `/Users/jordanshaw/Desktop/expense-reporting/backend/app/services/parser.py`

**Replace**: Lines 419-446 (`extract_tax` method)

```python
def extract_tax(self, text: str) -> Optional[Decimal]:
    """
    Extract tax amount from receipt, summing multiple tax lines if present.

    Args:
        text: Receipt text

    Returns:
        Total tax amount as Decimal or None
    """
    try:
        taxes = []

        # Try each tax pattern
        for pattern in self.tax_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Handle tuple results from patterns with multiple groups
                if isinstance(match, tuple):
                    match = match[-1]  # Take last group (the amount)

                tax_str = match.replace(',', '').replace('$', '').strip()
                try:
                    tax = Decimal(tax_str)
                    if tax > 0:
                        taxes.append(tax)
                except (InvalidOperation, ValueError):
                    continue

        # Return sum of all taxes found (or None if no taxes found)
        if taxes:
            total_tax = sum(taxes)
            print(f"Found {len(taxes)} tax line(s), total: ${total_tax}")
            return total_tax

        return None

    except Exception as e:
        print(f"Error extracting tax: {str(e)}")
        return None
```

### 2. Better Subtotal Filtering (PSA Canada & Urban Outfitters Fix)

**File**: `/Users/jordanshaw/Desktop/expense-reporting/backend/app/services/parser.py`

**In `extract_amount` method** (around line 287-332), update the subtotal check:

```python
# BEFORE (around line 304):
if 'subtotal' in context_window:
    continue

# AFTER:
# Check PRECEDING text specifically (not just context window)
preceding_text = text[max(0, match.start() - 100):match.start()].lower()
following_text = text[match.end():min(len(text), match.end() + 20)].lower()

# Skip if this is labeled as subtotal
if 'subtotal' in preceding_text or 'subtotal' in following_text:
    # Unless it says "grand total" or similar
    if 'grand' not in preceding_text and 'grand' not in following_text:
        continue
```

### 3. Ordinal Date Parsing (GeoGuessr Fix)

**File**: `/Users/jordanshaw/Desktop/expense-reporting/backend/app/services/parser.py`

**In `_parse_date_string` method** (around line 388-417), add BEFORE trying formats:

```python
def _parse_date_string(self, date_str: str) -> Optional[str]:
    """
    Parse various date formats into YYYY-MM-DD.

    Args:
        date_str: Date string in various formats

    Returns:
        Date in YYYY-MM-DD format or None
    """
    # NEW: Handle ordinal suffixes (1st, 2nd, 3rd, 23rd)
    if re.search(r'\d+(?:st|nd|rd|th)', date_str):
        # Remove ordinal suffix: "23rd November 2025" -> "23 November 2025"
        date_str = re.sub(r'(\d+)(?:st|nd|rd|th)', r'\1', date_str)

    # Common date format patterns
    formats = [
        '%m/%d/%Y', '%m-%d-%Y',
        # ... rest of existing formats ...
```

### 4. Payment Processor Detection (GeoGuessr Fix)

**File**: `/Users/jordanshaw/Desktop/expense-reporting/backend/app/services/parser.py`

**Add at class level** (around line 14):

```python
class ReceiptParser:
    """Service for parsing receipt text and extracting structured data."""

    # Known payment processors
    PAYMENT_PROCESSORS = {
        'paddle.com market ltd': 'paddle',
        'paddle.com': 'paddle',
        'paddle': 'paddle',
        'stripe': 'stripe',
        'square': 'square',
    }

    def __init__(self):
        """Initialize parser with regex patterns."""
        self._init_patterns()
```

**Add new method** (after `extract_vendor` method, around line 257):

```python
def _extract_real_merchant(self, text: str) -> Optional[str]:
    """
    Extract actual merchant when vendor is a payment processor.

    Args:
        text: Receipt text

    Returns:
        Real merchant name or None
    """
    # Check bank statement line (e.g., "PADDLE.NET* GEOGUESSR")
    statement_match = re.search(
        r'(?:statement|bank|card)\s+as:\s*([A-Z][A-Z\s\.\*]+)',
        text,
        re.IGNORECASE
    )
    if statement_match:
        statement = statement_match.group(1)
        # Split on * or space to get merchant name
        parts = re.split(r'[\*\s]+', statement)
        # Return last part (usually the merchant)
        for part in reversed(parts):
            if len(part) > 2 and part not in ['NET', 'COM', 'INC']:
                return part.strip().title()

    # Check for product name in invoice
    product_match = re.search(
        r'(?:Product|Description|Item)\s*\n\s*([A-Z][a-zA-Z\s]{2,30}?)(?:\s+(?:Unlimited|Subscription|Pro|Monthly|Annual)|\n)',
        text
    )
    if product_match:
        product_name = product_match.group(1).strip()
        # Clean up common suffixes
        product_name = re.sub(r'\s+(Unlimited|Subscription|Pro|Monthly|Annual)$', '', product_name)
        return product_name

    return None
```

**Update `extract_vendor` method** (add at the END, before return, around line 250):

```python
def extract_vendor(self, text: str) -> Optional[str]:
    """Extract vendor/merchant name from receipt text."""
    try:
        # ... existing vendor extraction logic ...

        # NEW: If vendor is a payment processor, try to find real merchant
        if vendor:
            vendor_lower = vendor.lower()
            if vendor_lower in self.PAYMENT_PROCESSORS:
                real_merchant = self._extract_real_merchant(text)
                if real_merchant:
                    print(f"Payment processor detected: {vendor} -> Real merchant: {real_merchant}")
                    return real_merchant

        return vendor

    except Exception as e:
        print(f"Error extracting vendor: {str(e)}")
        return None
```

### 5. Email Domain Hints for Vendor (PSA Canada Fix)

**File**: `/Users/jordanshaw/Desktop/expense-reporting/backend/app/services/parser.py`

**In `extract_vendor` method**, add AFTER checking email "From:" field (around line 162):

```python
# After the "From:" field check, add:

# Check for email domain hints (e.g., psacanada@collectors.com)
email_domain_match = re.search(
    r'([a-z]+)@[\w\.]+\.com',
    text[:500],
    re.IGNORECASE
)
if email_domain_match:
    domain_prefix = email_domain_match.group(1).lower()
    # Map known domain prefixes to company names
    if 'psa' in domain_prefix:
        return 'PSA Canada'

# Also check for company mentions in email signature/header
if re.search(r'\bPSA\s+(?:Submission|Invoice|Canada)\b', text[:500], re.IGNORECASE):
    return 'PSA Canada'
```

---

## BLACKLIST ADDITIONS

Add to `self.blacklist_contexts` (around line 42):

```python
self.blacklist_contexts = [
    'liability', 'coverage', 'insurance', 'limit', 'maximum',
    'up to', 'points', 'pts', 'booking reference', 'confirmation',
    'reference', 'miles', 'rewards',
    # NEW: Add these
    'item', 'price each', 'unit price', 'per item',  # Item prices
]
```

---

## TESTING COMMANDS

After making changes, run these tests:

```bash
cd /Users/jordanshaw/Desktop/expense-reporting/backend

# Test Sephora (multi-tax)
python -c "
from app.services.parser import ReceiptParser
with open('failed_receipts/email_19c33910.txt') as f:
    text = f.read()
parser = ReceiptParser()
result = parser.parse(text)
print(f'Amount: {result[\"amount\"]} (expect 59.52)')
print(f'Tax: {result[\"tax\"]} (expect 7.32)')
print(f'Vendor: {result[\"vendor\"]} (expect Sephora)')
"

# Test Urban Outfitters (order summary total)
python -c "
from app.services.parser import ReceiptParser
with open('failed_receipts/email_19c33917.txt') as f:
    text = f.read()
parser = ReceiptParser()
result = parser.parse(text)
print(f'Amount: {result[\"amount\"]} (expect 93.79, NOT 54.00)')
print(f'Tax: {result[\"tax\"]} (expect 10.79)')
"

# Test PSA Canada (total not subtotal)
python -c "
from app.services.parser import ReceiptParser
with open('failed_receipts/PSA_Canada.txt') as f:
    text = f.read()
parser = ReceiptParser()
result = parser.parse(text)
print(f'Amount: {result[\"amount\"]} (expect 153.84, NOT 134.95)')
print(f'Tax: {result[\"tax\"]} (expect 18.89)')
print(f'Vendor: {result[\"vendor\"]} (expect PSA Canada)')
"

# Test GeoGuessr (payment processor, date, tax)
python -c "
from app.services.parser import ReceiptParser
with open('failed_receipts/GeoGuessr.txt') as f:
    text = f.read()
parser = ReceiptParser()
result = parser.parse(text)
print(f'Amount: {result[\"amount\"]} (expect 6.99)')
print(f'Tax: {result[\"tax\"]} (expect 0.33)')
print(f'Vendor: {result[\"vendor\"]} (expect GeoGuessr)')
print(f'Date: {result[\"date\"]} (expect 2025-11-23)')
"
```

---

## IMPLEMENTATION CHECKLIST

- [ ] **CRITICAL**: Urban Outfitters - Add order summary patterns
- [ ] **CRITICAL**: Urban Outfitters - Improve subtotal filtering
- [ ] **HIGH**: Sephora - Multi-tax support (modify `extract_tax`)
- [ ] **HIGH**: PSA Canada - Add "TOTAL CAD $" pattern
- [ ] **HIGH**: PSA Canada - Email domain vendor hints
- [ ] **HIGH**: GeoGuessr - Multi-line tax pattern
- [ ] **HIGH**: GeoGuessr - Ordinal date parsing
- [ ] **HIGH**: GeoGuessr - Payment processor detection
- [ ] **MEDIUM**: Add blacklist for item prices
- [ ] **TEST**: Run all 5 test commands
- [ ] **TEST**: Check for regressions on previously working receipts

---

## ESTIMATED TIME

- **Regex additions**: 30 minutes
- **Logic changes**: 2-3 hours
- **Testing**: 1-2 hours
- **Total**: 4-6 hours

## FILES TO MODIFY

1. `/Users/jordanshaw/Desktop/expense-reporting/backend/app/services/parser.py` - Main parser logic

That's it! Only one file needs to be modified.
