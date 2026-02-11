# Parser Testing Guide

**Purpose**: How to test parser accuracy with real PDF receipts

**Last Updated**: 2026-02-10

---

## Overview

We use two complementary testing approaches:

### 1. Synthetic Text Tests (`test_parser_accuracy.py`)
- **Purpose**: Fast iteration during development
- **Format**: Hardcoded text strings in Python
- **Pros**: No file dependencies, fast to run, easy to add edge cases
- **Cons**: Not realistic (no OCR errors, perfect text)
- **Use case**: Quick validation during development

### 2. Real PDF Tests (`test_parser_bulk.py`)
- **Purpose**: Realistic accuracy measurement
- **Format**: Actual PDF receipts + expected results JSON
- **Pros**: Tests full pipeline (OCR → Parse), realistic OCR errors
- **Cons**: Slower, requires real receipts
- **Use case**: Final validation, regression testing, accuracy benchmarking

---

## Quick Start: Adding Real PDF Receipts

### Automated Workflow (Recommended)

The fastest way to add new test receipts:

**Step 1: Add PDF files to any folder**

```bash
# Put your PDFs in the failed/ folder (recommended starting point)
cp ~/Downloads/receipt*.pdf src/backend/tests/data/receipts/failed/
```

**Step 2: Auto-generate JSON metadata**

```bash
cd src/backend
python3 tests/generate_expected_results.py
```

This will:
- Find all PDFs without matching JSON files
- Run OCR + parser on each PDF
- Generate JSON files with extracted values
- Show you what was extracted

**Step 3: Review and correct**

Open each generated JSON file and:
- Verify extracted values are correct
- Fix any errors
- Update the `notes` field with description
- For vendor names, use shortest version (e.g., "Irving Oil" not "Irving Oil Limited")

**Step 4: Run tests**

```bash
python3 tests/test_parser_bulk.py
```

---

### Manual Workflow (If Needed)

If you prefer to create JSON files manually:

### Step 1: Organize Your PDFs

Place receipts in the appropriate folder:

```
tests/data/receipts/
├── passed/       # Receipts that currently parse correctly
├── failed/       # Receipts that currently fail
└── edge_cases/   # Unusual formats
```

**File naming**: `vendor_YYYYMMDD_description.pdf`

Examples:
- `starbucks_20240115_latte.pdf`
- `amazon_20240205_books.pdf`
- `uber_20220310_trip_downtown.pdf`

### Step 2: Create Expected Results

For each PDF, create a matching JSON file:

**File**: `starbucks_20240115_latte.json`
```json
{
  "vendor": "Starbucks",
  "amount": "5.93",
  "date": "2024-01-15",
  "currency": "CAD",
  "tax": "0.68",
  "notes": "Brick and mortar cafe receipt"
}
```

**Rules**:
- Use `null` if field should be missing (e.g., no tax)
- Use `null` if you expect extraction to fail (e.g., faded vendor name)
- Amounts and tax as strings (will be converted to Decimal)
- Date in YYYY-MM-DD format
- Notes are optional but helpful for understanding failures

### Step 3: Run Bulk Tests

```bash
cd src/backend
python3 tests/test_parser_bulk.py
```

**Output**:
```
================================================================================
BULK PARSER TEST - 10 receipts
================================================================================

  Testing: starbucks_20240115_latte.pdf... ✓ PASS
  Testing: amazon_20240205_books.pdf... ✗ FAIL
  ...

================================================================================
BULK TEST SUMMARY
================================================================================

Total Receipts: 10
Fully Correct:  8/10 (80.0%)

Per-Field Accuracy:
  Vendor:   9/10 (90.0%)
  Amount:   8/10 (80.0%)
  Date:     10/10 (100.0%)
  Currency: 7/10 (70.0%)
  Tax:      8/10 (80.0%)

Overall Accuracy: 82.0%
Target Accuracy:  90.0%
```

### Step 4: Debug Failures

For detailed output on each receipt:

```bash
python3 tests/test_parser_bulk.py --verbose
```

This shows:
- OCR extracted text length
- Parsed values for each field
- Comparison with expected values
- Specific field failures

---

## Testing Workflow

### Top-Down Debugging Approach

1. **Measure Baseline**
   ```bash
   python3 tests/test_parser_bulk.py > baseline_report.txt
   ```
   - Record overall accuracy
   - Identify worst-performing fields
   - Note which vendors fail most

2. **Prioritize Fixes**
   - Fix lowest-accuracy fields first (biggest impact)
   - Group similar failures (e.g., all currency detection issues)
   - Start with simple fixes (pattern additions) before complex logic

3. **Implement Fix**
   - Make targeted changes to parser
   - Add relevant patterns or improve scoring

