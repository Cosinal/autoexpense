# Production-Grade Critique: ReceiptParser

**Context**: Part of ~20k LOC production parsing system
**Scope**: ~852 LOC in parser.py
**Focus**: Generalization to unseen formats without vendor-specific rule creep

---

## Executive Summary

**Current State**: `parser.py` uses priority-based sequential matching with first-match-wins extraction. No candidate scoring framework exists elsewhere in the codebase.

**Key Issues**:
1. **First-match-wins** prevents scoring multiple extraction candidates
2. **Currency always defaults to USD**, inflating confidence when uncertain
3. **Vendor maps violate "no prebuilt conditions" goal** (known_vendor_patterns, PAYMENT_PROCESSORS)
4. **Locale/money parsing gaps**: No support for European formats (1.234,56), negative amounts, missing decimals
5. **Confidence calculation ignores per-field evidence** already collected in debug dict
6. **No upstream context utilization**: Email sender/subject extracted but never passed to parser

---

## I. Architectural Assumptions Analysis

### ✅ Verified Assumptions

1. **Structured Logging Exists**: `logging.getLogger(__name__)` pattern used throughout codebase
2. **Debug Metadata Storage**: `ingestion_debug` JSONB column exists in receipts table
3. **OCR Preprocessing**: Basic normalization exists in `ocr.py` (currency symbols, whitespace)
4. **Decimal Precision Required**: Database uses NUMERIC(15,4), Decimal type throughout

### ❌ False Assumptions

1. **NO centralized candidate/scoring framework** - parser.py could emit candidates for upstream selection
2. **NO shared money parsing utilities** - each service does inline parsing
3. **NO user locale/region data** - heuristic-only locale detection
4. **NO email context passed to parser** - sender domain/subject extracted but unused
5. **NO confidence-based decision making** - confidence calculated but not acted upon

### ⚠️ Questionable Assumptions

1. **Currency must always be truthy**: API layer defaults to USD if parser returns None
   - **Question**: Should parser return `Optional[str]` and let upstream decide?
   - **Current Impact**: Inflates confidence (always +0.05) even when guessing

2. **Vendor hint maps allowed**: 16 hardcoded vendor regexes + 6 payment processors
   - **Question**: Does this violate "no prebuilt vendor conditions" design goal?
   - **Current Impact**: Creates maintenance burden, doesn't generalize

3. **Date ambiguity acceptable**: Numeric dates (01/15/2024) resolve via heuristic
   - **Question**: Could upstream provide stronger hints (sender domain, billing country)?
   - **Current Impact**: MM/DD vs DD/MM remains guesswork for international receipts

---

## II. Critical Issues by Component

### A. Amount Extraction (Lines 504-566)

**Problem 1: First-Match-Wins Architecture**

```python
for spec in self.amount_patterns:
    matches = list(spec.compiled.finditer(text))
    for match in matches:
        # ... blacklist check, subtotal filtering ...
        return amount  # ← RETURNS IMMEDIATELY, no scoring
```

**Impact**:
- Pattern at priority=1 that matches "insurance limit: $50,000" blocks better priority=2 match "Total: $59.52"
- No way to score proximity to keywords like "total", "paid", "charged"
- No way to penalize ambiguous matches or reward clear context
- Can't preserve alternatives for manual review

**Recommended Fix**:
```python
# Collect all candidates first
candidates = []
for spec in self.amount_patterns:
    for match in spec.compiled.finditer(text):
        if not self._passes_blacklist(match, text):
            continue
        candidate = AmountCandidate(
            value=Decimal(amount_str),
            pattern=spec.name,
            span=(match.start(), match.end()),
            base_priority=spec.priority,
            context=text[match.start()-100:match.end()+100]
        )
        candidates.append(candidate)

# Score each candidate
for candidate in candidates:
    candidate.score = self._score_amount_candidate(candidate, text)

# Return best, preserve alternatives in debug
candidates.sort(key=lambda c: c.score, reverse=True)
if candidates:
    best = candidates[0]
    if _debug is not None:
        _debug['amount_candidates'] = [
            {'value': str(c.value), 'pattern': c.pattern,
             'score': c.score, 'reason': c.score_reason}
            for c in candidates[:3]
        ]
    return best.value
```

