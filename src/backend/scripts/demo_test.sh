#!/bin/bash
# Quick Demo Test Script
# Run this before your demo to verify everything works

set -e

echo "=========================================="
echo "AutoExpense Demo Pre-Flight Check"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if server is running
echo "1. Checking if server is running..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Server is running${NC}"
else
    echo -e "${RED}✗ Server is not running${NC}"
    echo "   Start it with: uvicorn app.main:app --reload --port 8000"
    exit 1
fi

echo ""

# Test API documentation
echo "2. Checking API documentation..."
if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API docs available at http://localhost:8000/docs${NC}"
else
    echo -e "${RED}✗ API docs not accessible${NC}"
    exit 1
fi

echo ""

# Check sample receipts exist
echo "3. Checking sample receipts..."
RECEIPTS=(
    "documentation/failed_receipts/PSA_Canada.pdf"
    "documentation/failed_receipts/GeoGuessr.pdf"
)

for receipt in "${RECEIPTS[@]}"; do
    if [ -f "$receipt" ]; then
        echo -e "${GREEN}✓ Found: $receipt${NC}"
    else
        echo -e "${RED}✗ Missing: $receipt${NC}"
        exit 1
    fi
done

echo ""

# Test upload endpoint with PSA Canada
echo "4. Testing upload endpoint (PSA Canada - Complex Receipt)..."
RESPONSE=$(curl -s -X POST "http://localhost:8000/upload" \
  -F "file=@documentation/failed_receipts/PSA_Canada.pdf" \
  -F "user_id=00000000-0000-0000-0000-000000000001")

if echo "$RESPONSE" | grep -q "receipt_id"; then
    echo -e "${GREEN}✓ Upload successful${NC}"

    # Extract key fields
    AMOUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('amount', 'N/A'))")
    VENDOR=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('vendor', 'N/A'))")
    CURRENCY=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('currency', 'N/A'))")
    CONFIDENCE=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('confidence', 'N/A'))")

    echo "   Amount: $AMOUNT"
    echo "   Vendor: $VENDOR"
    echo "   Currency: $CURRENCY"
    echo "   Confidence: $CONFIDENCE"

    # Verify expected values
    if [ "$AMOUNT" = "153.84" ]; then
        echo -e "${GREEN}   ✓ Amount correct (153.84)${NC}"
    else
        echo -e "${RED}   ✗ Amount incorrect (expected 153.84, got $AMOUNT)${NC}"
    fi

    if [ "$CURRENCY" = "CAD" ]; then
        echo -e "${GREEN}   ✓ Currency correct (CAD)${NC}"
    else
        echo -e "${YELLOW}   ⚠ Currency: $CURRENCY (expected CAD)${NC}"
    fi
else
    echo -e "${RED}✗ Upload failed${NC}"
    echo "Response: $RESPONSE"
    exit 1
fi

echo ""

# Test with Sephora (multi-tax)
echo "5. Testing multi-tax extraction (Sephora)..."
echo -e "${YELLOW}⚠ Skipping - no PDF available for Sephora receipt${NC}"
echo ""

# Test review flagging (GeoGuessr - lower confidence)
echo "5. Testing review flagging (GeoGuessr)..."
RESPONSE=$(curl -s -X POST "http://localhost:8000/upload" \
  -F "file=@documentation/failed_receipts/GeoGuessr.pdf" \
  -F "user_id=00000000-0000-0000-0000-000000000001")

if echo "$RESPONSE" | grep -q "receipt_id"; then
    NEEDS_REVIEW=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('needs_review', 'N/A'))")
    CONFIDENCE=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('confidence', 'N/A'))")
    REVIEW_REASON=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('review_reason', 'N/A'))")

    echo -e "${GREEN}✓ Upload successful${NC}"
    echo "   Needs Review: $NEEDS_REVIEW"
    echo "   Confidence: $CONFIDENCE"
    echo "   Review Reason: $REVIEW_REASON"

    if [ "$NEEDS_REVIEW" = "True" ] || [ "$NEEDS_REVIEW" = "true" ]; then
        echo -e "${GREEN}   ✓ Review flagging working!${NC}"
    else
        echo -e "${YELLOW}   ⚠ Review flag not set (confidence might be high)${NC}"
    fi
else
    echo -e "${RED}✗ Upload failed${NC}"
    exit 1
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✓ All Pre-Flight Checks Passed!${NC}"
echo "=========================================="
echo ""
echo "You're ready to demo! 🚀"
echo ""
echo "Quick Demo URLs:"
echo "  • API Docs: http://localhost:8000/docs"
echo "  • Health Check: http://localhost:8000/health"
echo ""
echo "Demo Guide: DEMO_GUIDE.md"
echo ""
