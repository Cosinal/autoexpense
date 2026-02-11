# Parser Baseline Accuracy Report

**Date**: 2026-02-10
**Test Suite**: test_parser_accuracy.py
**Test Cases**: 14 receipts (10 major vendors + 4 edge cases)

---

## Overall Results

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| **Overall Accuracy** | **80.0%** | **90.0%** | **-10.0%** |

### Per-Field Accuracy

| Field | Correct | Total | Accuracy | Target | Status |
|-------|---------|-------|----------|--------|--------|
| **Date** | 14/14 | 14 | **100.0%** | 90% | ✅ **EXCEEDS TARGET** |
| **Amount** | 12/14 | 14 | **85.7%** | 90% | ⚠️ Close to target |
| **Vendor** | 11/14 | 14 | **78.6%** | 90% | ❌ Below target |
| **Tax** | 10/14 | 14 | **71.4%** | 90% | ❌ Below target |
| **Currency** | 9/14 | 14 | **64.3%** | 90% | ❌ **WORST PERFORMER** |

---

## Test Results by Vendor

| Vendor | Status | Issues |
|--------|--------|--------|
| Uber | ✅ PASS | All fields correct |
| Steam | ✅ PASS | All fields correct |
| Sephora | ✅ PASS | All fields correct (dual tax) |
| Costco | ✅ PASS | All fields correct |
| Starbucks | ❌ FAIL | Tax: Expected 0.68, Got 6.61 (wrong extraction) |
| Amazon.ca | ❌ FAIL | Tax: Expected 1.00, Got None (missing) |
| Walmart | ❌ FAIL | Currency: Expected CAD, Got None (missing) |
| LinkedIn | ❌ FAIL | Amount: Expected 24.99, Got 23.80 (subtotal vs total) |
| GeoGuessr | ❌ FAIL | Vendor: Got "Market Ltd" instead of "GeoGuessr", Tax missing |
| Apple | ❌ FAIL | Currency: Expected USD, Got None (missing) |
| Handwritten Note | ❌ FAIL | Currency: Expected CAD, Got None (missing) |
| Faded Receipt | ❌ FAIL | Currency + Tax missing (expected behavior for faded) |
| No Tax Receipt | ❌ FAIL | Currency: Expected CAD, Got None (missing) |
| Refund | ❌ FAIL | Amount: Negative amounts not supported |

**Pass Rate**: 4/14 (28.6% fully correct)

---

## Critical Issues Identified

### 1. Currency Detection (64.3% - CRITICAL)

**Problem**: Many receipts don't have currency detected at all.

**Failing Cases**:
- Walmart: No currency found
- Apple: USD not detected
- Handwritten Note: CAD not detected
- Faded Receipt: CAD not detected
- No Tax Receipt: CAD not detected

**Root Cause**: Parser likely defaults to None when no explicit currency symbol or code found. Needs better inference (e.g., from location, tax type, or patterns).

**Recommended Fix**:
- Add default currency (CAD) for Canadian tax indicators (HST, GST, PST)
- Detect "CDN$", "CA$", "USD", "$" with context
- Infer from vendor country of origin

---

### 2. Tax Extraction (71.4% - HIGH PRIORITY)

**Problem**: Tax missing or incorrectly extracted in several cases.

**Failing Cases**:
- Starbucks: Extracted 6.61 instead of 0.68 (wrong line)
- Amazon.ca: Tax 1.00 not detected (CDN$ prefix issue)
- GeoGuessr: Tax 0.33 not detected (multi-line format)
- Faded Receipt: Tax 1.75 not detected (partial text)

**Root Cause**:
- Tax patterns miss some formats (CDN$ prefix, multi-line tax)
- Incorrect line selection (picking wrong tax line)
- Deduplication issues

**Recommended Fix**:
- Add pattern for "Tax (TYPE X%)" format
- Improve deduplication by span position (already planned)
- Add CDN$ and CA$ prefixes to tax patterns

---

### 3. Vendor Extraction (78.6% - MEDIUM PRIORITY)

**Problem**: Some vendor names incorrectly extracted.

**Failing Cases**:
- GeoGuessr: Extracted "Market Ltd" instead of "GeoGuessr"
- Faded Receipt: No vendor (expected - faded text)
- Refund: No vendor (expected - generic receipt)

**Root Cause**:
- Payment processor detection extracts wrong entity ("Paddle.com Market Ltd" instead of "GeoGuessr")
- Person name detection might be too aggressive

**Recommended Fix**:
- Improve payment processor logic (extract real vendor from "PADDLE.NET* GEOGUESSR")
- Better scoring for business names vs generic entities

---

### 4. Amount Extraction (85.7% - LOW PRIORITY)

**Problem**: Subtotal vs total confusion, negative amounts not supported.

**Failing Cases**:
- LinkedIn: Extracted subtotal 23.80 instead of total 24.99
- Refund: Negative amount -45.99 not supported (returned None)

**Root Cause**:
- Subtotal appears before total, gets higher priority
- Negative amount patterns not implemented

**Recommended Fix**:
- Improve total vs subtotal disambiguation (give "Total" higher priority)
- Add negative amount support for refunds

---

### 5. Date Extraction (100.0% - PERFECT ✅)

**No issues**: All dates correctly extracted, including edge cases like:
- Ordinal dates ("23rd November 2025")
- MM/DD/YYYY formats
- Written months ("Feb 1, 2024")

**No action needed**.

---

## Prioritized Improvements

Based on impact on overall accuracy:

### Phase 1: Quick Wins (Low Effort, High Impact)
1. **Currency defaulting** - Add CAD default for Canadian receipts (5% improvement)
2. **Tax pattern additions** - Add CDN$ and CA$ patterns (3% improvement)
3. **Total vs Subtotal** - Boost "Total" priority (1% improvement)

**Expected Accuracy**: 80% → 89% (+9%)

---

### Phase 2: Medium Effort Fixes
4. **Vendor extraction refinement** - Fix payment processor logic (2% improvement)
5. **Tax deduplication** - Fix span-based dedup (already planned)
6. **Negative amount support** - Add refund handling (1% improvement)

**Expected Accuracy**: 89% → 92% (+3%)

---

### Phase 3: Edge Case Handling
7. **Faded receipt tolerance** - Improve partial text handling
8. **Handwritten receipt support** - Better OCR preprocessing

**Expected Accuracy**: 92% → 95%+ (with better OCR)

---

## Next Steps

1. **Commit baseline** - Save this test suite and baseline results
2. **Start Phase 1 improvements** - Focus on currency and tax
3. **Re-run tests** - Measure improvement after each fix
4. **Track progress** - Update this document with new accuracy after changes

---

## Test Suite Expansion Plan

To reach 50+ test cases (current: 14):

**Add**:
- 10 more major vendors (Target, Best Buy, Home Depot, McDonald's, Tim Hortons, etc.)
- 10 international vendors (UK VAT, EU receipts, Asian formats)
- 6 service receipts (lawyers, consultants, contractors)
- 5 more edge cases (multi-page PDFs, scanned images, partial OCR)
- 5 duplicate scenarios (same vendor, different formats)

**Target**: 50 test cases by end of Task 1

---

**Last Updated**: 2026-02-10
**Next Review**: After Phase 1 improvements
