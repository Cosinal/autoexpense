"""
Test suite for Phase 2 parser improvements: confidence scoring and routing.

Tests cover:
- Scorer-derived confidence (not hardcoded)
- Forwarding-aware vendor penalties
- Amount blacklist improvements (tax breakdown)
- Amount consistency validation (subtotal + tax ≈ total)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.parser import ReceiptParser, ParseContext
from app.utils.scoring import select_best_vendor, select_best_amount, select_best_date, select_best_currency
from app.utils.candidates import create_vendor_candidate
from decimal import Decimal
import pytest


class TestScorerDerivedConfidence:
    """Test that confidence values use real scores, not hardcoded heuristics."""

    def test_select_best_vendor_returns_score(self):
        """Verify select_best_vendor returns (candidate, score) tuple when return_score=True."""
        candidates = [
            create_vendor_candidate(
                value="Uber",
                pattern_name="context_sender_name",
                match_span=(0, 4),
                raw_text="Uber",
                line_position=0,
                from_email_header=True
            ),
            create_vendor_candidate(
                value="Joe's Pizza",
                pattern_name="body_text",
                match_span=(10, 21),
                raw_text="Joe's Pizza",
                line_position=5,
                from_email_header=False
            )
        ]

        # Without return_score (legacy)
        result = select_best_vendor(candidates, return_score=False)
        assert result is not None
        assert hasattr(result, 'value')
        assert result.value == "Uber"  # Email header scores highest

        # With return_score (new behavior)
        result_with_score = select_best_vendor(candidates, return_score=True)
        assert result_with_score is not None
        assert isinstance(result_with_score, tuple)
        assert len(result_with_score) == 2

        candidate, score = result_with_score
        assert candidate.value == "Uber"
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Email header should score high

    def test_parser_uses_real_scores_not_hardcoded(self):
        """Verify parser.parse() uses real scores for confidence, not hardcoded 0.5/0.7/0.9."""
        parser = ReceiptParser()

        receipt_text = """
From: Uber <receipts@uber.com>
Total: $14.13
Date: 2024-01-15
"""
        context = ParseContext(sender_name="Uber", sender_domain="uber.com")
        result = parser.parse(receipt_text, context)

        # Check that confidence values exist and are in valid range
        assert 'debug' in result
        assert 'confidence_per_field' in result['debug']

        vendor_conf = result['debug']['confidence_per_field'].get('vendor')
        amount_conf = result['debug']['confidence_per_field'].get('amount')

        # Confidence should be float in [0, 1], not exactly 0.5, 0.7, or 0.9
        assert vendor_conf is not None
        assert isinstance(vendor_conf, float)
        assert 0.0 <= vendor_conf <= 1.0

        # Should NOT be exactly the old hardcoded values
        # (With real scoring, values will be more granular like 0.85, 0.62, etc.)
        # Note: This may occasionally be 0.9 by chance, but unlikely to be all three
        hardcoded_values = {0.5, 0.7, 0.9}
        # At least one field should have a non-hardcoded confidence
        confidences = [
            result['debug']['confidence_per_field'].get(field)
            for field in ['vendor', 'amount', 'date', 'currency']
            if result['debug']['confidence_per_field'].get(field) is not None
        ]
        non_hardcoded = [c for c in confidences if c not in hardcoded_values]
        assert len(non_hardcoded) > 0, "All confidences are hardcoded values (0.5, 0.7, 0.9)"

    def test_low_confidence_fields_populate_review_candidates(self):
        """Verify that fields with low confidence populate debug.review_candidates with top-3 options."""
        parser = ReceiptParser()

        # Ambiguous receipt with multiple vendor candidates
        ambiguous_receipt = """
