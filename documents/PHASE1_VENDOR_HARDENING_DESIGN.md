# Phase 1 Vendor Extraction Hardening - Design Document

**Status**: In Progress
**Date**: 2026-02-12
**Target**: 46.2% → 65% vendor accuracy
**Phase**: 1 of 4 (Pattern Improvements)

---

## Overview

This document describes the refactoring of vendor extraction to support a progressive, multi-phase intelligence pipeline. Phase 1 focuses on pattern-based improvements while laying groundwork for Phase 2 (vendor DB) and Phase 3 (LLM arbitration).

---

## Architecture Changes

### Current Architecture (Single-Pass Selection)
```python
def extract_vendor(text, context):
    candidates = []
    # Strategy 1: Email metadata
    # Strategy 2: From: header
    # Strategy 3: Payable to
    # Strategy 4: Business keywords
    # Strategy 5: Company suffix
    # Strategy 6: Early line fallback

    best = select_best_vendor(candidates)  # Single winner
    return best.value
```

**Limitations**:
- No visibility into runner-up candidates
- Can't defer decision to later phases
- Hard to debug why vendor was chosen

### New Architecture (Candidate Pipeline)
```python
def extract_vendor(text, context):
    # Stage 1: Generate ALL candidates
    candidates = self._generate_vendor_candidates(text, context)

    # Stage 2: Phase 1 scoring (pattern-based)
    scored_candidates = self._score_candidates_phase1(candidates, text)

    # Stage 3: Select best (with confidence threshold)
    best, confidence = self._select_best_with_confidence(scored_candidates)

    # Future: Stage 4 - Phase 2 DB lookup (if confidence < 0.8)
    # Future: Stage 5 - Phase 3 LLM arbitration (if confidence < 0.6)

    return best.value, confidence
```

**Benefits**:
- Modular pipeline (easy to insert Phase 2/3)
- Confidence scores enable progressive fallback
- Better debugging (can inspect all candidates)
- Preserves top-N for review UI

---

## Phase 1 Improvements

### 1. Enhanced Candidate Generation

#### 1.1 Multi-Line Vendor Aggregation
**Problem**: "Apple\nStore" extracted as "Apple" (incomplete)

**Solution**: Combine adjacent capitalized lines
```python
def _combine_multiline_vendors(self, lines: List[str]) -> List[str]:
    """Combine adjacent lines that look like split vendor names."""
    combined = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Check if next line continues the vendor name
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()

            # Combine if:
            # - Both are short (< 20 chars each)
            # - Both start with capital
            # - No numbers in either (avoid amounts)
            # - Combined length < 50 chars
            if (len(line) < 20 and len(next_line) < 20 and
                line and line[0].isupper() and
                next_line and next_line[0].isupper() and
                not re.search(r'\d', line) and
                not re.search(r'\d', next_line) and
                len(line + ' ' + next_line) < 50):

                combined.append(line + ' ' + next_line)
                i += 2
                continue

        combined.append(line)
        i += 1

    return combined
```

**Test case**: "Apple\nStore" → "Apple Store"

#### 1.2 Forwarded Email Detection
**Problem**: Extracting "Jorden Shaw" instead of "Uber" from forwarded emails

**Solution**: Detect forwarded context
```python
def _detect_forwarded_email(self, text: str, context: ParseContext) -> bool:
    """Detect if email was forwarded."""
    indicators = [
        r'[-=]+\s*forwarded message\s*[-=]+',
        r'---------- forwarded',
        r'begin forwarded message',
        r'from:.*\n.*to:.*\n.*subject:',  # Multiple headers = forwarded
    ]

    for pattern in indicators:
        if re.search(pattern, text[:1000], re.IGNORECASE):
            return True

    # Check if sender domain is personal email
    if context and context.sender_domain:
        personal_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com',
                          'icloud.com', 'me.com', 'live.com']
        if any(domain in context.sender_domain for domain in personal_domains):
            return True

    return False
```

