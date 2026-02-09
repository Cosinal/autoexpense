#!/usr/bin/env python3
"""
Test critical parser fixes against the 4 main problem receipts.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.parser import ReceiptParser
from decimal import Decimal

def test_sephora():
    """Test Sephora - Multi-tax summation (GST + HST)."""
    print("\n" + "="*80)
    print("TEST 1: SEPHORA (Multi-Tax Summation)")
    print("="*80)
    print("Expected: Amount=$59.52, Tax=$7.32 (GST $2.62 + HST $4.70)")

    with open('documentation/failed_receipts/email_19c33910.txt') as f:
        text = f.read()

    parser = ReceiptParser()
    result = parser.parse(text)

    print(f"\nResults:")
    print(f"  Amount: ${result['amount']}")
    print(f"  Tax: ${result['tax']}")
    print(f"  Vendor: {result['vendor']}")

    # Check results
    amount_ok = result['amount'] == Decimal('59.52')
    tax_ok = result['tax'] == Decimal('7.32')
    vendor_ok = result['vendor'] and 'sephora' in result['vendor'].lower()

    print(f"\n  Amount Match: {'✓' if amount_ok else '✗'}")
    print(f"  Tax Match: {'✓' if tax_ok else '✗'}")
    print(f"  Vendor Match: {'✓' if vendor_ok else '✗'}")

    passed = amount_ok and tax_ok and vendor_ok
    print(f"\n{'✓ TEST PASSED' if passed else '✗ TEST FAILED'}")
    return passed


def test_urban_outfitters():
    """Test Urban Outfitters - Order Summary total extraction."""
    print("\n" + "="*80)
    print("TEST 2: URBAN OUTFITTERS (Order Summary Total)")
    print("="*80)
    print("Expected: Amount=$93.79, Tax=$10.79")

    with open('documentation/failed_receipts/email_19c33917.txt') as f:
        text = f.read()

    parser = ReceiptParser()
    result = parser.parse(text)

    print(f"\nResults:")
    print(f"  Amount: ${result['amount']}")
    print(f"  Tax: ${result['tax']}")
    print(f"  Vendor: {result['vendor']}")

    # Check results
    amount_ok = result['amount'] == Decimal('93.79')
    tax_ok = result['tax'] == Decimal('10.79')

    print(f"\n  Amount Match: {'✓' if amount_ok else '✗'} (Should be $93.79, NOT $54.00)")
    print(f"  Tax Match: {'✓' if tax_ok else '✗'}")

    passed = amount_ok and tax_ok
    print(f"\n{'✓ TEST PASSED' if passed else '✗ TEST FAILED'}")
    return passed


def test_psa_canada():
    """Test PSA Canada - Total not subtotal."""
    print("\n" + "="*80)
    print("TEST 3: PSA CANADA (Total vs Subtotal)")
    print("="*80)
    print("Expected: Amount=$153.84, Tax=$18.89, Vendor=PSA Canada")

    with open('documentation/failed_receipts/PSA_Canada.txt') as f:
        text = f.read()

    parser = ReceiptParser()
    result = parser.parse(text)

    print(f"\nResults:")
    print(f"  Amount: ${result['amount']}")
    print(f"  Tax: ${result['tax']}")
    print(f"  Vendor: {result['vendor']}")

    # Check results
    amount_ok = result['amount'] == Decimal('153.84')
    tax_ok = result['tax'] == Decimal('18.89')
    vendor_ok = result['vendor'] and 'psa' in result['vendor'].lower()

    print(f"\n  Amount Match: {'✓' if amount_ok else '✗'} (Should be $153.84, NOT $134.95)")
    print(f"  Tax Match: {'✓' if tax_ok else '✗'}")
    print(f"  Vendor Match: {'✓' if vendor_ok else '✗'}")

    passed = amount_ok and tax_ok and vendor_ok
    print(f"\n{'✓ TEST PASSED' if passed else '✗ TEST FAILED'}")
    return passed


def test_geoguessr():
    """Test GeoGuessr - Date, tax, vendor."""
    print("\n" + "="*80)
    print("TEST 4: GEOGUESSR (Ordinal Date, Tax, Vendor)")
    print("="*80)
    print("Expected: Amount=$6.99, Tax=$0.33, Date=2025-11-23, Vendor=GeoGuessr")

    with open('documentation/failed_receipts/GeoGuessr.txt') as f:
        text = f.read()

    parser = ReceiptParser()
    result = parser.parse(text)

    print(f"\nResults:")
    print(f"  Amount: ${result['amount']}")
    print(f"  Tax: ${result['tax']}")
    print(f"  Date: {result['date']}")
    print(f"  Vendor: {result['vendor']}")

    # Check results
    amount_ok = result['amount'] == Decimal('6.99')
    tax_ok = result['tax'] == Decimal('0.33')
    date_ok = result['date'] == '2025-11-23'
    vendor_ok = result['vendor'] and 'geoguessr' in result['vendor'].lower()

    print(f"\n  Amount Match: {'✓' if amount_ok else '✗'}")
    print(f"  Tax Match: {'✓' if tax_ok else '✗'}")
    print(f"  Date Match: {'✓' if date_ok else '✗'} (from ordinal '23rd November 2025')")
    print(f"  Vendor Match: {'✓' if vendor_ok else '✗'}")

    passed = amount_ok and tax_ok and date_ok and vendor_ok
    print(f"\n{'✓ TEST PASSED' if passed else '✗ TEST FAILED'}")
    return passed


def main():
    """Run all critical tests."""
    print("="*80)
    print("CRITICAL PARSER FIXES VALIDATION")
    print("="*80)

    results = []

    # Run tests
    results.append(("Sephora (Multi-Tax)", test_sephora()))
    results.append(("Urban Outfitters (Order Summary)", test_urban_outfitters()))
    results.append(("PSA Canada (Total vs Subtotal)", test_psa_canada()))
    results.append(("GeoGuessr (Ordinal Date)", test_geoguessr()))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")

    if total_passed == len(results):
        print("\n✓ ALL CRITICAL FIXES WORKING!")
        print("Parser improvements successfully validated.")
    else:
        print("\n✗ SOME TESTS FAILED")
        print("Review implementation and debug failing tests.")


if __name__ == '__main__':
    main()