4. **Re-measure**
   ```bash
   python3 tests/test_parser_bulk.py
   ```
   - Compare new accuracy to baseline
   - Ensure no regressions (other fields didn't get worse)
   - Verify the specific failing receipts now pass

5. **Iterate**
   - Repeat until target accuracy reached (90%+)
   - Add more test receipts as you find edge cases

---

## Test Organization Strategy

### Folder Usage

**`passed/`**
- Receipts that currently parse correctly
- Use as regression tests (should never fail)
- Move here after fixing a receipt from `failed/`

**`failed/`**
- Receipts that currently fail
- Known issues to fix
- Move to `passed/` after fixing

**`edge_cases/`**
- Unusual formats (handwritten, faded, multi-page)
- May never reach 100% accuracy (that's OK)
- Helps prevent regressions when fixing common cases

### Coverage Goals

**By vendor type**:
- ✅ 5-10 major chains (Starbucks, Walmart, Amazon, etc.)
- ✅ 5 online services (Steam, LinkedIn, Apple, etc.)
- ✅ 5 local businesses (restaurants, shops, services)
- ✅ 3 professional services (consultants, lawyers, contractors)

**By format**:
- ✅ 10 email receipts (text-heavy)
- ✅ 10 printed receipts (point-of-sale)
- ✅ 5 invoices (professional)
- ✅ 5 online marketplace (Amazon, eBay)

**By tax scenario**:
- ✅ 5 GST only (5%)
- ✅ 5 HST (13%)
- ✅ 5 dual tax (GST + PST)
- ✅ 5 no tax (services, digital)

**By edge case**:
- ✅ 3 handwritten
- ✅ 3 faded/low quality
- ✅ 2 multi-page
- ✅ 2 rotated/skewed

**Total target**: 50+ receipts

---

## Advanced Usage

### Test Specific Folder Only

```bash
# Test only receipts currently passing
python3 tests/test_parser_bulk.py --folder passed

# Test only known failures
python3 tests/test_parser_bulk.py --folder failed

# Test only edge cases
python3 tests/test_parser_bulk.py --folder edge_cases
```

### Compare Before/After

```bash
# Before fix
python3 tests/test_parser_bulk.py > before.txt

# (make changes to parser)

# After fix
python3 tests/test_parser_bulk.py > after.txt

# Compare
diff before.txt after.txt
```

### Focus on Specific Field

When debugging a specific field (e.g., currency), you can:
1. Run bulk tests
2. Grep output for currency failures
3. Look at those specific receipts
4. Fix pattern/logic for that field
5. Re-run

---

## Expected Results Schema Reference

```json
{
  "vendor": "string or null",
  "amount": "decimal_string or null",
  "date": "YYYY-MM-DD or null",
  "currency": "CAD|USD|EUR|GBP or null",
  "tax": "decimal_string or null",
  "notes": "optional description"
}
```

**Field-specific rules**:

**`vendor`**:
- Match is case-insensitive substring
- "Starbucks" matches "STARBUCKS COFFEE" ✅
- "Uber" matches "Uber Receipts" ✅
- "Irving Oil" matches "Irving Oil Limited" ✅
- **Tip**: Use shortest, most recognizable version in JSON
- `null` means expect no vendor extraction

**`amount`**:
- Exact decimal match
- "45.99" must match exactly
- `null` means expect no amount extraction

**`date`**:
- Must be YYYY-MM-DD format
- "2024-02-10" must match exactly
- `null` means expect no date extraction

**`currency`**:
- Exact match (CAD, USD, EUR, GBP, etc.)
- `null` means expect no currency detection

**`tax`**:
- Exact decimal match
- For multi-tax (GST + PST), use total: "5.24" for 2.62+2.62
- `null` means expect no tax (not an error)

---

## Privacy & Security

**IMPORTANT**: Only use receipts where you're comfortable sharing the data.

**Options**:
1. **Redact personal info**: Use PDF editor to black out names, addresses
2. **Use public receipts**: Demo receipts from company websites
3. **Generate synthetic PDFs**: Create fake receipts for testing
4. **Don't commit sensitive data**: Add receipts to `.gitignore` if needed

**Recommendation**: For open-source testing, use:
- Public demo receipts from vendor websites
- Redacted versions of real receipts
- Synthetic test receipts you generate

---

## Tips for Success

### Good Test Receipts
- ✅ Clear, readable text (good OCR source)
- ✅ Typical format for that vendor
- ✅ Representative of common use case

### Poor Test Receipts
- ❌ Completely illegible (can't even read manually)
- ❌ Unique one-off format (not representative)
- ❌ Sensitive personal information

### Adding Receipts Incrementally

Start with:
1. **5 receipts you use most often** - Your common vendors
2. **5 receipts that failed in production** - Known issues
3. **5 receipts from major chains** - Common formats

Then expand to 50+ over time as you:
- Find edge cases in production
- Get feedback from beta users
- Discover new vendor formats

---

## Current Status

**Synthetic Tests**: 14 test cases, 80.0% accuracy
**PDF Tests**: TBD (waiting for PDF receipts)

**Next Steps**:
1. Add 10-15 PDF receipts to start
2. Run bulk tests to measure realistic accuracy
3. Compare synthetic vs PDF accuracy (OCR impact)
4. Expand to 50+ receipts over time

---

**Last Updated**: 2026-02-10
**Maintainer**: Engineering Team