**Scoring Factors** (Example):
```python
def _score_amount_candidate(self, candidate, full_text):
    score = 100 / candidate.base_priority  # Base: priority

    # Keyword proximity bonus
    keywords = ['total', 'paid', 'charged', 'amount paid', 'grand total']
    for kw in keywords:
        if kw in candidate.context.lower():
            score += 20
            break

    # Currency proximity bonus (indicates this is a monetary field)
    if self._currency_near_match(candidate.span, full_text):
        score += 10

    # Subtotal penalty
    if 'subtotal' in candidate.context.lower():
        score -= 30

    # Large amount penalty if low-priority pattern
    if candidate.value > 10000 and candidate.base_priority > 2:
        score -= 50

    candidate.score_reason = f"priority={candidate.base_priority}, context_kw={'yes' if score>110 else 'no'}"
    return score
```

---

**Problem 2: Blacklist is Global, Not Pattern-Aware**

```python
self.blacklist_contexts = [
    'liability', 'coverage', 'insurance', 'limit', 'maximum',
    'up to', 'points', 'pts', 'booking reference', 'confirmation',
    'reference', 'miles', 'rewards'
]
```

**Impact**:
- "reward points" correctly ignored
- BUT: "Total rewards: $50.00" also ignored (false negative)
- Blacklist applied uniformly regardless of pattern confidence

**Recommended Fix**:
- Make blacklist a penalty (-50 score) not a hard filter
- High-priority patterns (priority=1) can override blacklist if context is strong
- Example: "Amount Paid" with "rewards" nearby still wins if no better candidate

---

**Problem 3: No Support for European Money Formats**

**Missing Cases**:
```python
# European decimal comma: 1.234,56 EUR
# Space thousand separator: 1 234.56 CAD
# Missing decimals: $50 (zero cents implied)
# Negative/refund: -$12.34 or ($12.34)
```

**Question**: Does system need to support non-US formats?
- **If YES**: Create shared `parse_money(amount_str, locale_hint)` utility
- **If NO**: Document US-only assumption and add validation

**Recommended Shared Utility** (if YES):
```python
# app/utils/money.py
def parse_money(amount_str: str, locale_hint: Optional[str] = None) -> Optional[Decimal]:
    """
    Parse money amount with locale awareness.

    Supports:
    - US format: 1,234.56
    - EU format: 1.234,56
    - Space separator: 1 234.56
    - Missing decimals: $50 → 50.00
    - Negative: -12.34, (12.34)
    """
    # Remove currency symbols
    amount_str = re.sub(r'[$€£¥CA]', '', amount_str).strip()

    # Negative amount detection
    is_negative = amount_str.startswith('-') or (
        amount_str.startswith('(') and amount_str.endswith(')')
    )
    amount_str = amount_str.strip('-()').strip()

    # Detect format by looking at rightmost separator
    if ',' in amount_str and '.' in amount_str:
        # Both present: rightmost is decimal separator
        comma_pos = amount_str.rfind(',')
        dot_pos = amount_str.rfind('.')

        if dot_pos > comma_pos:
            # US: 1,234.56
            amount_str = amount_str.replace(',', '')
        else:
            # EU: 1.234,56
            amount_str = amount_str.replace('.', '').replace(',', '.')

    elif ',' in amount_str:
        # Ambiguous: could be 1,234 (thousand) or 12,34 (EU decimal)
        parts = amount_str.split(',')
        if len(parts[-1]) == 2 and len(parts[-1].replace(' ', '')) == 2:
            # Looks like EU decimal: 12,34
            amount_str = amount_str.replace(',', '.')
        else:
            # Thousand separator: 1,234
            amount_str = amount_str.replace(',', '')

    # Remove spaces (thousand separator in some locales)
    amount_str = amount_str.replace(' ', '')

    try:
        value = Decimal(amount_str)
        return -value if is_negative else value
    except (InvalidOperation, ValueError):
        return None
```

