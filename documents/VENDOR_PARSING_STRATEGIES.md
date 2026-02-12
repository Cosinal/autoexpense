# Vendor Parsing Strategies - Complete Analysis

**Status**: Research & Planning
**Date**: 2026-02-12
**Current Accuracy**: 46.2% (6/13 receipts)
**Target Accuracy**: 90%+

## Executive Summary

Vendor extraction is the most challenging field in receipt parsing, currently at 46.2% accuracy. This document explores all possible approaches to improve accuracy, including techniques likely used by industry leaders like Stripe, Ramp, Brex, and Expensify.

---

## Current Approach: Pattern-Based Structural Scoring

### What We Do Now
1. **Email metadata** (From: header, subject) - 0.9 score
2. **Body text patterns**:
   - "Payable to X" - 0.85 score
   - Business keywords (Clinic, Medical, etc.) - 0.75 score
   - Company suffixes (Inc, LLC, Ltd) - 0.7 score
   - Early lines (fallback) - 0.5 score
3. **Scoring adjustments**:
   - Title case: +0.1
   - Line position penalty: -0.02 per line after line 2
   - Person name penalty: -0.6 if looks like "First Last"

### Current Issues
- **46.2% accuracy** - Below acceptable threshold
- **OCR spacing artifacts**: "I N V O I C" instead of "INVOICE"
- **Multi-line confusion**: Extracting product names, document labels, customer names
- **Email forwarding**: Extracting forwarder name instead of original sender
- **Payment processor dominance**: Paddle/Stripe overshadowing actual merchant

---

## Industry Analysis: How Stripe/Ramp/Brex Do It

### 1. Machine Learning (Most Likely)
**What they probably use**: Computer Vision + NLP hybrid models

#### a) Vision Transformers (ViT / LayoutLM)
- **Model**: Microsoft's LayoutLMv3, Donut, or custom fine-tuned models
- **How it works**:
  - Treats receipt as an image + text
  - Learns spatial relationships (e.g., vendor usually top-left, bold, larger font)
  - Understands document structure without explicit rules
- **Accuracy**: 95-98% on diverse receipts
- **Training data**: Millions of receipts with human-labeled vendors

**Pros**:
- Handles ANY receipt format (no pattern engineering)
- Learns font size, position, styling as signals
- Robust to OCR errors (can read directly from image)
- Automatically adapts to new receipt types

**Cons**:
- Requires 10k-100k+ labeled receipts for training
- GPU infrastructure for inference ($)
- 500ms-2s latency per receipt
- Not feasible for solo developer without labeled dataset

#### b) Named Entity Recognition (NER) with BERT/RoBERTa
- **Model**: Fine-tuned BERT/RoBERTa on receipt text
- **How it works**:
  - Token-level classification: `[VENDOR]`, `[AMOUNT]`, `[DATE]`, etc.
  - Context-aware: understands "Invoice from X" vs "Bill to Y"
  - Transfer learning from general NER (companies, organizations)
- **Accuracy**: 85-92% on text-only
- **Training data**: 5k-50k receipts

**Pros**:
- Works on OCR text (no image needed)
- Faster inference than ViT (50-200ms)
- Can use pre-trained models (companies/organizations)
- Less training data than ViT

**Cons**:
- Still needs labeled data (though less)
- Loses spatial information (font size, position)
- Struggles with OCR errors

### 2. Knowledge Base / Vendor Database
**What they probably use**: Proprietary merchant database + fuzzy matching

#### Approach
1. **Database**: 1M+ known merchants with aliases
   - "Uber Technologies Inc." → "Uber"
   - "AMZN Marketplace" → "Amazon"
   - "Paddle.com Market Ltd" → Paddle (payment processor flag)
2. **Fuzzy matching**: Levenshtein distance, phonetic matching
3. **MCC codes**: Merchant Category Codes from card networks
4. **Transaction enrichment**: Use card transaction data to hint vendor

**Pros**:
- Instant lookup (< 5ms)
- No ML needed
- Works for known merchants (covers 80-90% of common vendors)
- Can normalize vendor names ("Uber Technologies" → "Uber")

**Cons**:
- Doesn't work for new/small vendors
- Database maintenance burden
- Requires initial database (licensing or scraping)
- Need to keep updated

### 3. Hybrid: Pattern-Based + LLM (Feasible for Us)
**What we could do**: Use patterns for extraction, LLM for validation/cleanup