**Scoring adjustment**:
```python
if self._is_forwarded:
    # Penalize email header candidates heavily
    if candidate.from_email_header:
        base_score -= 0.5  # Likely forwarder, not vendor
```

**Test case**: Forwarded Uber receipt with "From: Jorden Shaw" → Extract "Uber" not "Jorden Shaw"

#### 1.3 Enhanced OCR Normalization for Vendor Lines
**Problem**: "I N V O I C" instead of "INVOICE"

**Solution**: Aggressive normalization on vendor candidates
```python
def _normalize_vendor_ocr(self, text: str) -> str:
    """Aggressive OCR normalization specifically for vendor extraction."""

    # Step 1: Collapse excessive spacing (character-level)
    # "I N V O I C E" → "INVOICE"
    if re.search(r'[A-Z]\s+[A-Z]\s+[A-Z]', text):
        # Remove all single spaces between single letters
        text = re.sub(r'\b([A-Z])\s+(?=[A-Z]\b)', r'\1', text)

    # Step 2: Collapse multiple spaces
    text = re.sub(r'\s{2,}', ' ', text)

    # Step 3: Remove noise characters (but preserve hyphens, apostrophes, &)
    text = re.sub(r'[^\w\s&\'-]', '', text)

    # Step 4: Title case for consistency
    text = text.title()

    return text.strip()
```

**Test case**: "I N V O I C" → "Invoice", "H S T  -  C a n a d a" → "Hst - Canada"

---

### 2. Improved Scoring Weights

#### 2.1 Early-Line Boosting
**Current**: Lines 0-2 have no penalty (0.0)
**Problem**: Not enough advantage over later lines

**New scoring**:
```python
# SCORING WEIGHTS (document these)
EARLY_LINE_BOOST = {
    0: +0.25,  # Line 0 (very first line) - strong boost
    1: +0.15,  # Line 1 - moderate boost
    2: +0.10,  # Line 2 - small boost
    # 3+: use existing line position penalty
}

# In score_vendor_candidate:
if candidate.line_position <= 2:
    boost = EARLY_LINE_BOOST.get(candidate.line_position, 0.0)
    base_score += boost
elif candidate.line_position > 2:
    # Existing penalty logic
    line_penalty = min(0.4, (candidate.line_position - 2) * 0.02)
    base_score -= line_penalty
```

**Rationale**: Vendor typically appears in first 3 lines. This biases selection toward header.

#### 2.2 Business Context Scoring
**Current**: Business keywords give fixed 0.75 base
**Problem**: Not differentiated enough

**New scoring**:
```python
# Business context weights
BUSINESS_CONTEXT_WEIGHTS = {
    'retail': 0.15,      # "Store", "Shop", "Market", "Outlet"
    'service': 0.12,     # "Clinic", "Salon", "Spa", "Services"
    'food': 0.12,        # "Restaurant", "Cafe", "Bar", "Grill"
    'professional': 0.10, # "Inc", "LLC", "Ltd", "Corp"
    'medical': 0.15,     # "Medical", "Dental", "Optical", "Pharmacy"
}

def _calculate_business_context_score(self, vendor: str) -> float:
    """Calculate cumulative business context score."""
    score = 0.0
    vendor_lower = vendor.lower()

    # Retail indicators
    if any(kw in vendor_lower for kw in ['store', 'shop', 'market', 'outlet']):
        score += BUSINESS_CONTEXT_WEIGHTS['retail']

    # Service indicators
    if any(kw in vendor_lower for kw in ['clinic', 'salon', 'spa', 'services']):
        score += BUSINESS_CONTEXT_WEIGHTS['service']

    # ... other categories

    return min(score, 0.30)  # Cap at +0.30
```

#### 2.3 Person Name Penalty Enhancement
**Current**: -0.6 if looks like person name
**Problem**: Not context-aware