---

### B. Currency Extraction (Lines 590-678)

**Problem 1: Always Returns Truthy Value**

```python
def extract_currency(self, text: str, _debug=None) -> str:
    # ... detection strategies ...
    return 'USD'  # ← ALWAYS RETURNS SOMETHING
```

**Impact**:
- Confidence calculation always gets +0.05 bonus (line 847)
- No way to distinguish "found explicit CAD" from "defaulted to USD"
- Upstream services can't decide to use user's billing country if parser is uncertain

**Question**: Does API layer **require** currency field always?
- **Analysis**: Yes, ingestion.py:421 and upload.py:144 default to 'USD' if None
- **But**: This defaulting could happen **upstream** with provenance tracking

**Recommended Fix**:
```python
def extract_currency(self, text: str, _debug=None) -> Optional[str]:
    """
    Extract currency with explicit confidence.
    Returns None if no strong evidence found.
    """
    # Strategy 0: Amount vicinity (HIGH confidence)
    if _debug and 'amount_match_span' in _debug:
        currency = self._detect_currency_in_text(vicinity)
        if currency:
            if _debug: _debug['currency_source'] = 'amount_vicinity'
            return currency

    # Strategy 1: Document-level explicit codes (MEDIUM confidence)
    for code in ['CAD', 'USD', 'EUR', ...]:
        if code in text_upper:
            if _debug: _debug['currency_source'] = 'document_code'
            return code

    # Strategy 2: Symbol-only ($, €, £) → DO NOT DEFAULT
    # Let upstream decide based on user context
    if '$' in text:
        if _debug: _debug['currency_source'] = 'bare_dollar_symbol'
        # Could be USD, CAD, AUD, NZD - return None to signal ambiguity
        return None

    if _debug: _debug['currency_source'] = 'none'
    return None  # Upstream will default based on user's billing country
```

**Upstream Change** (ingestion.py):
```python
parsed_currency = parsed_data.get('currency')
if not parsed_currency:
    # Smart defaulting: check user's billing country, previous receipts
    parsed_currency = self._infer_currency(user_id, email_metadata)
receipt_data['currency'] = parsed_currency or 'USD'  # Final fallback
```

---

**Problem 2: Generic PAYMENT_PROCESSORS Keys**

```python
PAYMENT_PROCESSORS = {
    'market ltd': 'paddle',  # ← TOO GENERIC
    # ... other processors
}
```

**Impact**:
- "ABC Market Ltd" incorrectly identified as Paddle
- "London Market Ltd" false positive

**Question**: Does upstream normalize merchant field? Is there a safer processor list?
- **Analysis**: No upstream merchant normalization found
- **Issue**: Very low precision on generic terms

**Recommended Fix**:
```python
# Tighten to high-precision tokens only
PAYMENT_PROCESSORS = {
    'paddle.com market ltd': 'paddle',  # KEEP (specific)
    'paddle.com': 'paddle',             # KEEP
    'stripe, inc': 'stripe',            # ADD specificity
    'square, inc': 'square',
    'paypal': 'paypal',
}

# REMOVE generic "market ltd" entirely
```

---

### C. Vendor Extraction (Lines 347-502)

**Problem 1: Hardcoded Vendor Patterns Violate Design Goal**

```python
self.known_vendor_patterns = [
    (re.compile(r'\buber\b', re.IGNORECASE), 'Uber'),
    (re.compile(r'\bamazon\b', re.IGNORECASE), 'Amazon'),
    # ... 16 total
]
```