#### Approach
1. **Extract candidates** using existing patterns (what we do now)
2. **LLM validation**: Send top 3 candidates to GPT-4/Claude with prompt:
   ```
   Receipt text: [first 30 lines]
   Candidate vendors: ["I N V O I C", "Anthropic", "HST Canada"]

   Which is the actual merchant/vendor? Return only the name.
   ```
3. **Cost**: $0.0001-0.0003 per receipt (100x cheaper than full LLM parsing)
4. **Latency**: 200-500ms (acceptable for background processing)

**Pros**:
- Improves accuracy from 46% → 85-90% estimated
- Handles edge cases patterns miss
- Corrects OCR errors ("I N V O I C" → "Anthropic")
- Distinguishes vendor from customer/product
- No training data needed

**Cons**:
- API cost: $0.10-0.30 per 1000 receipts
- Requires API key and network
- Privacy: sending receipt text to third party
- Latency: adds 200-500ms

### 4. Rule-Based + External APIs (Hybrid)
**What smaller companies might use**: Combine patterns with external services

#### Available Services
- **Google Cloud Vision API**: Document AI has vendor extraction
- **Amazon Textract**: Expense analysis feature
- **Azure Form Recognizer**: Receipt model with vendor field
- **Taggun API**: Receipt parsing API ($0.01-0.05 per receipt)

**Pros**:
- No training needed
- Battle-tested on millions of receipts
- Handles multiple formats out of the box

**Cons**:
- Cost: $0.01-0.10 per receipt
- Privacy concerns
- Vendor lock-in
- Network dependency

---

## Proposed Solutions (Short to Long Term)

### Phase 1: Quick Wins (Pattern Improvements) - 1-2 weeks
**Target**: 46% → 65%

1. **Fix OCR spacing normalization**
   - Apply only to header (first 15 lines) to avoid breaking amounts
   - More aggressive normalization: "I N V O I C" → "INVOICE"

2. **Improve person name detection**
   - Check if name appears in "From:" or "Bill To:" context
   - Use email domain hint (name@personal.com = person, name@company.com = maybe vendor)

3. **Better early-line scoring**
   - Boost score for lines 0-2 (+0.2 instead of +0.0)
   - Penalize lines with financial terms ("Subtotal", "Invoice To")
   - Prefer lines with business indicators

4. **Payment processor handling**
   - Detect "via X" patterns → skip X
   - Known processor list expansion
   - Look for "real" vendor on same receipt

5. **Multi-line vendor handling**
   - Combine adjacent capitalized lines (e.g., "Apple\nStore" → "Apple Store")
   - Detect split vendor names

**Estimated effort**: 10-15 hours
**Risk**: Low - incremental improvements
**Investment**: $0

---

### Phase 2: Vendor Database (Medium Term) - 2-4 weeks
**Target**: 65% → 80%

#### 2a. Build Core Database
1. **Seed from transaction data**:
   - Extract unique vendors from user's past receipts
   - Build mapping: OCR variations → canonical name
   - Example: "UBER TECH" / "Uber Technologies" → "Uber"

2. **Open-source databases**:
   - Merchant category codes (MCC) database
   - OpenCorporates business registry
   - Wikipedia company names / aliases

3. **Fuzzy matching**:
   - Levenshtein distance < 3 edits
   - Phonetic matching (Soundex, Metaphone)
   - Token overlap (Jaccard similarity)

**Implementation**:
```python
class VendorDatabase:
    def __init__(self):
        self.vendors = {}  # canonical name → aliases
        self.fuzzy_index = {}  # for fast lookup

    def lookup(self, text: str) -> Optional[str]:
        # Exact match
        if text in self.fuzzy_index:
            return self.fuzzy_index[text]

        # Fuzzy match (Levenshtein < 3)
        for canonical, aliases in self.vendors.items():
            for alias in aliases:
                if levenshtein(text, alias) <= 3:
                    return canonical

        return None
```

**Pros**:
- Fast (< 5ms per receipt)
- Handles common vendors well
- No API costs
- Privacy-preserving

**Cons**:
- Doesn't help with new/rare vendors
- Database maintenance

**Estimated effort**: 20-30 hours
**Risk**: Medium - database quality critical
**Investment**: $0 (open-source data)

---

### Phase 3: LLM-Assisted Validation (Medium Term) - 1-2 weeks
**Target**: 80% → 90%

#### Approach
Use LLM only for **low-confidence extractions** (< 0.7 confidence)