John's Coffee Shop
Starbucks Card Reload
Amount: $25.00
Date: 2024-01-15
"""
        result = parser.parse(ambiguous_receipt)

        # Vendor might have low confidence due to ambiguity
        vendor_conf = result['debug']['confidence_per_field'].get('vendor', 1.0)

        if vendor_conf < 0.7:
            # Should have review candidates
            assert 'vendor_candidates' in result['debug']
            candidates = result['debug']['vendor_candidates']

            # Should have top-3 candidates with scores
            assert len(candidates) >= 1
            assert len(candidates) <= 3

            for cand in candidates:
                assert 'value' in cand
                assert 'score' in cand
                assert 'pattern' in cand
                assert isinstance(cand['score'], float)
                assert 0.0 <= cand['score'] <= 1.0


class TestForwardedEmailVendorPenalty:
    """Test forwarding-aware penalties to prevent extracting forwarder name."""

    def test_forwarded_uber_extracts_vendor_not_forwarder(self):
        """
        When Uber receipt is forwarded by 'Jorden Shaw', should extract 'Uber', not 'Jorden Shaw'.
        """
        parser = ReceiptParser()

        forwarded_uber_receipt = """
From: Jorden Shaw <jorden@gmail.com>
Subject: Fwd: Your Uber receipt

---------- Forwarded message ---------
From: Uber <receipts@uber.com>
Date: Thu, Jan 15, 2024
Subject: Your trip receipt

Your trip with Uber
Trip Fare: $12.50
HST: $1.63
Total: $14.13
"""
        # Context shows it's from a personal email (forwarder)
        context = ParseContext(
            sender_name="Jorden Shaw",
            sender_domain="gmail.com"
        )

        result = parser.parse(forwarded_uber_receipt, context)

        # Should extract "Uber", not "Jorden Shaw" or "Jorden"
        assert result['vendor'] is not None
        vendor = result['vendor'].lower()

        # Vendor should contain "uber"
        assert 'uber' in vendor, f"Expected 'uber' in vendor, got: {result['vendor']}"

        # Vendor should NOT contain forwarder name parts
        assert 'jorden' not in vendor, f"Vendor should not contain 'jorden', got: {result['vendor']}"
        assert 'shaw' not in vendor, f"Vendor should not contain 'shaw', got: {result['vendor']}"

    def test_forwarded_flag_detected_in_debug(self):
        """Verify is_forwarded flag is detected and logged in debug metadata."""
        parser = ReceiptParser()

        forwarded_text = """
---------- Forwarded message ---------
From: Starbucks <receipts@starbucks.com>
Total: $8.50
"""
        result = parser.parse(forwarded_text)

        # Should detect forwarding
        assert 'debug' in result
        assert result['debug'].get('vendor_is_forwarded') is True

    def test_forwarding_penalty_reduces_sender_name_score(self):
        """Verify that is_forwarded=True reduces score for sender_name candidates."""
        from app.utils.scoring import score_vendor_candidate

        # Create a sender name candidate (looks like person name)
        forwarder_candidate = create_vendor_candidate(
            value="John Smith",
            pattern_name="context_sender_name",
            match_span=(0, 10),
            raw_text="John Smith",
            line_position=0,
            from_email_header=True
        )

        # Score without forwarding
        score_normal = score_vendor_candidate(forwarder_candidate, is_forwarded=False)

        # Score with forwarding (should be heavily penalized)
        context = ParseContext(sender_name="John Smith", sender_domain="gmail.com")
        score_forwarded = score_vendor_candidate(forwarder_candidate, is_forwarded=True, context=context)

        # Forwarded score should be significantly lower
        assert score_forwarded < score_normal
        assert score_forwarded < 0.5, f"Forwarded sender_name should score <0.5, got {score_forwarded}"


class TestAmountBlacklistImprovements:
    """Test expanded blacklist for tax breakdown and related contexts."""

    def test_geoguessr_tax_breakdown_excluded(self):
        """
        GeoGuessr receipt has 'Tax breakdown' section with $0.33.
        Should extract main total ($6.99), not tax breakdown amount.
        """
        parser = ReceiptParser()

        geoguessr_receipt = """
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
"""
        result = parser.parse(geoguessr_receipt)

        # Should extract $6.99 (main total), not $0.33 (tax breakdown)
        assert result['amount'] == Decimal('6.99'), \
            f"Expected 6.99, got {result['amount']} (tax breakdown should be excluded)"

    def test_tax_total_not_treated_as_strong_prefix(self):
        """
        'Tax total' should not be treated as a strong prefix for amount extraction.
        Only 'Total' (without 'Tax') should be a strong prefix.
        """
        parser = ReceiptParser()

        receipt_with_tax_total = """