**Question**: Are vendor maps allowed, or does this violate "no prebuilt vendor conditions"?
- **If ALLOWED**: Gate behind feature flag, ensure not primary path
- **If NOT ALLOWED**: Replace with general "name-likeness" scoring

**Impact if kept**:
- Creates maintenance burden (adding new vendors constantly)
- Doesn't generalize to unseen vendors
- Becomes primary extraction path (line 381-386) before general heuristics

**Recommended Fix (if maps NOT allowed)**:
```python
def _score_vendor_candidate(self, text: str, lines: List[str]) -> List[VendorCandidate]:
    """
    Score potential vendor names by structural features, not hardcoded lists.
    """
    candidates = []

    for i, line in enumerate(lines[:20]):
        if self._is_email_header(line):
            continue

        # Scoring factors (generic, no vendor-specific rules)
        score = 100

        # Position bonus (earlier = more likely)
        score -= i * 5

        # Length bonus (company names 3-50 chars)
        if 3 <= len(line) <= 50:
            score += 20

        # Title case bonus (proper noun indicator)
        if line.istitle() or line.isupper():
            score += 10

        # Legal entity indicator (Inc, LLC, Ltd)
        if re.search(r'\b(Inc|LLC|Ltd|Limited|Corp)\b', line):
            score += 30

        # All-caps penalty (likely header/label)
        if line.isupper() and len(line) > 10:
            score -= 20

        # Contains digits penalty (likely address/phone)
        if re.search(r'\d', line):
            score -= 15

        candidates.append(VendorCandidate(name=line, score=score, line_num=i))

    return sorted(candidates, key=lambda c: c.score, reverse=True)
```

---

**Problem 2: Email "From:" Extraction Missing Sender Domain Context**

**Current**: Parser looks for "From:" in OCR text (line 367-378)
```python
if line.strip().lower().startswith('from:'):
    match = re.search(r'from:\s*\*?\*?([^<\*]+?)[\*\s]*(?:<|$)', line, re.IGNORECASE)
```

**Issue**:
- Only works if email headers are in OCR text
- Doesn't leverage actual email metadata extracted in `email.py:402-446`

**Question**: Should parser receive email context as parameter?
- **Current signature**: `parse(text: str) -> Dict`
- **Proposed**: `parse(text: str, context: Optional[ParseContext] = None) -> Dict`

**Recommended Fix**:
```python
@dataclass
class ParseContext:
    """Optional context for parser to improve extraction."""
    email_from: Optional[str] = None      # receipts@uber.com
    email_subject: Optional[str] = None   # Your Uber Receipt
    user_locale: Optional[str] = None     # 'en-CA', 'en-US', 'de-DE'
    sender_domain: Optional[str] = None   # uber.com

def parse(self, text: str, context: Optional[ParseContext] = None) -> Dict[str, Any]:
    """Parse with optional context hints."""
    debug = {...}

    result = {
        'vendor': self.extract_vendor(text, context=context, _debug=debug),
        # ...
    }

def extract_vendor(self, text: str, context: Optional[ParseContext] = None, _debug=None):
    """Extract vendor with context hints."""
    # Try context-based extraction first (HIGHEST confidence)
    if context and context.email_from:
        vendor = self._vendor_from_email(context.email_from)
        if vendor:
            if _debug: _debug['vendor_source'] = 'email_context'
            return vendor

    # Fallback to text-based extraction
    # ...

def _vendor_from_email(self, email_addr: str) -> Optional[str]:
    """Extract vendor from email sender with high precision."""
    # Parse domain
    match = re.search(r'@([a-z0-9.-]+)', email_addr, re.IGNORECASE)
    if not match:
        return None

    domain = match.group(1)

    # Extract company name from domain (generic rules)
    # amazon.com → Amazon
    # receipts.uber.com → Uber
    # noreply.sephora.com → Sephora

    parts = domain.split('.')
    # Use second-to-last part (before .com/.ca etc)
    if len(parts) >= 2:
        company = parts[-2]
        # Skip generic subdomains
        if company not in ['receipts', 'noreply', 'no-reply', 'mail']:
            return company.title()

    return None
```