**Selective LLM call**:
```python
def extract_vendor_with_llm_fallback(text: str) -> str:
    # Step 1: Pattern-based extraction
    candidates = extract_vendor_candidates(text)
    best = select_best_vendor(candidates)

    if best.confidence >= 0.7:
        return best.value  # High confidence, no LLM needed

    # Step 2: LLM validation for low confidence
    top_3 = [c.value for c in candidates[:3]]

    prompt = f"""Receipt text (first 30 lines):
{text[:1500]}

Candidate vendors: {top_3}

Task: Identify the actual merchant/vendor name (the business that provided the service/product).
- Ignore: customer names, product names, payment processors (Stripe, Paddle, PayPal)
- Return: Just the vendor name, nothing else

Vendor:"""

    vendor = call_llm(prompt, max_tokens=20)
    return vendor.strip()
```

**Cost Analysis**:
- **Input tokens**: ~400 tokens (receipt excerpt + prompt)
- **Output tokens**: ~5 tokens (vendor name)
- **Cost per receipt**: $0.0002 (GPT-4o-mini) or $0.0001 (Claude Haiku)
- **If 30% need LLM**: $0.06-0.10 per 1000 receipts

**Accuracy projection**: 90-92%

**Pros**:
- Cost-effective (only for ambiguous cases)
- Handles edge cases patterns can't
- Corrects OCR errors
- No training needed

**Cons**:
- API dependency
- Privacy (can self-host with Ollama if needed)
- Latency (+200-500ms for 30% of receipts)

**Estimated effort**: 8-12 hours
**Risk**: Low - well-tested approach
**Investment**: $0.06-0.10 per 1000 receipts

---

### Phase 4: Machine Learning (Long Term) - 2-3 months
**Target**: 90% → 95%+

#### Option A: Fine-tune Pre-trained NER Model
**Model**: `dslim/bert-base-NER` or `Jean-Baptiste/camembert-ner`

**Approach**:
1. **Label data**: 1000-2000 receipts with vendor highlighted
2. **Fine-tune**: Transfer learning on receipt domain
3. **Inference**: Token classification → extract vendor entities
4. **Cost**: One-time GPU training ($50-100 on cloud)

**Pros**:
- Can run locally (no API)
- Fast inference (50-100ms)
- Privacy-preserving
- Works offline

**Cons**:
- Labeling effort (200-400 hours or $2k-5k for outsourcing)
- Model hosting (1GB model file)
- Training complexity

#### Option B: Document AI Model (LayoutLMv3 / Donut)
**Model**: Microsoft LayoutLMv3 or Naver Donut

**Approach**:
1. **Label data**: 2000-5000 receipts (vendor location + text)
2. **Fine-tune**: Vision + text model
3. **Inference**: Directly predict vendor from receipt image
4. **Cost**: $500-1000 GPU training time

**Pros**:
- Best accuracy (95-98%)
- Uses spatial layout (font size, position)
- Robust to OCR errors

**Cons**:
- Requires more labeled data
- GPU for inference (or slower CPU)
- Complex training pipeline

**Estimated effort**: 80-120 hours + labeling
**Risk**: High - ML expertise needed
**Investment**: $2k-5k (labeling) + $500-1000 (GPU)

---

## Recommendation: Hybrid Phased Approach

### Immediate (Week 1-2): Phase 1 - Pattern Improvements
**Goal**: 46% → 65%
**Effort**: 10-15 hours
**Cost**: $0

Focus on:
- Fix OCR normalization for vendor field
- Improve early-line scoring
- Better payment processor detection
- Person name filtering improvements

### Short-term (Week 3-4): Phase 2 - Vendor Database
**Goal**: 65% → 80%
**Effort**: 20-30 hours
**Cost**: $0

Build:
- 500-1000 common vendor database
- Fuzzy matching with Levenshtein distance
- Alias mappings (OCR variations)

### Medium-term (Week 5-6): Phase 3 - LLM Fallback
**Goal**: 80% → 90%
**Effort**: 8-12 hours
**Cost**: $0.06-0.10 per 1000 receipts

Implement:
- Selective LLM validation (confidence < 0.7)
- Cost-optimized prompts (< 500 tokens)
- Optional: self-hosted Ollama for privacy

### Long-term (3-6 months): Phase 4 - ML Model (Optional)
**Goal**: 90% → 95%+
**Decision point**: Only if processing 10k+ receipts/month

Consider:
- Fine-tuned NER model for text
- OR document AI model for vision + text
- Requires labeled training data

---

## Specific Fixes for Current Failures

### 1. Air Canada: "New" instead of "Air Canada"
**Root cause**: "Air Canada" on line with booking reference, skipped by filters
**Fix**: Look for airline names (Air X, X Airlines) with special handling
**Alternative**: Vendor database with "Air Canada" + aliases

