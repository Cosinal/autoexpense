# Test Receipt Data Structure

This directory contains real PDF receipts used for parser accuracy testing.

## Directory Structure

```
receipts/
├── passed/          # Receipts that currently parse correctly
├── failed/          # Receipts that currently fail (known issues)
├── edge_cases/      # Edge cases (handwritten, faded, multi-page, etc.)
└── README.md        # This file
```

## Adding New Test Receipts

### Step 1: Add the PDF File

Place your PDF receipt in the appropriate folder:
- `passed/` - If parser currently extracts correctly
- `failed/` - If parser currently fails to extract correctly
- `edge_cases/` - For unusual formats (handwritten, faded, multi-page)

**Naming convention**: `vendor_name_YYYYMMDD_description.pdf`

Examples:
- `starbucks_20240115_latte.pdf`
- `amazon_20240205_books.pdf`
- `uber_20220310_trip.pdf`

### Step 2: Create Expected Results File

Create a JSON file with the same name but `.json` extension:

**Format**: `vendor_name_YYYYMMDD_description.json`

**Contents**:
```json
{
  "vendor": "Starbucks",
  "amount": "5.93",
  "date": "2024-01-15",
  "currency": "CAD",
  "tax": "0.68",
  "notes": "Brick and mortar cafe receipt with HST 13%"
}
```

### Step 3: Run Tests

```bash
cd src/backend
python3 tests/test_parser_bulk.py
```

This will:
1. Process all PDFs through OCR
2. Parse the extracted text
3. Compare against expected results
4. Generate accuracy report

## Expected Results Schema

```json
{
  "vendor": "string",           // Expected vendor name (null if should fail)
  "amount": "decimal_string",   // Expected amount (null if should fail)
  "date": "YYYY-MM-DD",         // Expected date (null if should fail)
  "currency": "CAD|USD|EUR",    // Expected currency (null if not specified)
  "tax": "decimal_string",      // Expected tax (null if no tax)
  "notes": "string"             // Description of receipt format/challenges
}
```

## Tips for Good Test Coverage

### Vendor Diversity
- Major chains: Starbucks, Walmart, Amazon, Tim Hortons
- Regional stores: Local businesses
- Online services: Steam, LinkedIn, Apple
- Service providers: Consultants, lawyers, contractors

### Format Variety
- Email receipts (text-heavy)
- Printed receipts (point-of-sale)
- Invoices (professional services)
- Online marketplace (Amazon, eBay)
- Subscription services (SaaS products)

### Tax Scenarios
- Single tax (GST 5%)
- Dual tax (GST 5% + PST 7%)
- HST (13%)
- No tax (services, digital goods)
- International (VAT, etc.)

### Edge Cases
- Handwritten receipts
- Faded/low quality scans
- Multi-page invoices
- Receipts with logos/graphics
- Rotated or skewed scans
- Multiple languages

## Privacy Note

**IMPORTANT**: Only use receipts where you're comfortable sharing the data.
- Redact personal information if needed
- Don't include receipts with sensitive data
- Consider using public/demo receipts for testing

## Current Test Coverage

**Total Receipts**: TBD
**Major Vendors**: TBD
**Edge Cases**: TBD
**Pass Rate**: TBD

(Updated by test_parser_bulk.py)
