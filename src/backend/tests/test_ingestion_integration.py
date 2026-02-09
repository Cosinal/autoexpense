#!/usr/bin/env python3
"""
Integration tests for the production-grade ingestion pipeline.
Tests state machine, idempotency, Decimal precision, and all service integrations.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from decimal import Decimal
import hashlib
from app.services.storage import StorageService
from app.services.parser import ReceiptParser
from app.utils.supabase import get_supabase_client

print("=" * 80)
print("INGESTION PIPELINE INTEGRATION TESTS")
print("=" * 80)


def test_storage_content_addressed_paths():
    """Test 1: Content-addressed storage paths are deterministic."""
    print("\n[TEST 1] Content-addressed storage paths")

    storage = StorageService()

    # Same content should produce same path
    file_data = b"Test receipt content"
    file_hash = storage.calculate_file_hash(file_data)

    path1 = storage.generate_file_path("user123", file_hash, "receipt.pdf")
    path2 = storage.generate_file_path("user123", file_hash, "receipt.pdf")

    assert path1 == path2, f"Paths should be identical: {path1} != {path2}"

    # Verify path format: user_id/hash[:2]/hash/filename
    expected_format = f"user123/{file_hash[:2]}/{file_hash}/receipt.pdf"
    assert path1 == expected_format, f"Path format incorrect: {path1}"

    print(f"  ✓ Deterministic path: {path1}")
    print(f"  ✓ Hash: {file_hash}")
    return True


def test_storage_filename_sanitization():
    """Test 2: Unsafe filenames are sanitized."""
    print("\n[TEST 2] Filename sanitization")

    storage = StorageService()

    # Test various unsafe characters
    unsafe_name = "../../etc/passwd'; DROP TABLE receipts;--.pdf"
    file_hash = "abc123"

    path = storage.generate_file_path("user123", file_hash, unsafe_name)

    # Should not contain directory traversal or SQL injection
    assert "../" not in path, "Path contains directory traversal"
    assert "DROP TABLE" not in path, "Path contains SQL injection attempt"

    print(f"  ✓ Unsafe input: {unsafe_name}")
    print(f"  ✓ Sanitized path: {path}")
    return True


def test_decimal_precision_throughout_pipeline():
    """Test 3: Decimal precision is maintained (no float conversion)."""
    print("\n[TEST 3] Decimal precision throughout pipeline")

    parser = ReceiptParser()

    # Test receipt with precise amounts
    test_receipt = """
    Sephora Receipt
    Subtotal: $52.20
    GST (5%): $2.62
    HST (9%): $4.70
    Total: $59.52
    """

    result = parser.parse(test_receipt)

    # Verify amounts are Decimal, not float
    assert isinstance(result['amount'], Decimal), f"Amount should be Decimal, got {type(result['amount'])}"
    assert isinstance(result['tax'], Decimal), f"Tax should be Decimal, got {type(result['tax'])}"

    # Verify exact values (no rounding errors)
    assert result['amount'] == Decimal('59.52'), f"Amount mismatch: {result['amount']}"
    assert result['tax'] == Decimal('7.32'), f"Tax mismatch: {result['tax']}"

    # Verify conversion to string for DB
    from app.services.ingestion import IngestionService
    ingestion = IngestionService()

    amount_str = ingestion._decimal_to_str(result['amount'])
    tax_str = ingestion._decimal_to_str(result['tax'])

    assert amount_str == '59.52', f"Amount string incorrect: {amount_str}"
    assert tax_str == '7.32', f"Tax string incorrect: {tax_str}"

    print(f"  ✓ Amount: {result['amount']} (type: {type(result['amount']).__name__})")
    print(f"  ✓ Tax: {result['tax']} (type: {type(result['tax']).__name__})")
    print(f"  ✓ DB conversion: amount={amount_str}, tax={tax_str}")
    return True


def test_parser_debug_metadata():
    """Test 4: Parser returns debug metadata for ingestion_debug column."""
    print("\n[TEST 4] Parser debug metadata")

    parser = ReceiptParser()

    test_receipt = """
    Amazon Receipt
    Order Total: $156.78
    Tax: $12.34
    """

    result = parser.parse(test_receipt)

    # Verify debug metadata exists
    assert 'debug' in result, "Parser should return debug metadata"
    assert 'patterns_matched' in result['debug'], "Debug should have patterns_matched"
    assert 'confidence_per_field' in result['debug'], "Debug should have confidence_per_field"

    # Verify amount pattern was recorded
    assert 'amount' in result['debug']['patterns_matched'], "Amount pattern should be recorded"

    print(f"  ✓ Debug keys: {list(result['debug'].keys())}")
    print(f"  ✓ Amount pattern: {result['debug']['patterns_matched'].get('amount')}")
    print(f"  ✓ Confidence: amount={result['debug']['confidence_per_field'].get('amount', 'N/A')}")
    return True


def test_file_hash_deduplication():
    """Test 5: File hash deduplication prevents duplicate uploads."""
    print("\n[TEST 5] File hash deduplication")

    storage = StorageService()

    # Same content should produce same hash
    content1 = b"Receipt image data"
    content2 = b"Receipt image data"  # Identical
    content3 = b"Different receipt"

    hash1 = storage.calculate_file_hash(content1)
    hash2 = storage.calculate_file_hash(content2)
    hash3 = storage.calculate_file_hash(content3)

    assert hash1 == hash2, f"Identical content should have same hash: {hash1} != {hash2}"
    assert hash1 != hash3, f"Different content should have different hash"

    print(f"  ✓ Identical content: {hash1[:16]}...")
    print(f"  ✓ Different content: {hash3[:16]}...")
    print(f"  ✓ Deduplication would prevent duplicate upload")
    return True


def test_decimal_to_str_edge_cases():
    """Test 6: Decimal to string conversion handles edge cases."""
    print("\n[TEST 6] Decimal to string edge cases")

    from app.services.ingestion import IngestionService
    ingestion = IngestionService()

    # Test various edge cases
    test_cases = [
        (None, None),
        (Decimal('0'), '0'),
        (Decimal('0.00'), '0.00'),
        (Decimal('123.456'), '123.456'),
        (Decimal('9999999.99'), '9999999.99'),
    ]

    for input_val, expected in test_cases:
        result = ingestion._decimal_to_str(input_val)
        assert result == expected, f"Failed for {input_val}: got {result}, expected {expected}"
        print(f"  ✓ {input_val} → {result}")

    return True


def test_schema_migration_applied():
    """Test 7: Verify migration was applied correctly."""
    print("\n[TEST 7] Schema migration verification")

    supabase = get_supabase_client()

    # This is a basic check - we'll try to query the new columns
    # If they don't exist, Supabase will return an error
    try:
        # Check processed_emails has new columns
        result = supabase.table('processed_emails').select(
            'status,failure_reason,provider'
        ).limit(0).execute()

        print("  ✓ processed_emails: status, failure_reason, provider columns exist")

        # Check receipts has new columns
        result = supabase.table('receipts').select(
            'file_path,source_message_id,source_type,attachment_index,ingestion_debug'
        ).limit(0).execute()

        print("  ✓ receipts: file_path, source_message_id, source_type, attachment_index, ingestion_debug columns exist")

        return True

    except Exception as e:
        print(f"  ✗ Migration verification failed: {e}")
        return False


def test_parser_regression_suite():
    """Test 8: Run existing parser regression tests."""
    print("\n[TEST 8] Parser regression suite")

    # Import the regression tests
    from test_parser_regression import (
        test_steam_pipe_table,
        test_geoguessr_payment_processor,
        test_sephora_dual_tax,
        test_debug_metadata_present
    )

    tests = [
        ("Steam pipe table", test_steam_pipe_table),
        ("GeoGuessr payment processor", test_geoguessr_payment_processor),
        ("Sephora dual tax", test_sephora_dual_tax),
        ("Debug metadata", test_debug_metadata_present),
    ]

    passed = 0
    for name, test_func in tests:
        try:
            test_func()
            print(f"  ✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {name}: {e}")
        except Exception as e:
            print(f"  ✗ {name}: UNEXPECTED ERROR: {e}")

    print(f"  → {passed}/{len(tests)} parser tests passed")
    return passed == len(tests)


def test_critical_receipts():
    """Test 9: Verify critical receipts still parse correctly."""
    print("\n[TEST 9] Critical receipt parsing")

    parser = ReceiptParser()

    # Test GeoGuessr receipt
    try:
        with open('documentation/failed_receipts/GeoGuessr.txt') as f:
            text = f.read()

        result = parser.parse(text)

        assert result['amount'] == Decimal('6.99'), f"GeoGuessr amount: {result['amount']}"
        assert result['tax'] == Decimal('0.33'), f"GeoGuessr tax: {result['tax']}"
        assert result['date'] == '2025-11-23', f"GeoGuessr date: {result['date']}"

        print(f"  ✓ GeoGuessr: amount=${result['amount']}, tax=${result['tax']}, date={result['date']}")
    except FileNotFoundError:
        print("  ⚠ GeoGuessr.txt not found (skipping)")
    except AssertionError as e:
        print(f"  ✗ GeoGuessr parsing failed: {e}")
        return False

    return True


def main():
    """Run all integration tests."""
    tests = [
        test_storage_content_addressed_paths,
        test_storage_filename_sanitization,
        test_decimal_precision_throughout_pipeline,
        test_parser_debug_metadata,
        test_file_hash_deduplication,
        test_decimal_to_str_edge_cases,
        test_schema_migration_applied,
        test_parser_regression_suite,
        test_critical_receipts,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n✗ {test.__name__}: UNEXPECTED ERROR")
            print(f"  {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")

    if failed == 0:
        print("\n✓ ALL INTEGRATION TESTS PASSED")
        print("Production-grade ingestion pipeline is ready!")
    else:
        print(f"\n✗ {failed} TEST(S) FAILED")
        print("Review failures above and fix issues.")

    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
