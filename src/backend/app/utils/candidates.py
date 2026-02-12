"""
Candidate dataclasses for extraction scoring.

Each candidate represents a potential extracted value with metadata
used for scoring and selection.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Any
import re


@dataclass
class Candidate:
    """Base class for extraction candidates."""
    value: Any
    pattern_name: str
    match_span: tuple[int, int]  # (start, end) character positions
    priority: int = 100  # Lower is better (like CSS priority)
    raw_text: str = ""  # Original matched text


@dataclass
class AmountCandidate(Candidate):
    """
    Candidate for extracted amount.

    Scoring factors:
    - priority: Base pattern priority (lower = higher quality)
    - has_strong_prefix: Keywords like "Total", "Amount Due"
    - proximity_to_keywords: Distance to strong keywords
    - in_subtotal_context: Near "Subtotal" (penalty)
    - in_blacklist_context: Near "Balance", "Credit" (penalty)
    """
    value: Decimal
    proximity_to_keywords: int = 999  # Characters to nearest strong keyword
    has_strong_prefix: bool = False
    in_subtotal_context: bool = False
    in_blacklist_context: bool = False


@dataclass
class DateCandidate(Candidate):
    """
    Candidate for extracted date.

    Scoring factors:
    - priority: Base pattern priority
    - line_position: Which line number (earlier = better)
    - has_strong_prefix: Keywords like "Date:", "Issued:"
    - is_ambiguous: Format is ambiguous (MM/DD vs DD/MM)
    """
    value: str  # ISO format: YYYY-MM-DD
    line_position: int = 999
    has_strong_prefix: bool = False
    is_ambiguous: bool = False
    detected_locale: Optional[str] = None  # 'US' or 'EU'


@dataclass
class VendorCandidate(Candidate):
    """
    Candidate for extracted vendor.

    Scoring factors:
    - from_email_header: Extracted from From:/Reply-To: (highest confidence)
    - from_subject: Extracted from email subject
    - line_position: Which line number (earlier = better)
    - has_company_suffix: Ends with Inc, LLC, Ltd, Corp, etc.
    - is_title_case: Proper capitalization
    - word_count: Number of words (2-4 is ideal)

    Normalization stages (Phase 2 enhancement):
    - raw_line: Original OCR text (e.g., "U B E R")
    - normalized_line: After OCR normalization (e.g., "UBER")
    - value: Final display format (e.g., "Uber")
    """
    value: str
    raw_line: str = ""  # Original OCR text
    normalized_line: str = ""  # After OCR normalization
    from_email_header: bool = False
    from_subject: bool = False
    line_position: int = 999
    has_company_suffix: bool = False
    is_title_case: bool = False
    word_count: int = 0


@dataclass
class CurrencyCandidate(Candidate):
    """
    Candidate for extracted currency.

    Scoring factors:
    - priority: Base pattern priority
    - symbol_proximity: Distance to amount (closer = better)
    - is_explicit: Explicitly stated vs inferred from symbol
    - context_count: Number of times currency appears in text
    """
    value: str  # ISO code: USD, EUR, GBP, etc.
    symbol_proximity: int = 999  # Characters to nearest amount
    is_explicit: bool = False  # True if "USD" written out, False if "$" symbol
    context_count: int = 1  # How many times this currency appears


@dataclass
class TaxCandidate(Candidate):
    """
    Candidate for extracted tax amount.

    Used for span-based deduplication to avoid summing the same
    tax value multiple times when it appears in different contexts.
    """
    value: Decimal
    is_percentage: bool = False  # If tax was shown as percentage
    tax_type: Optional[str] = None  # GST, HST, VAT, etc.


# Helper functions for creating candidates

def create_amount_candidate(
    value: Decimal,
    pattern_name: str,
    match_span: tuple[int, int],
    raw_text: str,
    priority: int,
    text: str
) -> AmountCandidate:
    """
    Create AmountCandidate with computed context flags.

    Args:
        value: Parsed amount
        pattern_name: Name of pattern that matched
        match_span: Character span of match
        raw_text: Original matched text
        priority: Pattern priority
        text: Full text for context analysis

    Returns:
        AmountCandidate with computed flags
    """
    # Extract context around match (100 chars before/after)
    start, end = match_span
    context_start = max(0, start - 100)
    context_end = min(len(text), end + 100)
    context = text[context_start:context_end].lower()

    # Compute flags with more precise context analysis
    strong_keywords = ['total', 'amount due', 'balance due', 'grand total', 'order total', 'amount paid']

    # Patterns that inherently match strong keywords should be treated as having strong prefix
    # (e.g., 'total_cad_format' pattern explicitly looks for "TOTAL CAD")
    pattern_implies_strong = any(kw in pattern_name for kw in ['total', 'amount', 'paid', 'explicit'])

    if pattern_implies_strong:
        has_strong_prefix = True
    else:
        # Check for strong prefix in immediate preceding text (15 chars, more restrictive)
        # Must be at line start or after newline to avoid table headers like "Price Total"
        immediate_prefix = text[max(0, start - 15):start]
        has_strong_prefix = False

        for keyword in strong_keywords:
            if keyword in immediate_prefix.lower():
                # Must have newline or start of text before keyword to be valid
                keyword_start = immediate_prefix.lower().rfind(keyword)
                if keyword_start == 0 or immediate_prefix[keyword_start - 1] == '\n':
                    # Verify it's not "tax total", "sales tax total", or "subtotal"
                    # Check for both "tax total" and "tax\ntotal" patterns
                    prefix_before_keyword = immediate_prefix[:keyword_start].lower()
                    if 'tax' in prefix_before_keyword:
                        # Tax total or sales tax total - skip
                        continue
                    if 'sub' + keyword in immediate_prefix.lower():
                        # Subtotal - skip
                        continue
                    has_strong_prefix = True
                    break

    # Find proximity to keywords (check full context window)
    proximity = 999
    for keyword in strong_keywords:
        pos = context.find(keyword)
        if pos != -1:
            # Exclude "tax total", "sales tax total", and "subtotal"
            # Check for "tax" before the keyword (with space or newline)
            context_before_keyword = context[max(0, pos-10):pos]
            if 'tax' in context_before_keyword:
                # Tax total or sales tax total - skip
                continue
            if 'sub' + keyword in context[max(0, pos-3):pos+len(keyword)+3]:
                # Subtotal - skip
                continue
            proximity = min(proximity, abs(pos - (start - context_start)))

    # Penalty contexts - more precise boundaries
    # Only penalize if subtotal is within 30 chars AND we don't have a strong prefix
    preceding_30 = text[max(0, start - 30):start].lower()
    in_subtotal_context = 'subtotal' in preceding_30 and not has_strong_prefix

    # Blacklist terms that suggest this is NOT a transaction total
    # Aligned with parser.py blacklist_contexts
    # Note: "credit card" is a payment method, not a blacklist term
    blacklist_terms = [
        'balance', 'refund', 'discount',  # Original terms
        'liability', 'coverage', 'insurance', 'limit', 'maximum', 'up to',  # Insurance/limits
        'points', 'pts', 'miles', 'rewards',  # Loyalty programs
        'booking reference', 'confirmation', 'reference',  # IDs/references
        'tax breakdown', 'breakdown', 'tax %'  # Tax detail sections
    ]
    in_blacklist_context = any(term in context for term in blacklist_terms)

    return AmountCandidate(
        value=value,
        pattern_name=pattern_name,
        match_span=match_span,
        priority=priority,
        raw_text=raw_text,
        proximity_to_keywords=proximity,
        has_strong_prefix=has_strong_prefix,
        in_subtotal_context=in_subtotal_context,
        in_blacklist_context=in_blacklist_context
    )


def create_vendor_candidate(
    value: str,
    pattern_name: str,
    match_span: tuple[int, int],
    raw_text: str,
    line_position: int,
    from_email_header: bool = False,
    from_subject: bool = False,
    raw_line: str = "",
    normalized_line: str = ""
) -> VendorCandidate:
    """
    Create VendorCandidate with computed structure flags.

    Args:
        value: Extracted vendor name (final display format)
        pattern_name: Name of pattern that matched
        match_span: Character span of match
        raw_text: Original matched text
        line_position: Line number in text
        from_email_header: Extracted from email From:/Reply-To:
        from_subject: Extracted from email subject
        raw_line: Original OCR text before normalization
        normalized_line: After OCR normalization, before cleaning

    Returns:
        VendorCandidate with computed flags
    """
    # Structural analysis
    company_suffixes = [
        'inc', 'llc', 'ltd', 'corp', 'corporation',
        'company', 'co', 'gmbh', 'limited', 'sa', 'ag'
    ]
    has_company_suffix = any(value.lower().endswith(suffix) for suffix in company_suffixes)

    # Title case check (each word starts with capital)
    is_title_case = value.istitle() or (
        value[0].isupper() and not value.isupper()
    )

    word_count = len(value.split())

    return VendorCandidate(
        value=value,
        pattern_name=pattern_name,
        match_span=match_span,
        raw_text=raw_text,
        priority=100,
        raw_line=raw_line or raw_text,  # Default to raw_text if not provided
        normalized_line=normalized_line or value,  # Default to value if not provided
        from_email_header=from_email_header,
        from_subject=from_subject,
        line_position=line_position,
        has_company_suffix=has_company_suffix,
        is_title_case=is_title_case,
        word_count=word_count
    )


def create_date_candidate(
    value: str,
    pattern_name: str,
    match_span: tuple[int, int],
    raw_text: str,
    priority: int,
    line_position: int,
    text: str,
    is_ambiguous: bool = False,
    detected_locale: Optional[str] = None
) -> DateCandidate:
    """
    Create DateCandidate with computed context flags.

    Args:
        value: ISO-formatted date (YYYY-MM-DD)
        pattern_name: Name of pattern that matched
        match_span: Character span of match
        raw_text: Original matched text
        priority: Pattern priority
        line_position: Line number in text
        text: Full text for context analysis
        is_ambiguous: Whether format is ambiguous (MM/DD vs DD/MM)
        detected_locale: Detected locale if ambiguous

    Returns:
        DateCandidate with computed flags
    """
    # Check for strong prefix keywords
    start, _ = match_span
    context_start = max(0, start - 20)
    prefix = text[context_start:start].lower()

    strong_keywords = ['date:', 'issued:', 'purchase date:', 'transaction date:']
    has_strong_prefix = any(kw in prefix for kw in strong_keywords)

    return DateCandidate(
        value=value,
        pattern_name=pattern_name,
        match_span=match_span,
        raw_text=raw_text,
        priority=priority,
        line_position=line_position,
        has_strong_prefix=has_strong_prefix,
        is_ambiguous=is_ambiguous,
        detected_locale=detected_locale
    )


def create_currency_candidate(
    value: str,
    pattern_name: str,
    match_span: tuple[int, int],
    raw_text: str,
    priority: int,
    is_explicit: bool,
    text: str
) -> CurrencyCandidate:
    """
    Create CurrencyCandidate with computed context.

    Args:
        value: ISO currency code (USD, EUR, etc.)
        pattern_name: Name of pattern that matched
        match_span: Character span of match
        raw_text: Original matched text
        priority: Pattern priority
        is_explicit: True if "USD" written out, False if symbol
        text: Full text for context analysis

    Returns:
        CurrencyCandidate with computed flags
    """
    # Count occurrences
    context_count = text.lower().count(raw_text.lower())

    return CurrencyCandidate(
        value=value,
        pattern_name=pattern_name,
        match_span=match_span,
        raw_text=raw_text,
        priority=priority,
        symbol_proximity=999,  # Will be computed during amount matching
        is_explicit=is_explicit,
        context_count=context_count
    )
