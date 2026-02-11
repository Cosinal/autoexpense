#!/usr/bin/env python3
"""
Comprehensive Parser Accuracy Test Suite

Measures baseline accuracy for vendor, amount, date, currency, and tax extraction
across a variety of real-world receipt formats.

Target Accuracy: 90%+ per field
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.parser import ReceiptParser
from decimal import Decimal
from datetime import date
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

@dataclass
class ExpectedReceipt:
    """Expected values for a receipt test case."""
    name: str
    text: str
    vendor: Optional[str] = None
    amount: Optional[Decimal] = None
    date: Optional[str] = None
    currency: Optional[str] = 'CAD'
    tax: Optional[Decimal] = None
    notes: str = ""

@dataclass
class AccuracyResults:
    """Accuracy measurement results."""
    total_tests: int = 0
    vendor_correct: int = 0
    amount_correct: int = 0
    date_correct: int = 0
    currency_correct: int = 0
    tax_correct: int = 0
    failures: List[Dict[str, Any]] = field(default_factory=list)

    def vendor_accuracy(self) -> float:
        return (self.vendor_correct / self.total_tests * 100) if self.total_tests > 0 else 0.0

    def amount_accuracy(self) -> float:
        return (self.amount_correct / self.total_tests * 100) if self.total_tests > 0 else 0.0

    def date_accuracy(self) -> float:
        return (self.date_correct / self.total_tests * 100) if self.total_tests > 0 else 0.0

    def currency_accuracy(self) -> float:
        return (self.currency_correct / self.total_tests * 100) if self.total_tests > 0 else 0.0

    def tax_accuracy(self) -> float:
        return (self.tax_correct / self.total_tests * 100) if self.total_tests > 0 else 0.0

    def overall_accuracy(self) -> float:
        total_fields = self.total_tests * 5  # 5 fields per test
        total_correct = (self.vendor_correct + self.amount_correct +
                        self.date_correct + self.currency_correct + self.tax_correct)
        return (total_correct / total_fields * 100) if total_fields > 0 else 0.0


# =============================================================================
# TEST CASES: Major Vendors
# =============================================================================

UBER_RECEIPT = ExpectedReceipt(
    name="Uber",
    text="""\
From: Uber Receipts <noreply@uber.com>
Date: Thu, Mar 10, 2022

Your trip with Uber

Trip Fare | $12.50
HST | $1.63
Total: | $14.13

Thank you for riding with Uber!
""",
    vendor="Uber",
    amount=Decimal('14.13'),
    date='2022-03-10',
    currency='CAD',
    tax=Decimal('1.63'),
    notes="From email header, pipe-separated HST"
)

STARBUCKS_RECEIPT = ExpectedReceipt(
    name="Starbucks",
    text="""\
STARBUCKS COFFEE
123 Main Street
Toronto, ON

Date: 01/15/2024
Time: 08:30 AM

Latte Grande         $5.25
Tax (HST 13%)        $0.68
---------------------------
Total                $5.93

Thank you for visiting!
""",
    vendor="Starbucks",
    amount=Decimal('5.93'),
    date='2024-01-15',
    currency='CAD',
    tax=Decimal('0.68'),
    notes="Brick and mortar cafe receipt"
)

AMAZON_RECEIPT = ExpectedReceipt(
    name="Amazon.ca",
    text="""\
From: Amazon.ca <shipment-tracking@amazon.ca>
Order Date: February 5, 2024

Order Total: CDN$ 45.99

Items Ordered:
Book Title - Qty: 1 - CDN$ 39.99
Shipping - CDN$ 5.00
Tax (GST): CDN$ 1.00

Amount Charged: CDN$ 45.99
""",
    vendor="Amazon",
    amount=Decimal('45.99'),
    date='2024-02-05',
    currency='CAD',
    tax=Decimal('1.00'),
    notes="Online retailer with CDN$ prefix"
)

STEAM_RECEIPT = ExpectedReceipt(
    name="Steam",
    text="""\
From: Steam <noreply@steampowered.com>
Date: Mon, Jan 15, 2024

Steam Receipt