**Ingestion Change** (ingestion.py):
```python
# Line 106: metadata already extracted
metadata = self.email_service.extract_email_metadata(message)

# Line 230: Pass context to parser
context = ParseContext(
    email_from=metadata.get('from'),
    email_subject=metadata.get('subject'),
    sender_domain=self._extract_domain(metadata.get('from'))
)
parsed_data = self.parser.parse(text, context=context)
```

---

### D. Date Extraction (Lines 714-778)

**Problem: Numeric Date Ambiguity Persists**

**Current Heuristic** (lines 688-692):
```python
if any(t in text_upper for t in ('GST', 'PST', 'HST', 'CANADA')):
    return 'MM/DD'  # North American
if '£' in text or 'VAT' in text_upper:
    return 'DD/MM'  # European
return 'MM/DD'  # Default to North American
```

**Issues**:
- International receipts without clear indicators default to MM/DD
- No disambiguation for dates like 05/06/2024 (May 6 or June 5?)
- No use of upstream locale hints (sender domain, user billing country)

**Recommended Improvements**:

1. **Use >12 Heuristic** (unambiguous dates):
```python
def _parse_numeric_date_with_locale(self, date_str: str, locale: str) -> Optional[str]:
    """Parse numeric date with disambiguation."""
    sep = '/' if '/' in date_str else '-'
    parts = [int(p) for p in date_str.split(sep)]

    # Unambiguous cases
    if parts[0] > 12:  # Must be DD/MM/YYYY
        locale = 'DD/MM'
    elif parts[1] > 12:  # Must be MM/DD/YYYY
        locale = 'MM/DD'

    # Use provided locale hint for ambiguous cases
    # ...
```

2. **Keyword-Window Prioritization** (find dates near transaction keywords):
```python
def extract_date(self, text: str, context: Optional[ParseContext] = None, _debug=None):
    """Extract date with keyword proximity scoring."""

    # Collect all date candidates
    candidates = []
    for spec in self.date_patterns:
        for match in spec.compiled.finditer(text):
            candidate = DateCandidate(
                value=match.group(1),
                span=match.span(),
                pattern=spec.name
            )
            candidates.append(candidate)

    # Score by proximity to transaction keywords
    keywords = ['transaction', 'order', 'issued', 'paid', 'date:', 'purchased']
    for candidate in candidates:
        context_window = text[max(0, candidate.span[0]-100):candidate.span[1]+50]
        candidate.score = sum(10 for kw in keywords if kw in context_window.lower())

    # Return highest-scoring date
    candidates.sort(key=lambda c: c.score, reverse=True)
    if candidates:
        best = candidates[0]
        parsed = self._parse_date_string(best.value)
        if _debug:
            _debug['date_candidates'] = [
                {'value': c.value, 'score': c.score} for c in candidates[:3]
            ]
        return parsed
```

3. **Use Upstream Locale** (if context provides it):
```python
if context and context.user_locale:
    locale = 'DD/MM' if context.user_locale.startswith('en-GB') else 'MM/DD'
else:
    locale = self._detect_date_locale(text)  # Fallback to heuristic
```

---

### E. Tax Extraction (Lines 780-826)

**✅ Strengths**: Span-based deduplication is excellent (lines 796-804)

**⚠️ Concern**: "Tax total" / "Tax breakdown" Summary Lines**

**Current Mitigation** (line 232):
```python
PatternSpec(
    name='sales_tax_multiline',
    pattern=r'sales\s+tax\s*\n\s*([A-Z]{2,3})?\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
    notes='GeoGuessr - multi-line sales tax (excludes "Tax total" summary lines)',
)
```

**Issue**: Pattern-by-pattern mitigation doesn't scale