Subtotal: $50.00
Tax: $5.00
Total: $55.00
Tax total: $5.00
"""
        result = parser.parse(receipt_with_tax_total)

        # Should extract $55.00 (main total), not $5.00 (tax total)
        assert result['amount'] == Decimal('55.00'), \
            f"Expected 55.00, got {result['amount']} ('Tax total' should not be strong prefix)"

    def test_points_and_miles_blacklisted(self):
        """
        Amounts near 'points', 'pts', 'miles', 'rewards' should be blacklisted.
        """
        parser = ReceiptParser()

        receipt_with_points = """
Total: $45.00
Points earned: 1500
Miles: 3000
"""
        result = parser.parse(receipt_with_points)

        # Should extract $45.00, not 1500 or 3000
        assert result['amount'] == Decimal('45.00'), \
            f"Expected 45.00, got {result['amount']} (points/miles should be blacklisted)"

    def test_booking_reference_blacklisted(self):
        """
        Amounts near 'booking reference', 'confirmation', 'reference' should be blacklisted.
        """
        parser = ReceiptParser()

        receipt_with_reference = """
Total: $126.07
Booking reference: 987654
Confirmation: 123456
"""
        result = parser.parse(receipt_with_reference)

        # Should extract $126.07, not reference numbers
        assert result['amount'] == Decimal('126.07'), \
            f"Expected 126.07, got {result['amount']} (booking reference should be blacklisted)"


class TestAmountConsistencyValidation:
    """Test subtotal + tax ≈ total validation."""

    def test_consistent_subtotal_plus_tax_validates(self):
        """
        When subtotal + tax ≈ total, validation should pass (is_consistent=True).
        """
        parser = ReceiptParser()

        consistent_receipt = """
Subtotal: $50.00
Tax: $6.50
Total: $56.50
"""
        result = parser.parse(consistent_receipt)

        # Should extract correct total
        assert result['amount'] == Decimal('56.50')
        assert result['tax'] == Decimal('6.50')

        # Validation should pass
        assert 'debug' in result
        if 'amount_validation' in result['debug']:
            validation = result['debug']['amount_validation']
            assert validation['is_consistent'] is True
            assert Decimal(validation['subtotal']) == Decimal('50.00')
            assert Decimal(validation['tax']) == Decimal('6.50')
            assert Decimal(validation['calculated_total']) == Decimal('56.50')

    def test_inconsistent_subtotal_plus_tax_flags_warning(self):
        """
        When subtotal + tax != total (beyond tolerance), should flag warning.
        """
        parser = ReceiptParser()

        # Inconsistent: $50 + $5 = $55, but total says $60
        inconsistent_receipt = """
Subtotal: $50.00
Tax: $5.00
Total: $60.00
"""
        result = parser.parse(inconsistent_receipt)

        # Should still extract the total (but validation fails)
        assert result['amount'] == Decimal('60.00')

        # Validation should detect inconsistency
        assert 'debug' in result
        if 'amount_validation' in result['debug']:
            validation = result['debug']['amount_validation']
            assert validation['is_consistent'] is False

            # Should have warning
            warnings = result['debug'].get('warnings', [])
            inconsistency_warnings = [w for w in warnings if 'inconsistency' in w.lower()]
            assert len(inconsistency_warnings) > 0, \
                "Expected inconsistency warning in debug.warnings"

    def test_subtotal_plus_tax_within_tolerance(self):
        """
        Subtotal + tax within 1% tolerance should validate as consistent.
        """
        parser = ReceiptParser()

        # Slightly off due to rounding: $50.00 + $6.49 = $56.49, total is $56.50 (1 cent off)
        receipt_with_rounding = """
