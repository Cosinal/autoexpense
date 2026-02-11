#!/usr/bin/env python3
"""
Bulk Parser Test Runner - Tests parser against real PDF receipts

This script:
1. Finds all PDF files in tests/data/receipts/
2. Runs OCR on each PDF
3. Parses the extracted text
4. Compares against expected results (JSON files)
5. Generates accuracy report

Usage:
    python3 tests/test_parser_bulk.py
    python3 tests/test_parser_bulk.py --verbose
    python3 tests/test_parser_bulk.py --folder passed
"""

import sys
import os
import json
import argparse
from pathlib import Path
from decimal import Decimal
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.ocr import OCRService
from app.services.parser import ReceiptParser


@dataclass
class TestResult:
    """Result of testing a single receipt."""
    filename: str
    passed: bool
    expected: Dict[str, Any]
    actual: Dict[str, Any]
    failures: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class BulkTestResults:
    """Aggregate results from bulk testing."""
    total_tests: int = 0
    total_passed: int = 0
    vendor_correct: int = 0
    amount_correct: int = 0
    date_correct: int = 0
    currency_correct: int = 0
    tax_correct: int = 0
    results: List[TestResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def pass_rate(self) -> float:
        return (self.total_passed / self.total_tests * 100) if self.total_tests > 0 else 0.0

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


def load_expected_results(json_path: Path) -> Optional[Dict[str, Any]]:
    """Load expected results from JSON file."""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)

        # Convert amount and tax to Decimal if present
        if data.get('amount'):
            data['amount'] = Decimal(str(data['amount']))
        if data.get('tax'):
            data['tax'] = Decimal(str(data['tax']))

        return data
    except Exception as e:
        print(f"  ✗ Error loading expected results: {e}")
        return None


def compare_field(expected: Any, actual: Any, field_name: str) -> bool:
    """Compare a single field, handling None values and case-insensitive strings."""
    if expected is None:
        # If expected is None, we expect extraction to fail (return None or empty)
        return actual is None or actual == '' or actual == 'None'

    if actual is None or actual == '' or actual == 'None':
        # If actual is None but expected is not, it's a failure
        return False

    # For strings (vendor, currency, date), do case-insensitive comparison
    if isinstance(expected, str) and isinstance(actual, str):
        if field_name == 'vendor':
            # For vendor, check if expected is contained in actual (case-insensitive)
            return expected.lower() in actual.lower()
        else:
            return expected.lower() == actual.lower()

    # For Decimal (amount, tax), compare directly
    return expected == actual


def test_receipt(pdf_path: Path, json_path: Path, ocr_service: OCRService,
                parser: ReceiptParser, verbose: bool = False) -> TestResult:
    """Test a single receipt PDF against expected results."""

    if verbose:
        print(f"\n{'='*80}")
        print(f"Testing: {pdf_path.name}")
        print(f"{'='*80}")

    # Load expected results
    expected = load_expected_results(json_path)
    if expected is None:
        return TestResult(
            filename=pdf_path.name,
            passed=False,
            expected={},
            actual={},
            error="Failed to load expected results"
        )

    try:
        # Run OCR
        if verbose:
            print(f"\n1. Running OCR...")
        ocr_text = ocr_service.extract_text_from_file(str(pdf_path))

        if not ocr_text or ocr_text.strip() == '':
            return TestResult(
                filename=pdf_path.name,
                passed=False,
                expected=expected,
                actual={},
                error="OCR extracted no text"
            )

        if verbose:
            print(f"   OCR extracted {len(ocr_text)} characters")
            print(f"\n2. Parsing extracted text...")

        # Parse
        parsed = parser.parse(ocr_text)

        actual = {
            'vendor': parsed.get('vendor'),
            'amount': parsed.get('amount'),
            'date': parsed.get('date'),
            'currency': parsed.get('currency'),
            'tax': parsed.get('tax')
        }

        if verbose:
            print(f"\n3. Comparing results...")
            print(f"\n   Expected:")
            for field, value in expected.items():
                if field != 'notes':
                    print(f"     {field}: {value}")
            print(f"\n   Actual:")
            for field, value in actual.items():
                print(f"     {field}: {value}")

        # Compare fields
        failures = {}
        all_correct = True

        for field in ['vendor', 'amount', 'date', 'currency', 'tax']:
            expected_val = expected.get(field)
            actual_val = actual.get(field)

            is_correct = compare_field(expected_val, actual_val, field)

            if not is_correct:
                all_correct = False
                failures[field] = {
                    'expected': str(expected_val) if expected_val is not None else None,
                    'actual': str(actual_val) if actual_val is not None else None
                }

        if verbose:
            print(f"\n4. Result: {'✓ PASS' if all_correct else '✗ FAIL'}")
            if failures:
                print(f"\n   Failures:")
                for field, details in failures.items():
                    print(f"     {field}: expected={details['expected']}, actual={details['actual']}")

        return TestResult(
            filename=pdf_path.name,
            passed=all_correct,
            expected=expected,
            actual=actual,
            failures=failures
        )

    except Exception as e:
        error_msg = f"Error processing receipt: {str(e)}"
        if verbose:
            print(f"\n✗ {error_msg}")
        return TestResult(
            filename=pdf_path.name,
            passed=False,
            expected=expected,
            actual={},
            error=error_msg
        )