**New logic**:
```python
def _calculate_person_name_penalty(self, candidate: VendorCandidate,
                                   is_forwarded: bool) -> float:
    """Calculate person name penalty based on context."""
    if not _looks_like_person_name(candidate.value):
        return 0.0

    penalty = 0.0

    # Base penalty for person name pattern
    penalty += 0.4

    # Additional penalty if from email header
    if candidate.from_email_header:
        penalty += 0.3

    # Heavy penalty if email was forwarded (sender = forwarder)
    if is_forwarded and candidate.from_email_header:
        penalty += 0.4  # Total: -1.1 (very strong)

    return penalty
```

**Test case**: Forwarded email with "Jorden Shaw" → penalty -1.1, nearly impossible to win

---

### 3. Confidence Thresholds

**Purpose**: Enable Phase 2/3 fallback for low-confidence extractions

```python
# Confidence thresholds (document these)
CONFIDENCE_THRESHOLDS = {
    'high': 0.8,      # Very confident, no fallback needed
    'medium': 0.6,    # Moderately confident, consider DB lookup (Phase 2)
    'low': 0.4,       # Low confidence, needs LLM arbitration (Phase 3)
    'reject': 0.3,    # Too uncertain, mark for manual review
}

def _select_best_with_confidence(self, scored_candidates):
    """Select best candidate and return confidence score."""
    if not scored_candidates:
        return None, 0.0

    # Sort by score descending
    sorted_candidates = sorted(scored_candidates, key=lambda x: x[1], reverse=True)
    best_candidate, best_score = sorted_candidates[0]

    # Calculate confidence based on score and margin
    if len(sorted_candidates) > 1:
        runner_up_score = sorted_candidates[1][1]
        margin = best_score - runner_up_score

        # Confidence is combination of absolute score and margin
        confidence = (best_score * 0.7) + (margin * 0.3)
    else:
        confidence = best_score

    # Normalize to [0, 1]
    confidence = max(0.0, min(1.0, confidence))

    return best_candidate, confidence
```

**Future integration points**:
```python
# Phase 2: Vendor database lookup
if confidence < CONFIDENCE_THRESHOLDS['medium']:
    db_vendor = vendor_db.lookup(best_candidate.value)
    if db_vendor:
        return db_vendor, 0.9  # DB match = high confidence

# Phase 3: LLM arbitration
if confidence < CONFIDENCE_THRESHOLDS['low']:
    top_3 = [c.value for c, _ in sorted_candidates[:3]]
    llm_vendor = llm_arbitrate(text, top_3)
    if llm_vendor:
        return llm_vendor, 0.85  # LLM result = high confidence
```

---

## Phase 2 Groundwork

### Vendor Database Schema