Subtotal: $50.00
Tax: $6.49
Total: $56.50
"""
        result = parser.parse(receipt_with_rounding)

        # Should extract correct total
        assert result['amount'] == Decimal('56.50')

        # Validation should pass (within tolerance)
        if 'amount_validation' in result['debug']:
            validation = result['debug']['amount_validation']
            # 1 cent difference on $56.50 is 0.018%, well within 1% tolerance
            assert validation['is_consistent'] is True


class TestVendorNormalization:
    """Test vendor normalization stages (raw_line, normalized_line, value)."""

    def test_clean_vendor_name_preserves_case_when_requested(self):
        """Verify _clean_vendor_name respects preserve_case parameter."""
        parser = ReceiptParser()

        # Default: apply title case
        result_default = parser._clean_vendor_name("STARBUCKS COFFEE")
        assert result_default == "Starbucks Coffee"

        # Preserve case: keep original
        result_preserved = parser._clean_vendor_name("STARBUCKS COFFEE", preserve_case=True)
        assert result_preserved == "STARBUCKS COFFEE"

    def test_vendor_candidate_stores_normalization_stages(self):
        """Verify VendorCandidate can store raw_line and normalized_line."""
        candidate = create_vendor_candidate(
            value="Uber",
            pattern_name="body_text",
            match_span=(0, 4),
            raw_text="U B E R",  # OCR artifact
            line_position=0,
            raw_line="U B E R",
            normalized_line="UBER"
        )

        assert candidate.raw_line == "U B E R"
        assert candidate.normalized_line == "UBER"
        assert candidate.value == "Uber"


def test_all_phase2_improvements_integrated():
    """
    Integration test: verify all Phase 2 improvements work together.

    Tests a complex scenario with:
    - Forwarded email (should penalize forwarder name)
    - Tax breakdown section (should be blacklisted)
    - Subtotal + tax validation
    - Real scores in confidence metadata
    """
    parser = ReceiptParser()

    complex_receipt = """
From: Alice Johnson <alice@gmail.com>
Subject: Fwd: Your receipt

---------- Forwarded message ---------
From: Starbucks <receipts@starbucks.com>

Starbucks Coffee
Order #12345

Subtotal: $15.00
Tax: $1.95
Total: $16.95

Tax breakdown
Sales Tax (13%): 13%
"""

    context = ParseContext(
        sender_name="Alice Johnson",
        sender_domain="gmail.com"
    )

    result = parser.parse(complex_receipt, context)

    # 1. Should extract "Starbucks", not "Alice Johnson"
    assert result['vendor'] is not None
    vendor = result['vendor'].lower()
    assert 'starbucks' in vendor
    assert 'alice' not in vendor
    assert 'johnson' not in vendor

    # 2. Should extract $16.95 (main total), not amounts from tax breakdown
    assert result['amount'] == Decimal('16.95')

    # 3. Should extract tax correctly
    assert result['tax'] == Decimal('1.95')

    # 4. Should validate subtotal + tax = total
    if 'amount_validation' in result['debug']:
        validation = result['debug']['amount_validation']
        assert validation['is_consistent'] is True

    # 5. Should use real scores for confidence
    assert 'confidence_per_field' in result['debug']
    vendor_conf = result['debug']['confidence_per_field'].get('vendor')
    assert vendor_conf is not None
    assert isinstance(vendor_conf, float)
    assert 0.0 <= vendor_conf <= 1.0

    # 6. Should detect forwarding
    assert result['debug'].get('vendor_is_forwarded') is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