def run_bulk_tests(receipts_dir: Path, folder: Optional[str] = None,
                   verbose: bool = False) -> BulkTestResults:
    """Run tests on all PDF receipts in the directory."""

    ocr_service = OCRService()
    parser = ReceiptParser()
    results = BulkTestResults()

    # Find all PDF files
    if folder:
        search_dirs = [receipts_dir / folder]
    else:
        search_dirs = [
            receipts_dir / 'passed',
            receipts_dir / 'failed',
            receipts_dir / 'edge_cases'
        ]

    pdf_files = []
    for search_dir in search_dirs:
        if search_dir.exists():
            pdf_files.extend(search_dir.glob('*.pdf'))

    if not pdf_files:
        print(f"No PDF files found in {receipts_dir}")
        print(f"Searched: {', '.join(str(d) for d in search_dirs)}")
        return results

    print(f"\n{'='*80}")
    print(f"BULK PARSER TEST - {len(pdf_files)} receipts")
    print(f"{'='*80}")

    # Test each receipt
    for pdf_path in sorted(pdf_files):
        json_path = pdf_path.with_suffix('.json')

        if not json_path.exists():
            print(f"\n⚠️  Skipping {pdf_path.name} - no expected results JSON found")
            results.errors.append(f"{pdf_path.name}: Missing expected results JSON")
            continue

        if not verbose:
            print(f"\n  Testing: {pdf_path.name}...", end=' ')

        result = test_receipt(pdf_path, json_path, ocr_service, parser, verbose)
        results.results.append(result)
        results.total_tests += 1

        if result.error:
            results.errors.append(f"{pdf_path.name}: {result.error}")
            if not verbose:
                print(f"✗ ERROR")
            continue

        if result.passed:
            results.total_passed += 1
            if not verbose:
                print(f"✓ PASS")
        else:
            if not verbose:
                print(f"✗ FAIL")

        # Count per-field accuracy
        for field in ['vendor', 'amount', 'date', 'currency', 'tax']:
            if field not in result.failures:
                if field == 'vendor':
                    results.vendor_correct += 1
                elif field == 'amount':
                    results.amount_correct += 1
                elif field == 'date':
                    results.date_correct += 1
                elif field == 'currency':
                    results.currency_correct += 1
                elif field == 'tax':
                    results.tax_correct += 1

    return results


def print_summary_report(results: BulkTestResults, verbose: bool = False):
    """Print summary report of bulk test results."""

    print(f"\n{'='*80}")
    print("BULK TEST SUMMARY")
    print(f"{'='*80}")

    print(f"\nTotal Receipts: {results.total_tests}")
    print(f"Fully Correct:  {results.total_passed}/{results.total_tests} ({results.pass_rate():.1f}%)")

    print(f"\nPer-Field Accuracy:")
    print(f"  Vendor:   {results.vendor_correct}/{results.total_tests} ({results.vendor_accuracy():.1f}%)")
    print(f"  Amount:   {results.amount_correct}/{results.total_tests} ({results.amount_accuracy():.1f}%)")
    print(f"  Date:     {results.date_correct}/{results.total_tests} ({results.date_accuracy():.1f}%)")
    print(f"  Currency: {results.currency_correct}/{results.total_tests} ({results.currency_accuracy():.1f}%)")
    print(f"  Tax:      {results.tax_correct}/{results.total_tests} ({results.tax_accuracy():.1f}%)")

    print(f"\nOverall Accuracy: {results.overall_accuracy():.1f}%")
    print(f"Target Accuracy:  90.0%")

    # Show failures
    failed_results = [r for r in results.results if not r.passed and not r.error]
    if failed_results and not verbose:
        print(f"\n{'='*80}")
        print(f"FAILURES ({len(failed_results)} receipts)")
        print(f"{'='*80}")
        for result in failed_results:
            print(f"\n{result.filename}:")
            if result.expected.get('notes'):
                print(f"  Notes: {result.expected['notes']}")
            for field, details in result.failures.items():
                print(f"  {field.upper()}:")
                print(f"    Expected: {details['expected']}")
                print(f"    Actual:   {details['actual']}")

    # Show errors
    if results.errors:
        print(f"\n{'='*80}")
        print(f"ERRORS ({len(results.errors)})")
        print(f"{'='*80}")
        for error in results.errors:
            print(f"  {error}")

    # Final verdict
    print(f"\n{'='*80}")
    if results.overall_accuracy() >= 90.0:
        print("✓ TARGET ACCURACY ACHIEVED (90%+)")
    else:
        gap = 90.0 - results.overall_accuracy()
        print(f"✗ BELOW TARGET ACCURACY ({results.overall_accuracy():.1f}% < 90%)")
        print(f"  Need to improve {gap:.1f} percentage points")
    print(f"{'='*80}\n")


def main():
    parser_args = argparse.ArgumentParser(description='Bulk test parser against PDF receipts')
    parser_args.add_argument('--verbose', '-v', action='store_true',
                           help='Show detailed output for each receipt')
    parser_args.add_argument('--folder', '-f', type=str,
                           help='Test only receipts in specific folder (passed/failed/edge_cases)')
    args = parser_args.parse_args()

    # Find receipts directory
    tests_dir = Path(__file__).parent
    receipts_dir = tests_dir / 'data' / 'receipts'

    if not receipts_dir.exists():
        print(f"Error: Receipts directory not found: {receipts_dir}")
        print(f"\nExpected structure:")
        print(f"  {receipts_dir}/")
        print(f"    passed/")
        print(f"    failed/")
        print(f"    edge_cases/")
        sys.exit(1)

    # Run bulk tests
    results = run_bulk_tests(receipts_dir, folder=args.folder, verbose=args.verbose)

    # Print summary
    print_summary_report(results, verbose=args.verbose)

    # Exit with error code if target not met
    sys.exit(0 if results.overall_accuracy() >= 90.0 else 1)


if __name__ == '__main__':
    main()