| Item              | Total
| Game Purchase     | 6.99 CAD
| Subtotal          | 6.99 CAD
| Total             | 6.99 CAD

No sales tax applied.
""",
    vendor="Steam",
    amount=Decimal('6.99'),
    date='2024-01-15',
    currency='CAD',
    tax=None,
    notes="Gaming platform, pipe table format, no tax"
)

WALMART_RECEIPT = ExpectedReceipt(
    name="Walmart",
    text="""\
WALMART SUPERCENTER
456 Retail Blvd

12/15/2023  14:25

Groceries           $42.00
Household           $3.00

Subtotal            $45.00
Tax                 $3.15
---------------------------
TOTAL               $48.15

VISA ending in 1234
""",
    vendor="Walmart",
    amount=Decimal('48.15'),
    date='2023-12-15',
    currency='CAD',
    tax=Decimal('3.15'),
    notes="Big box retailer, MM/DD/YYYY date"
)

LINKEDIN_RECEIPT = ExpectedReceipt(
    name="LinkedIn",
    text="""\
From: LinkedIn <receipts@linkedin.com>
Date: Feb 1, 2024

LinkedIn Premium Subscription

GST : 5%
CA $ 23.80
CA $ 1.19

Subtotal       CA $ 23.80
GST (5%)       CA $ 1.19
Total          CA $ 24.99

Payment method: Visa ****1234
""",
    vendor="LinkedIn",
    amount=Decimal('24.99'),
    date='2024-02-01',
    currency='CAD',
    tax=Decimal('1.19'),
    notes="Multi-line GST with percentage, CA $ format"
)

SEPHORA_RECEIPT = ExpectedReceipt(
    name="Sephora",
    text="""\
From: Sephora <shop@beauty.sephora.com>
Date: Sat, Sep 6, 2025

Your Sephora Order

Subtotal:           $52.20
CANADA GST/TPS (5%): $2.62
NOVA SCOTIA HST (9%): $4.70
-------------------------
**Total: $59.52**

Thank you for shopping!
""",
    vendor="Sephora",
    amount=Decimal('59.52'),
    date='2025-09-06',
    currency='CAD',
    tax=Decimal('7.32'),  # GST 2.62 + HST 4.70
    notes="Dual-tax summation (GST + HST), markdown bold total"
)

GEOGUESSR_RECEIPT = ExpectedReceipt(
    name="GeoGuessr",
    text="""\
Tax invoice
PAID
23rd November 2025
CA$6.99
via Paddle.com

Invoice from
Paddle.com Market Ltd
London EC1V 8BT
United Kingdom

Currency code: CAD

GeoGuessr Unlimited         1    CA$6.66
                            5%   CA$6.66
Subtotal                         CA$6.66
Sales Tax                        CA$0.33
Total                            CA$6.99
Amount paid                      CA$6.99

Tax breakdown
Tax %        Tax
5%           CA$0.33
Tax total    CA$0.33

The CA$6.99 payment will appear on your bank/card statement as:
PADDLE.NET* GEOGUESSR
""",
    vendor="GeoGuessr",
    amount=Decimal('6.99'),
    date='2025-11-23',
    currency='CAD',
    tax=Decimal('0.33'),
    notes="Payment processor (Paddle), ordinal date, multi-line tax"
)

APPLE_RECEIPT = ExpectedReceipt(
    name="Apple",
    text="""\
Apple Inc.
One Apple Park Way
Cupertino, CA 95014

Date: Nov 20, 2024

App Store Purchase
App Name - Subscription

Amount Paid: $9.99
Payment Method: Apple Pay

No tax applied (digital service)
""",
    vendor="Apple",
    amount=Decimal('9.99'),
    date='2024-11-20',
    currency='USD',  # Apple uses USD
    tax=None,
    notes="App store format, explicit amount paid, no tax"
)

COSTCO_RECEIPT = ExpectedReceipt(
    name="Costco",
    text="""\
COSTCO WHOLESALE
789 Wholesale Ave
Mississauga, ON

02/10/2024

Item 1              $45.99
Item 2              $23.50
Item 3              $12.00

