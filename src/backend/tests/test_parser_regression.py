#!/usr/bin/env python3
"""
Regression test suite for the refactored ReceiptParser.
Uses synthetic snippets based on known vendor receipt formats.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.parser import ReceiptParser
from decimal import Decimal


STEAM_RECEIPT = """\
From: Steam <noreply@steampowered.com>
Date: Mon, Jan 15, 2024

Steam Receipt

| Item | Total
Game Purchase | 6.99 CAD
Subtotal | 6.99 CAD
Total | 6.99 CAD
"""

GEOGUESSR_RECEIPT = """\
Tax invoice
PAID
23rd November 2025 -
CA$6.99
via Paddle.com
Invoice from
Paddle.com Market Ltd
London EC1V 8BT
United Kingdom
Currency code:
CAD
GeoGuessr Unlimited
1
CA$6.66
5%
CA$6.66
Subtotal
CA$6.66
Sales Tax
CA$0.33
Total
CA$6.99
Amount paid
CA$6.99
Tax breakdown
Tax %
Tax
5%
CA$0.33
Tax total
CA$0.33
The CA$6.99 payment will appear on your bank/card statement as:
PADDLE.NET* GEOGUESSR
"""

LINKEDIN_RECEIPT = """\
From: LinkedIn <receipts@linkedin.com>
Date: Feb 1, 2024
GST : 5%
CA $ 23.80
CA $ 1.19
Subtotal CA $ 23.80
Total CA $ 24.99
"""

UBER_RECEIPT = """\
From: **Uber Receipts** <noreply@uber.com>
Date: Thu, Mar 10, 2022
Trip Fare | $12.50
HST | $1.63
Total: | $14.13
"""

SEPHORA_RECEIPT = """\
From: **Sephora** <shop@beauty.sephora.com>
Date: Sat, Sep 6, 2025
Subtotal: $52.20
CANADA GST/TPS (5%): $2.62
NOVA SCOTIA HST (9%): $4.70
**Total: $59.52**
"""

WALMART_RECEIPT = """\
Walmart
Date: 12/15/2023
Subtotal $45.00
Tax $3.15
Total $48.15
"""

APPLE_RECEIPT = """\
Apple
Date: Nov 20, 2024
Amount Paid: $9.99
"""


def test_steam_pipe_table():
    """Steam — pipe table format, CAD, no tax."""
    parser = ReceiptParser()
    result = parser.parse(STEAM_RECEIPT)
    assert result['amount'] == Decimal('6.99'), f"Expected 6.99, got {result['amount']}"
    assert result['currency'] == 'CAD', f"Expected CAD, got {result['currency']}"
    print("✓ test_steam_pipe_table")


def test_geoguessr_payment_processor():
    """Paddle/GeoGuessr — payment processor detection, ordinal date, multi-line tax."""
    parser = ReceiptParser()
    result = parser.parse(GEOGUESSR_RECEIPT)
    assert result['amount'] == Decimal('6.99'), f"Expected 6.99, got {result['amount']}"
    assert result['tax'] == Decimal('0.33'), f"Expected 0.33, got {result['tax']}"
    assert result['date'] == '2025-11-23', f"Expected 2025-11-23, got {result['date']}"
    assert result['vendor'] and 'geoguessr' in result['vendor'].lower(), \
        f"Expected geoguessr in vendor, got {result['vendor']}"
    print("✓ test_geoguessr_payment_processor")


def test_linkedin_gst():
    """LinkedIn — multi-line GST with percentage."""
    parser = ReceiptParser()
    result = parser.parse(LINKEDIN_RECEIPT)
    assert result['currency'] == 'CAD', f"Expected CAD, got {result['currency']}"
    print("✓ test_linkedin_gst")


def test_uber_from_header():
    """Uber — From: header vendor extraction, HST."""
    parser = ReceiptParser()
    result = parser.parse(UBER_RECEIPT)
    assert result['vendor'] and 'uber' in result['vendor'].lower(), \
        f"Expected uber in vendor, got {result['vendor']}"
    assert result['amount'] == Decimal('14.13'), f"Expected 14.13, got {result['amount']}"
    print("✓ test_uber_from_header")


def test_sephora_dual_tax():
    """Sephora — dual-tax summation (GST + HST), markdown bold total."""
    parser = ReceiptParser()
    result = parser.parse(SEPHORA_RECEIPT)
    assert result['amount'] == Decimal('59.52'), f"Expected 59.52, got {result['amount']}"
    assert result['tax'] == Decimal('7.32'), f"Expected 7.32 (2.62+4.70), got {result['tax']}"
    assert result['vendor'] and 'sephora' in result['vendor'].lower(), \
        f"Expected sephora in vendor, got {result['vendor']}"
    print("✓ test_sephora_dual_tax")


def test_walmart_generic():
    """Walmart — generic format."""
    parser = ReceiptParser()
    result = parser.parse(WALMART_RECEIPT)
    assert result['vendor'] == 'Walmart', f"Expected Walmart, got {result['vendor']}"
    assert result['amount'] == Decimal('48.15'), f"Expected 48.15, got {result['amount']}"
    assert result['tax'] == Decimal('3.15'), f"Expected 3.15, got {result['tax']}"
    print("✓ test_walmart_generic")


def test_apple_app_store():
    """Apple — app store format with explicit amount paid."""
    parser = ReceiptParser()
    result = parser.parse(APPLE_RECEIPT)
    assert result['vendor'] == 'Apple', f"Expected Apple, got {result['vendor']}"
    assert result['amount'] == Decimal('9.99'), f"Expected 9.99, got {result['amount']}"
    print("✓ test_apple_app_store")


def test_debug_metadata_present():
    """Verifies parse() returns 'debug' key with expected structure."""
    parser = ReceiptParser()
    result = parser.parse(SEPHORA_RECEIPT)
    assert 'debug' in result, "Expected 'debug' key in result"
    debug = result['debug']
    assert 'patterns_matched' in debug, "Expected 'patterns_matched' in debug"
    assert 'confidence_per_field' in debug, "Expected 'confidence_per_field' in debug"
    assert 'warnings' in debug, "Expected 'warnings' in debug"
    # At least amount should be recorded since Sephora has a clear total
    assert 'amount' in debug['patterns_matched'], \
        f"Expected 'amount' in patterns_matched, got {debug['patterns_matched']}"
    print("✓ test_debug_metadata_present")


def test_tax_dedup_different_values():
    """Two taxes with different values (GST + HST) at different positions sum correctly."""
    # Sephora has $2.62 (GST) and $4.70 (HST) — both should be counted
    receipt = """\
CANADA GST/TPS (5%): $2.62
NOVA SCOTIA HST (9%): $4.70
**Total: $59.52**
"""
    parser = ReceiptParser()
    result = parser.parse(receipt)
    assert result['tax'] == Decimal('7.32'), \
        f"Expected 7.32 (2.62 + 4.70), got {result['tax']}"
    print("✓ test_tax_dedup_different_values")


def main():
    """Run all regression tests."""
    print("=" * 60)
    print("PARSER REGRESSION TESTS")
    print("=" * 60)

    tests = [
        test_steam_pipe_table,
        test_geoguessr_payment_processor,
        test_linkedin_gst,
        test_uber_from_header,
        test_sephora_dual_tax,
        test_walmart_generic,
        test_apple_app_store,
        test_debug_metadata_present,
        test_tax_dedup_different_values,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: UNEXPECTED ERROR: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"Total: {passed}/{len(tests)} passed")
    if failed == 0:
        print("✓ ALL REGRESSION TESTS PASSED")
    else:
        print(f"✗ {failed} TEST(S) FAILED")
    print("=" * 60)

    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