**Question**: Does upstream already remove summary lines?
- **Analysis**: No pre-filtering in OCR or email services

**Recommended Fix**: Add negative-context filter
```python
def extract_tax(self, text: str, _debug=None) -> Optional[Decimal]:
    """Extract tax with summary line filtering."""
    seen_spans = set()
    taxes = []

    # Negative context indicators (summary lines to skip)
    summary_indicators = ['tax total', 'tax breakdown', 'total tax', 'included']

    for spec in self.tax_patterns:
        for match in spec.compiled.finditer(text):
            amount_span = match.span(match.lastindex or 1)
            if amount_span in seen_spans:
                continue

            # Check for summary line context
            match_context = text[max(0, match.start()-50):match.end()+30].lower()
            if any(indicator in match_context for indicator in summary_indicators):
                continue  # Skip summary lines

            seen_spans.add(amount_span)
            # ... rest of extraction
```

---

### F. Confidence Calculation (Lines 828-851)

**Problem 1: Ignores Per-Field Evidence Already Collected**

**Current Implementation**:
```python
def _calculate_confidence(self, parsed_data: Dict[str, Any]) -> float:
    score = 0.0
    if parsed_data.get('vendor'): score += 0.25
    if parsed_data.get('amount'): score += 0.35
    if parsed_data.get('date'): score += 0.25
    if parsed_data.get('currency'): score += 0.05  # ← Always true!
    if parsed_data.get('tax'): score += 0.10
    return round(score, 2)
```

**Issue**: Parser populates `debug['confidence_per_field']` but never uses it!

**Evidence Already Collected**:
```python
_debug['confidence_per_field']['vendor'] = 0.95  # known vendor
_debug['confidence_per_field']['amount'] = 1.0 / spec.priority  # pattern priority
_debug['confidence_per_field']['date'] = 0.9
_debug['confidence_per_field']['tax'] = 0.9
```

**Recommended Fix**:
```python
def _calculate_confidence(self, parsed_data: Dict[str, Any]) -> float:
    """Calculate confidence using per-field evidence and penalties."""

    debug = parsed_data.get('debug', {})
    field_confidence = debug.get('confidence_per_field', {})

    # Use actual per-field confidence (not binary presence)
    weights = {
        'vendor': 0.25,
        'amount': 0.35,
        'date': 0.25,
        'currency': 0.05,
        'tax': 0.10,
    }

    score = 0.0
    for field, weight in weights.items():
        if parsed_data.get(field):
            # Use per-field confidence if available
            field_conf = field_confidence.get(field, 0.5)  # Default mid-conf
            score += weight * field_conf

    # Penalties for uncertainty signals
    warnings = debug.get('warnings', [])
    if 'currency_defaulted' in warnings:
        score *= 0.95  # Penalize default currency

    if 'date_ambiguous' in warnings:
        score *= 0.90  # Penalize MM/DD ambiguity

    if 'amount_low_priority_pattern' in warnings:
        score *= 0.85  # Penalize weak amount match

    return round(score, 2)
```

**Add Provenance Tracking**:
```python
# In extract_currency
if currency is None:
    _debug['warnings'].append('currency_defaulted')
    currency = 'USD'

# In extract_amount
if spec.priority > 3:
    _debug['warnings'].append('amount_low_priority_pattern')

# In extract_date (numeric ambiguous)
if spec.name == 'numeric_date_ambiguous':
    _debug['warnings'].append('date_ambiguous')
```

---

**Problem 2: Confidence Not Used for Decision-Making**

**Question**: Is confidence used upstream?
- **Analysis**: Stored in `ingestion_debug` column but never queried
- **Opportunity**: Trigger manual review queue if confidence < 0.7

**Recommended Upstream Logic** (ingestion.py):
```python
parsed_data = self.parser.parse(text, context=context)

if parsed_data['confidence'] < 0.70:
    # Flag for manual review
    receipt_data['requires_review'] = True
    receipt_data['review_reason'] = 'low_parser_confidence'
    logger.info("Receipt flagged for review", extra={
        'confidence': parsed_data['confidence'],
        'receipt_id': receipt_id
    })
```