### 2. Uber forwarded email: "Jorden Shaw" instead of "Uber"
**Root cause**: Forwarded email has "From: Jorden Shaw", original sender in body
**Fix**: Detect forwarded emails, look for "Original Message" or "From: X" in body
**Alternative**: Check email domain - personal domains = likely forwarder

### 3. Anthropic: "I N V O I C" (OCR spacing)
**Root cause**: OCR adds spaces, normalization not aggressive enough on early lines
**Fix**: More aggressive normalization for lines 0-10: collapse ANY multi-space
**Alternative**: LLM validation would auto-correct this

### 4. Browz Eyeware: Product name instead of vendor
**Root cause**: "Browz Eyeware" appears later, product name appears early
**Fix**: Business keyword "Eyeware" should boost score more (+0.3 instead of 0.75 base)
**Alternative**: Multi-line vendor detection (company name + business type)

### 5. GeoGuessr: "Invoice To" instead of vendor
**Root cause**: Skip pattern not catching "Invoice To" prefix
**Fix**: Add to skip patterns: `r'^\s*invoice\s+to\b'`
**Already added**: Just committed this fix!

### 6. receipt-test.jpg: "Patrick Cusack" (customer) instead of "Apple Store"
**Root cause**: Customer name appears early, Apple Store appears later
**Fix**: Boost vendor score for retail keywords ("Store", "Shop", "Market")
**Alternative**: Person name penalty should be higher (-0.8 instead of -0.6)

---

## What Stripe/Ramp Are Actually Doing (Best Guess)

### Stripe's Likely Approach
Based on their engineering blog and ML publications:

1. **Primary**: LayoutLMv3 or custom document AI model
   - Trained on millions of receipts from Stripe customers
   - Predicts vendor, amount, date, tax simultaneously
   - Uses image + text + spatial layout
   - Accuracy: 95-98%

2. **Fallback**: Vendor database with 10M+ merchants
   - Scraped from business registries, web data
   - Updated from Stripe's own transaction data
   - Fuzzy matching with ML-based similarity

3. **Validation**: Human-in-the-loop for low confidence
   - Flag receipts with confidence < 0.85
   - Human reviewers label ambiguous cases
   - Feedback loop improves model

### Ramp/Brex's Likely Approach
Similar to Stripe, with emphasis on:

1. **Card transaction data**: Cross-reference receipt with card transaction
   - Transaction has MCC (Merchant Category Code) and merchant name
   - Use as ground truth hint for receipt parsing
   - Accuracy: 98-99% when transaction available

2. **Receipt-transaction matching**:
   - Match receipt amount ± 2% to card transaction
   - Match date within 3 days
   - Match merchant name (fuzzy)
   - If confident match → use transaction merchant name

3. **For cash receipts**: Fall back to ML model

### Expensify's Approach (Pre-ML Era)
From their public materials:

1. **SmartScan**: Pattern-based + OCR
2. **Human verification**: Receipts > $75 reviewed by humans
3. **Vendor database**: 100k+ common merchants
4. **User corrections**: Learn from user edits

**Accuracy**: 85-90% (pre-ML), now likely 95%+ with ML

---

## Action Items

### This Week (Phase 1)
- [ ] Fix OCR normalization to be more aggressive on early lines
- [ ] Improve early-line scoring (boost lines 0-2)
- [ ] Add retail keyword boost ("Store", "Shop", "Market")
- [ ] Enhance person name penalty (-0.8 instead of -0.6)
- [ ] Test on 13 receipts, target 65%+ vendor accuracy

### Next 2 Weeks (Phase 2)
- [ ] Build vendor database (500 merchants)
- [ ] Implement fuzzy matching (Levenshtein)
- [ ] Add airline/retail category detection
- [ ] Test on 13 receipts, target 80%+ vendor accuracy

### Month 2 (Phase 3)
- [ ] Implement LLM fallback for low confidence
- [ ] Set up cost monitoring
- [ ] Test on 13 receipts, target 90%+ vendor accuracy
- [ ] Evaluate if Phase 4 (ML) is needed

---

## References

- **Microsoft LayoutLMv3**: https://arxiv.org/abs/2204.08387
- **Naver Donut**: https://arxiv.org/abs/2111.15664
- **Document AI comparisons**: https://paperswithcode.com/task/document-information-extraction
- **Stripe ML blog**: https://stripe.com/blog/applied-ml
- **Tesseract bbox API**: https://github.com/tesseract-ocr/tesseract/wiki/APIExample

---

**Last Updated**: 2026-02-12
**Author**: Engineering Team
**Status**: Active Planning
