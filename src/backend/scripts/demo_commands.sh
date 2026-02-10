#!/bin/bash
# Demo Commands Cheat Sheet
# Copy and paste these during your demo

# ====================
# SETUP
# ====================

# Start server (keep this running)
# uvicorn app.main:app --reload --port 8000

# Test server is running
curl http://localhost:8000/health

# Open API docs in browser
# open http://localhost:8000/docs

# ====================
# DEMO 1: PSA CANADA
# Complex receipt - Total vs Subtotal
# ====================

echo "Demo 1: PSA Canada - Complex Receipt"
curl -X POST "http://localhost:8000/upload" \
  -F "file=@documentation/failed_receipts/PSA_Canada.pdf" \
  -F "user_id=00000000-0000-0000-0000-000000000001" \
  | python3 -m json.tool

# Expected:
# - Amount: 153.84 (NOT 134.95 subtotal)
# - Tax: 18.89
# - Currency: CAD
# - Vendor: Contains "PSA"

# ====================
# DEMO 2: SEPHORA
# Multi-tax summation (GST + HST)
# ====================

echo ""
echo "Demo 2: Sephora - Multi-Tax Summation"
echo "(Note: No PDF available, using text file for parser testing)"
# curl -X POST "http://localhost:8000/upload" \
#   -F "file=@documentation/failed_receipts/email_19c33910.txt" \
#   -F "user_id=00000000-0000-0000-0000-000000000001" \
#   | python3 -m json.tool

# Expected:
# - Amount: 59.52
# - Tax: 7.32 (GST 2.62 + HST 4.70)
# - Vendor: Sephora
# - Confidence: > 0.9

# ====================
# DEMO 3: URBAN OUTFITTERS
# Order summary total extraction
# ====================

echo ""
echo "Demo 3: Urban Outfitters - Order Summary"
echo "(Note: No PDF available, using text file for parser testing)"
# curl -X POST "http://localhost:8000/upload" \
#   -F "file=@documentation/failed_receipts/email_19c33917.txt" \
#   -F "user_id=00000000-0000-0000-0000-000000000001" \
#   | python3 -m json.tool

# Expected:
# - Amount: 93.79 (order total, NOT 54.00 item price)
# - Tax: 10.79
# - Vendor: Urban Outfitters

# ====================
# DEMO 4: GEOGUESSR
# Auto-review flagging (payment processor)
# ====================

echo ""
echo "Demo 4: GeoGuessr - Review Flagging"
curl -X POST "http://localhost:8000/upload" \
  -F "file=@documentation/failed_receipts/GeoGuessr.pdf" \
  -F "user_id=00000000-0000-0000-0000-000000000001" \
  | python3 -m json.tool

# Expected:
# - Amount: 6.99
# - needs_review: true/false (depends on confidence)
# - Vendor: May be payment processor
# - Shows provenance in debug

# ====================
# PRETTY PRINT HELPERS
# ====================

# Extract just the key fields
extract_key_fields() {
    python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Vendor: {data.get('vendor', 'N/A')}\")
print(f\"Amount: {data.get('amount', 'N/A')}\")
print(f\"Currency: {data.get('currency', 'N/A')}\")
print(f\"Tax: {data.get('tax', 'N/A')}\")
print(f\"Date: {data.get('date', 'N/A')}\")
print(f\"Confidence: {data.get('confidence', 'N/A')}\")
print(f\"Needs Review: {data.get('needs_review', 'N/A')}\")
"
}

# Usage:
# curl ... | extract_key_fields

# ====================
# SHOW DEBUG METADATA
# ====================

show_debug() {
    python3 -c "
import sys, json
data = json.load(sys.stdin)
debug = data.get('ingestion_debug', {})
print(json.dumps(debug, indent=2))
"
}

# Usage:
# curl ... | show_debug

# ====================
# LIST ALL RECEIPTS
# ====================

# Get all receipts for the test user
curl -X GET "http://localhost:8000/receipts?user_id=00000000-0000-0000-0000-000000000001" \
  | python3 -m json.tool

# ====================
# GET SPECIFIC RECEIPT
# ====================

# Replace {receipt_id} with actual ID from previous upload
# curl -X GET "http://localhost:8000/receipts/{receipt_id}" | python3 -m json.tool

# ====================
# SHOW CONFIDENCE DISTRIBUTION
# ====================

show_confidence_stats() {
    curl -s -X GET "http://localhost:8000/receipts?user_id=00000000-0000-0000-0000-000000000001" \
      | python3 -c "
import sys, json
receipts = json.load(sys.stdin)
confidences = [r.get('confidence', 0) for r in receipts]
if confidences:
    print(f'Total receipts: {len(confidences)}')
    print(f'Avg confidence: {sum(confidences)/len(confidences):.2f}')
    print(f'Min: {min(confidences):.2f}, Max: {max(confidences):.2f}')
    needs_review = sum(1 for r in receipts if r.get('needs_review'))
    print(f'Needs review: {needs_review}/{len(receipts)}')
"
}

# ====================
# CLEANUP (Optional)
# ====================

# Delete a receipt (use after demo)
# curl -X DELETE "http://localhost:8000/receipts/{receipt_id}"

# ====================
# QUICK TEST ALL
# ====================

test_all() {
    echo "Testing all demo receipts..."

    for file in documentation/failed_receipts/*.txt; do
        echo ""
        echo "Testing: $file"
        curl -s -X POST "http://localhost:8000/upload" \
          -F "file=@$file" \
          -F "user_id=00000000-0000-0000-0000-000000000001" \
          | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"  ✓ Vendor: {data.get('vendor', 'N/A')}\")
print(f\"  ✓ Amount: {data.get('amount', 'N/A')}\")
print(f\"  ✓ Confidence: {data.get('confidence', 'N/A')}\")
"
    done
}

# ====================
# USAGE
# ====================

# To run a specific demo:
# bash demo_commands.sh

# To use functions:
# source demo_commands.sh
# test_all
# show_confidence_stats