```python
@dataclass
class VendorEntry:
    """Entry in local vendor knowledge base."""
    canonical_name: str          # "Uber"
    aliases: List[str]           # ["Uber Technologies", "UBER TRIP", "Uber Eats"]
    category: str                # "transportation", "food", "retail", etc.
    fingerprint: str             # Normalized for fuzzy matching
    confidence: float = 1.0      # DB entry confidence (1.0 = verified)
    source: str = 'manual'       # 'manual', 'transaction', 'user_correction'

class VendorDatabase:
    """Lightweight local merchant knowledge base."""

    def __init__(self):
        self.vendors: Dict[str, VendorEntry] = {}
        self.fingerprint_index: Dict[str, str] = {}  # fingerprint → canonical
        self._load_database()

    def _normalize_fingerprint(self, name: str) -> str:
        """Create normalized fingerprint for fuzzy matching."""
        # Remove common suffixes
        name = re.sub(r'\b(Inc|LLC|Ltd|Limited|Corp|Corporation)\b', '', name, flags=re.IGNORECASE)
        # Remove punctuation
        name = re.sub(r'[^\w\s]', '', name)
        # Lowercase and strip
        name = name.lower().strip()
        # Remove multiple spaces
        name = re.sub(r'\s+', ' ', name)
        return name

    def lookup(self, vendor_text: str, threshold: int = 3) -> Optional[str]:
        """
        Lookup vendor in database with fuzzy matching.

        Args:
            vendor_text: OCR-extracted vendor text
            threshold: Levenshtein distance threshold

        Returns:
            Canonical vendor name if match found
        """
        # Exact fingerprint match
        fingerprint = self._normalize_fingerprint(vendor_text)
        if fingerprint in self.fingerprint_index:
            return self.fingerprint_index[fingerprint]

        # Fuzzy match (Levenshtein distance)
        for fp, canonical in self.fingerprint_index.items():
            if levenshtein(fingerprint, fp) <= threshold:
                return canonical

        return None

    def add_vendor(self, canonical: str, aliases: List[str],
                   category: str, source: str = 'manual'):
        """Add vendor to database."""
        entry = VendorEntry(
            canonical_name=canonical,
            aliases=aliases,
            category=category,
            source=source
        )

        self.vendors[canonical] = entry

        # Index all aliases by fingerprint
        for alias in [canonical] + aliases:
            fp = self._normalize_fingerprint(alias)
            self.fingerprint_index[fp] = canonical

    def _load_database(self):
        """Load vendor database from JSON file."""
        db_path = Path('data/vendor_database.json')
        if db_path.exists():
            with open(db_path) as f:
                data = json.load(f)
                for item in data['vendors']:
                    self.add_vendor(**item)
```

### Initial Database Seed (100 Common Vendors)

```json
{
  "vendors": [
    {
      "canonical": "Uber",
      "aliases": ["Uber Technologies", "Uber Trip", "Uber Eats", "UBER TECH"],
      "category": "transportation"
    },
    {
      "canonical": "Amazon",
      "aliases": ["Amazon.ca", "Amazon.com", "AMZN Marketplace", "AMZ"],
      "category": "retail"
    },
    {
      "canonical": "Starbucks",
      "aliases": ["Starbucks Coffee", "SBUX"],
      "category": "food"
    },
    {
      "canonical": "Walmart",
      "aliases": ["Walmart Canada", "Walmart Supercenter"],
      "category": "retail"
    },
    {
      "canonical": "Apple",
      "aliases": ["Apple Store", "Apple Inc", "Apple Canada"],
      "category": "retail"
    }
  ]
}
```

---

## Implementation Plan

### Week 1: Core Refactoring
**Day 1-2**: Candidate pipeline refactoring
- [ ] Split extract_vendor into _generate_candidates + _score_candidates + _select_best
- [ ] Add confidence calculation
- [ ] Preserve existing regression tests
- [ ] Test: All 9 regression tests pass

**Day 3-4**: Enhanced candidate generation
- [ ] Multi-line vendor aggregation
- [ ] Forwarded email detection
- [ ] Enhanced OCR normalization
- [ ] Test: Add test for "Apple\nStore", forwarded Uber, "I N V O I C"

**Day 5**: Improved scoring
- [ ] Early-line boosting (+0.25/+0.15/+0.10)
- [ ] Business context scoring
- [ ] Enhanced person name penalty
- [ ] Test: Verify Walmart/Apple now score higher

### Week 2: Phase 2 Groundwork
**Day 6-7**: Vendor database foundation
- [ ] Create VendorDatabase class
- [ ] Implement fingerprint normalization
- [ ] Implement fuzzy matching (Levenshtein)
- [ ] Test: Lookup "UBER TECH" → "Uber"

**Day 8-9**: Database population
- [ ] Create vendor_database.json
- [ ] Seed with 100 common vendors (retail, food, transport, airlines)
- [ ] Add alias mappings for OCR variations
- [ ] Test: Lookup coverage on 13 test receipts

**Day 10**: Integration hook
- [ ] Add Phase 2 integration point (confidence < 0.8)
- [ ] Add logging/metrics for DB hit rate
- [ ] Test: Verify fallback logic without breaking Phase 1