Subtotal            $81.49
HST (13%)           $10.59
---------------------------
TOTAL               $92.08

Member #: 123456789
""",
    vendor="Costco",
    amount=Decimal('92.08'),
    date='2024-02-10',
    currency='CAD',
    tax=Decimal('10.59'),
    notes="Warehouse club, HST percentage shown"
)


# =============================================================================
# TEST CASES: Edge Cases
# =============================================================================

HANDWRITTEN_NOTE_RECEIPT = ExpectedReceipt(
    name="Handwritten Note (Edge Case)",
    text="""\
Joe's Pizza
Cash Sale

2/15/24

2 Large Pizzas  $30.00
Tax             $2.10
Total           $32.10

Thanks!
""",
    vendor="Joe's Pizza",
    amount=Decimal('32.10'),
    date='2024-02-15',
    currency='CAD',
    tax=Decimal('2.10'),
    notes="Handwritten-style receipt, minimal formatting"
)

FADED_RECEIPT = ExpectedReceipt(
    name="Faded Receipt (Edge Case)",
    text="""\
...OCERY STORE...
...te: 12/...  /2023...

...ubtotal...  $25.....
...ax...       $1.75...
TOTAL          $26.75

Cash Tendered  $30.00
""",
    vendor=None,  # Expect to fail vendor extraction
    amount=Decimal('26.75'),
    date=None,  # Partial date, expect to fail
    currency='CAD',
    tax=Decimal('1.75'),
    notes="Simulated faded receipt with missing text"
)

NO_TAX_RECEIPT = ExpectedReceipt(
    name="No Tax Receipt",
    text="""\
Professional Services
Consulting Invoice

Date: Jan 10, 2024
Invoice #: INV-001

Services Rendered    $500.00

Total Due:           $500.00

No tax applicable (professional services)
""",
    vendor="Professional Services",
    amount=Decimal('500.00'),
    date='2024-01-10',
    currency='CAD',
    tax=None,
    notes="Service invoice with no tax"
)

REFUND_RECEIPT = ExpectedReceipt(
    name="Refund (Negative Amount)",
    text="""\
RETURNS DEPARTMENT
Store Credit Issued

Date: 03/01/2024

Original Purchase   -$45.99
Processing Fee      $0.00
---------------------------
Refund Amount       -$45.99