---

## III. Locale/Money Parsing Gaps

### Missing Format Support

| Format | Example | Current Support | Fix |
|--------|---------|-----------------|-----|
| **European decimal comma** | 1.234,56 € | ❌ Fails | Shared `parse_money()` |
| **Space thousand separator** | 1 234.56 CAD | ❌ Fails | Shared `parse_money()` |
| **Missing decimals** | $50 (→ 50.00) | ⚠️ Partial | Normalize to .00 |
| **Negative amounts** | -$12.34, ($12.34) | ❌ Fails | Support in `parse_money()` |
| **Multiple currencies in doc** | EUR subtotal, USD total | ⚠️ May misclassify | Amount-vicinity strategy helps |

**Question**: Does system support non-US formats?
- **Usage Evidence**: Database shows receipts from Canada (CAD), but numeric formats not tested
- **Recommendation**: Support at minimum: comma-as-decimal (EU), space separator, negative amounts

**Implementation**: Create `app/utils/money.py` (shared utility, see Section II.A.3 for full code)

---

## IV. Minimal, Architecture-Aware Refactor Plan

### Phase 1: Foundation (No Breaking Changes)

**Goal**: Improve extraction quality without changing interfaces

1. **Add Candidate Collection** (3-5 days)
   - Create `AmountCandidate`, `DateCandidate`, `VendorCandidate` dataclasses
   - Refactor `extract_amount()` to collect + score + select
   - Preserve top 3 alternatives in `debug['amount_candidates']`
   - **No API change**: Still returns single `Decimal`, but debug has alternatives

2. **Scoring Helpers** (2-3 days)
   - `_score_amount_candidate()`: keyword proximity, currency vicinity, blacklist penalty
   - `_score_vendor_candidate()`: position, title case, legal entity, no hardcoded names
   - `_score_date_candidate()`: keyword proximity, unambiguous heuristic

3. **Improve Confidence** (1 day)
   - Use per-field confidence from debug
   - Add provenance tracking (defaulted, ambiguous, low-priority)
   - Penalize uncertainty

**Testing**: Use existing test fixtures, verify debug output includes candidates

---

### Phase 2: Context Integration (Optional, if agreed)

**Goal**: Leverage email metadata for better extraction

4. **Add ParseContext** (2-3 days)
   - Create `ParseContext` dataclass with email_from, subject, user_locale
   - Update `parse()` signature: `parse(text, context=None)`
   - Extract vendor from email sender (high confidence)
   - Use user_locale for date disambiguation

5. **Update Ingestion** (1 day)
   - Pass ParseContext to parser in `ingestion.py`
   - Extract domain from email metadata

**Testing**: Verify email-based vendor extraction improves coverage

---

### Phase 3: Money Parsing (If International Support Needed)

6. **Shared Money Utility** (2-3 days)
   - Create `app/utils/money.py` with `parse_money()`
   - Support: EU decimal comma, space separator, negative amounts
   - Refactor `extract_amount()` to use `parse_money()`

7. **Optionalize Currency Default** (1 day)
   - Change `extract_currency()` return type to `Optional[str]`
   - Add `currency_source` to debug
   - Update upstream (ingestion.py) to handle None with smart defaulting

**Testing**: Add fixtures with EU formats, negative amounts

---

### Phase 4: Vendor Generalization (If Maps Not Allowed)

8. **Remove Hardcoded Vendor Maps** (2-3 days)
   - Delete `known_vendor_patterns` (16 patterns)
   - Delete `PAYMENT_PROCESSORS` or reduce to 3 high-precision entries
   - Replace with generic `_score_vendor_candidate()` (structural features)

9. **Tighten Payment Processor List** (1 day)
   - Remove "market ltd" generic entry
   - Keep only: "paddle.com market ltd", "paddle.com", "stripe, inc", etc.