---

## Success Metrics

### Phase 1 Completion Criteria
- [ ] Vendor accuracy: 65%+ (from 46.2%)
- [ ] All 9 regression tests pass
- [ ] All 9 failed receipts have targeted fixes
- [ ] Confidence scores available for all extractions
- [ ] Code is modular (easy to add Phase 2/3)

### Phase 2 Readiness Criteria
- [ ] VendorDatabase class tested and working
- [ ] 100+ vendors in database
- [ ] Fuzzy matching working (Levenshtein ≤ 3)
- [ ] Integration hook in place (not yet active)

---

## Testing Strategy

### Unit Tests
```python
def test_multiline_vendor_aggregation():
    """Test combining adjacent lines into vendor name."""
    lines = ["Apple", "Store", "Location 123"]
    combined = parser._combine_multiline_vendors(lines)
    assert "Apple Store" in combined

def test_forwarded_email_detection():
    """Test detecting forwarded emails."""
    text = "---------- Forwarded message ---------\nFrom: Uber"
    assert parser._detect_forwarded_email(text, None) == True

def test_ocr_vendor_normalization():
    """Test aggressive OCR cleanup for vendor."""
    assert parser._normalize_vendor_ocr("I N V O I C") == "Invoice"
    assert parser._normalize_vendor_ocr("H S T") == "Hst"

def test_vendor_database_lookup():
    """Test fuzzy vendor matching."""
    db = VendorDatabase()
    db.add_vendor("Uber", ["Uber Technologies", "UBER TRIP"], "transportation")
    assert db.lookup("uber tech") == "Uber"
    assert db.lookup("UBER TECHNOLOGIES INC") == "Uber"
```

### Integration Tests (13 Real Receipts)
```python
# Known failures that should be fixed:
FAILURE_TESTS = [
    ("Air Canada", "Air Canada"),  # Currently: "New"
    ("Uber forwarded", "Uber"),    # Currently: "Jorden Shaw"
    ("Anthropic", "Anthropic"),    # Currently: "I N V O I C"
    ("Browz", "Browz Eyeware"),    # Currently: product name
    ("receipt-test.jpg", "Apple Store"),  # Currently: "Patrick Cusack"
]
```

---

## Documentation Requirements

### Code Comments
- Document all scoring weight constants
- Explain threshold values (why 0.8 for DB fallback?)
- Comment decision points for future developers

### Design Rationale
- Why multi-line aggregation only for short lines?
- Why Levenshtein threshold = 3?
- Why early-line boost values (+0.25/+0.15/+0.10)?

### Future Integration Points
```python
# PHASE 2 INTEGRATION POINT
# When implementing vendor database:
# 1. Uncomment the DB lookup below
# 2. Ensure vendor_database.json is populated
# 3. Monitor DB hit rate in logs

# if confidence < CONFIDENCE_THRESHOLDS['medium']:
#     db_vendor = self.vendor_db.lookup(best_candidate.value)
#     if db_vendor:
#         logger.info(f"DB match: {best_candidate.value} → {db_vendor}")
#         return db_vendor, 0.9
```

---

## Risks & Mitigations

### Risk 1: Regression in Working Cases
**Mitigation**: Run regression tests after every change. Rollback if any test fails.

### Risk 2: Over-tuning on 13 Receipts
**Mitigation**: Add 10+ new test receipts before claiming Phase 1 success. Target: 20+ receipts tested.

### Risk 3: Phase 2 Integration Breaks Phase 1
**Mitigation**: Keep Phase 2 code behind feature flag. Test both paths.

### Risk 4: Database Maintenance Burden
**Mitigation**: Auto-learn from user corrections. Add aliases automatically.

---

**Last Updated**: 2026-02-12
**Status**: Ready for Implementation
**Next**: Begin Week 1, Day 1-2 (Candidate pipeline refactoring)