No tax refund on store credit
""",
    vendor=None,
    amount=Decimal('-45.99'),  # Negative amount
    date='2024-03-01',
    currency='CAD',
    tax=None,
    notes="Refund with negative amount"
)


# =============================================================================
# TEST SUITE DEFINITION
# =============================================================================

ALL_TEST_CASES = [
    # Major vendors
    UBER_RECEIPT,
    STARBUCKS_RECEIPT,
    AMAZON_RECEIPT,
    STEAM_RECEIPT,
    WALMART_RECEIPT,
    LINKEDIN_RECEIPT,
    SEPHORA_RECEIPT,
    GEOGUESSR_RECEIPT,
    APPLE_RECEIPT,
    COSTCO_RECEIPT,

    # Edge cases
    HANDWRITTEN_NOTE_RECEIPT,
    FADED_RECEIPT,
    NO_TAX_RECEIPT,
    REFUND_RECEIPT,
]


def test_receipt(receipt: ExpectedReceipt, parser: ReceiptParser, results: AccuracyResults) -> bool:
    """Test a single receipt and update accuracy results."""
    result = parser.parse(receipt.text)

    results.total_tests += 1
    all_correct = True
    failures = {}

    # Test vendor
    if receipt.vendor is not None:
        vendor_match = (result['vendor'] and
                       receipt.vendor.lower() in result['vendor'].lower())
        if vendor_match:
            results.vendor_correct += 1
        else:
            all_correct = False
            failures['vendor'] = {
                'expected': receipt.vendor,
                'actual': result['vendor']
            }
    else:
        # Vendor is None (expected to fail), count as correct if it fails
        if result['vendor'] is None or result['vendor'] == '':
            results.vendor_correct += 1

    # Test amount
    if receipt.amount is not None:
        if result['amount'] == receipt.amount:
            results.amount_correct += 1
        else:
            all_correct = False
            failures['amount'] = {
                'expected': str(receipt.amount),
                'actual': str(result['amount'])
            }

    # Test date
    if receipt.date is not None:
        if result['date'] == receipt.date:
            results.date_correct += 1
        else:
            all_correct = False
            failures['date'] = {
                'expected': receipt.date,
                'actual': result['date']
            }
    else:
        # Date is None (expected to fail), count as correct if it fails
        if result['date'] is None or result['date'] == '':
            results.date_correct += 1

    # Test currency
    if receipt.currency is not None:
        if result['currency'] == receipt.currency:
            results.currency_correct += 1
        else:
            all_correct = False
            failures['currency'] = {
                'expected': receipt.currency,
                'actual': result['currency']
            }

    # Test tax
    if receipt.tax is not None:
        if result['tax'] == receipt.tax:
            results.tax_correct += 1
        else:
            all_correct = False
            failures['tax'] = {
                'expected': str(receipt.tax),
                'actual': str(result['tax'])
            }
    else:
        # Tax is None (expected to have no tax), count as correct if None
        if result['tax'] is None:
            results.tax_correct += 1

    # Record failure if not all fields correct
    if not all_correct:
        results.failures.append({
            'name': receipt.name,
            'fields': failures,
            'notes': receipt.notes
        })

    return all_correct


def print_accuracy_report(results: AccuracyResults):
    """Print detailed accuracy report."""
    print("\n" + "="*80)
    print("PARSER ACCURACY REPORT")
    print("="*80)

    print(f"\nTotal Test Cases: {results.total_tests}")
    print(f"\nPer-Field Accuracy:")
    print(f"  Vendor:   {results.vendor_correct}/{results.total_tests} ({results.vendor_accuracy():.1f}%)")
    print(f"  Amount:   {results.amount_correct}/{results.total_tests} ({results.amount_accuracy():.1f}%)")
    print(f"  Date:     {results.date_correct}/{results.total_tests} ({results.date_accuracy():.1f}%)")
    print(f"  Currency: {results.currency_correct}/{results.total_tests} ({results.currency_accuracy():.1f}%)")
    print(f"  Tax:      {results.tax_correct}/{results.total_tests} ({results.tax_accuracy():.1f}%)")

    print(f"\nOverall Accuracy: {results.overall_accuracy():.1f}%")
    print(f"Target Accuracy:  90.0%")

    # Show failures
    if results.failures:
        print(f"\n{'='*80}")
        print(f"FAILURES ({len(results.failures)} receipts)")
        print("="*80)
        for failure in results.failures:
            print(f"\n{failure['name']}:")
            if failure['notes']:
                print(f"  Notes: {failure['notes']}")
            for field, details in failure['fields'].items():
                print(f"  {field.upper()}:")
                print(f"    Expected: {details['expected']}")
                print(f"    Actual:   {details['actual']}")
    else:
        print(f"\n✓ ALL TESTS PASSED!")

    # Summary
    print(f"\n{'='*80}")
    if results.overall_accuracy() >= 90.0:
        print("✓ TARGET ACCURACY ACHIEVED (90%+)")
    else:
        print(f"✗ BELOW TARGET ACCURACY ({results.overall_accuracy():.1f}% < 90%)")
        print(f"  Need to improve {90.0 - results.overall_accuracy():.1f} percentage points")
    print("="*80)


def main():
    """Run comprehensive parser accuracy tests."""
    print("="*80)
    print("COMPREHENSIVE PARSER ACCURACY TEST SUITE")
    print("="*80)
    print(f"\nTest Cases: {len(ALL_TEST_CASES)}")
    print(f"Target Accuracy: 90%+ per field")

    parser = ReceiptParser()
    results = AccuracyResults()

    # Run all tests
    print(f"\nRunning tests...")
    for receipt in ALL_TEST_CASES:
        passed = test_receipt(receipt, parser, results)
        status = "✓" if passed else "✗"
        print(f"  {status} {receipt.name}")

    # Print detailed report
    print_accuracy_report(results)

    # Return success if target accuracy achieved
    return results.overall_accuracy() >= 90.0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