**Testing**: Verify no regression on known vendors, improved generalization on unseen vendors

---

### Phase 5: Targeted Tests

10. **Representative Unseen-Format Fixtures** (2-3 days)
    - European format: `DE_restaurant_receipt.txt` (1.234,56 €)
    - Negative amount: `refund_receipt.txt` (-$50.00)
    - Ambiguous date: `intl_invoice.txt` (15/03/2024 with no locale hint)
    - Missing vendor: `generic_pos_receipt.txt` (no From: field, no known patterns)
    - Multiple currencies: `forex_receipt.txt` (USD subtotal, EUR total)

11. **Debug Output Validation** (1 day)
    - Every test verifies debug contains:
      - `patterns_matched`: pattern name for each field
      - `confidence_per_field`: per-field confidence
      - `amount_candidates`: top 3 alternatives with scores
      - `warnings`: uncertainty signals (defaulted, ambiguous)
      - `*_source`: provenance (email_context, document_code, amount_vicinity)

**Success Criteria**:
- Parser selects correct value even when lower-priority pattern
- Debug explains reasoning (scores, candidates, warnings)
- Confidence reflects true extraction quality

---

## V. Summary

### Immediate Wins (Phase 1 Only)

✅ **Better amount extraction**: Score multiple candidates instead of first-match
✅ **Transparent reasoning**: Debug shows why parser chose each value
✅ **Honest confidence**: Penalize defaults and ambiguity
✅ **No breaking changes**: Preserves API, adds debug detail

**Effort**: ~1 week (6-9 days)

### Full Refactor (All Phases)

✅ **Context-aware extraction**: Uses email sender for vendor
✅ **International support**: EU formats, negative amounts
✅ **Vendor generalization**: No hardcoded patterns
✅ **Smart defaulting**: Upstream handles ambiguity with user context

**Effort**: ~3-4 weeks (15-20 days)

---

## VI. Open Questions for Architectural Decisions

1. **Currency Defaulting**: Should parser return `Optional[str]` or always default to USD?
   - **Recommendation**: Return Optional, upstream defaults based on user billing country

2. **Vendor Maps**: Are hardcoded vendor regexes allowed or should they be removed?
   - **Recommendation**: Remove or gate behind feature flag, prefer general scoring

3. **International Support**: Does system need to support EU number formats?
   - **Recommendation**: Yes, at minimum support comma-as-decimal and negative amounts

4. **Context Parameter**: Should parser accept ParseContext with email metadata?
   - **Recommendation**: Yes, significantly improves vendor/currency extraction

5. **Confidence Thresholds**: Should low confidence trigger manual review?
   - **Recommendation**: Yes, flag receipts <0.7 for review queue

---

## VII. Code Quality Notes

**Strengths**:
- ✅ PatternSpec dataclass is clean, well-documented
- ✅ Span-based tax dedup is elegant (lines 796-804)
- ✅ Priority-based pattern ordering is good foundation for scoring
- ✅ Debug metadata structure is well-designed
- ✅ Structured logging used correctly

**Technical Debt**:
- 🔶 No regex timeout protection (DoS risk on adversarial input)
- 🔶 Vendor/processor maps create maintenance burden
- 🔶 Inline money parsing duplicated (no shared utilities)
- 🔶 Large methods (extract_vendor=156 lines, extract_amount=63 lines)

**Recommended Protections**:
```python
# Add regex timeout to PatternSpec
@dataclass(frozen=True)
class PatternSpec:
    # ...
    timeout_ms: int = 1000  # Prevent ReDoS attacks

    def __post_init__(self):
        # Python 3.11+ supports timeout in re.compile
        compiled = re.compile(self.pattern, self.flags, timeout=self.timeout_ms / 1000.0)
        object.__setattr__(self, 'compiled', compiled)
```

---

**End of Critique**
