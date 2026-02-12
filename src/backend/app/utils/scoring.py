"""
Scoring functions for extraction candidates.

Each function returns a score from 0.0 (worst) to 1.0 (best).
The highest-scoring candidate is selected as the final result.
"""

from typing import List, Optional, TypeVar
from decimal import Decimal
import math
import re

from .candidates import (
    Candidate,
    AmountCandidate,
    VendorCandidate,
    DateCandidate,
    CurrencyCandidate
)

__all__ = [
    'select_best_candidate', 'select_top_candidates',
    'select_best_amount', 'select_best_vendor', 'select_best_date', 'select_best_currency',
    'select_top_amounts', 'select_top_vendors', 'select_top_dates', 'select_top_currencies',
    'score_amount_candidate', 'score_vendor_candidate', 'score_date_candidate', 'score_currency_candidate'
]

T = TypeVar('T', bound=Candidate)


def score_amount_candidate(candidate: AmountCandidate, text: str) -> float:
    """
    Score amount candidate based on pattern quality and context.

    Scoring factors (weights):
    - Base priority: 1.0 / priority (normalized)
    - Strong prefix bonus: +0.3 if "Total", "Amount Due", etc.
    - Proximity bonus: Up to +0.2 based on distance to keywords
    - Subtotal penalty: -0.4 if near "Subtotal"
    - Blacklist penalty: -0.5 if near "Balance", "Credit", "Refund"

    Args:
        candidate: AmountCandidate to score
        text: Full text for additional context

    Returns:
        Score from 0.0 to 1.0
    """
    # Base score from pattern priority (lower priority = higher score)
    # Priority 1 = 1.0, Priority 10 = 0.5, Priority 100 = 0.1
    base_score = 1.0 / (1.0 + math.log10(candidate.priority))

    # Strong prefix bonus
    if candidate.has_strong_prefix:
        base_score += 0.3

    # Proximity bonus (inverse relationship)
    # proximity=0 → +0.2, proximity=50 → +0.1, proximity=100+ → +0.0
    if candidate.proximity_to_keywords < 100:
        proximity_bonus = 0.2 * (1.0 - candidate.proximity_to_keywords / 100.0)
        base_score += proximity_bonus

    # Context penalties
    if candidate.in_subtotal_context:
        base_score -= 0.4

    if candidate.in_blacklist_context:
        base_score -= 0.5

    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, base_score))


def _looks_like_person_name(name: str) -> bool:
    """
    Detect if a vendor name looks like a person's name (First Last format).

    Used to penalize customer names that appear in forwarded email headers.

    Args:
        name: Potential vendor name

    Returns:
        True if it looks like a person name (e.g., "John Smith", "Jorden Shaw")
    """
    # Split into words
    words = name.split()

    # Person names are typically 2-3 words (First Last or First Middle Last)
    if len(words) < 2 or len(words) > 3:
        return False

    # Check if all words are title case and relatively short (< 15 chars each)
    # Business names often have longer words or special characters
    for word in words:
        if not word[0].isupper():  # Must start with capital
            return False
        if len(word) > 15:  # Person name parts are usually short
            return False
        if not word.replace('-', '').replace("'", '').isalpha():  # Only letters (allow hyphen/apostrophe)
            return False

    # Common business suffixes and terms indicate NOT a person name
    business_indicators = ['Inc', 'LLC', 'Ltd', 'Limited', 'Corp', 'Corporation',
                          'Co', 'Company', 'Group', 'Partners', 'Associates',
                          'Clinic', 'Medical', 'Pharmacy', 'Store', 'Shop', 'Cafe',
                          'Eyeware', 'Eyecare', 'Optical', 'Optometry', 'Dental',
                          'Restaurant', 'Bar', 'Grill', 'Hotel', 'Spa', 'Salon',
                          'Unlimited', 'Premium', 'Pro', 'Plus', 'Express', 'Online',
                          'Digital', 'Games', 'Software', 'Services', 'Solutions']
    if any(indicator in words for indicator in business_indicators):
        return False

    return True


def score_vendor_candidate(candidate: VendorCandidate) -> float:
    """
    Score vendor candidate based on structural features only.

    Phase 1 Enhanced: Early-line boosting, improved business context scoring.

    NO hardcoded vendor names. Scoring is purely structural:
    - From email header (From:/Reply-To:): 0.9 base
    - From email subject: 0.7 base
    - From body text: 0.5 base
    - Company suffix (Inc, LLC, Ltd): +0.1
    - Title case: +0.1
    - Early-line boost: +0.25 (line 0), +0.15 (line 1), +0.10 (line 2)
    - Line position penalty: -0.02 per line after line 2
    - Word count penalty: -0.1 if > 5 words
    - Person name penalty: -0.6 if looks like "First Last" from email header (likely forwarded)

    Args:
        candidate: VendorCandidate to score

    Returns:
        Score from 0.0 to 1.0
    """
    # Base score by source and pattern
    if candidate.from_email_header:
        base_score = 0.9
    elif candidate.from_subject:
        base_score = 0.7
    elif candidate.pattern_name == 'payable_to':
        base_score = 0.85  # "Make cheques payable to..." is explicit vendor declaration
    elif candidate.pattern_name == 'business_keyword':
        base_score = 0.75  # Business-type keywords (Clinic, Eyeware, etc.) strongly indicate vendor
    elif candidate.pattern_name == 'company_suffix':
        base_score = 0.7  # Inc/LLC/Ltd strongly indicates business entity
    else:
        base_score = 0.5

    # Structural bonuses
    if candidate.has_company_suffix and candidate.pattern_name != 'company_suffix':
        base_score += 0.1  # Bonus if not already scored as company_suffix

    if candidate.is_title_case:
        base_score += 0.1

    # PHASE 1 ENHANCEMENT: Early-line boosting
    # Vendor typically appears in first 3 lines - give strong preference
    EARLY_LINE_BOOST = {
        0: 0.25,  # Line 0 (very first line) - strong boost
        1: 0.15,  # Line 1 - moderate boost
        2: 0.10,  # Line 2 - small boost
    }

    if candidate.line_position in EARLY_LINE_BOOST:
        boost = EARLY_LINE_BOOST[candidate.line_position]
        base_score += boost
    elif candidate.line_position > 2:
        # Line position penalty for lines after 2 (earlier lines = better)
        # Line 3: -0.02, Line 10: -0.16, Line 20+: -0.36 (capped at -0.4)
        line_penalty = min(0.4, (candidate.line_position - 2) * 0.02)
        base_score -= line_penalty

    # Word count penalty for excessively long names only
    # Single-word names are valid (Walmart, Apple, Uber, etc.)
    # Penalize only names with > 5 words (likely extracted too much text)
    if candidate.word_count > 5:
        base_score -= 0.1

    # Person name penalty (detect customer names in forwarded emails)
    # If this looks like "First Last" and comes from email header, heavily penalize
    # This handles cases where user forwards receipt and their name appears as sender
    if candidate.from_email_header or candidate.pattern_name == 'context_sender_name':
        if _looks_like_person_name(candidate.value):
            base_score -= 0.6  # Heavy penalty - likely customer, not vendor

    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, base_score))


def score_date_candidate(candidate: DateCandidate) -> float:
    """
    Score date candidate based on pattern quality and context.

    Scoring factors:
    - Base priority: 1.0 / priority (normalized)
    - Strong prefix bonus: +0.3 if "Date:", "Issued:", etc.
    - Line position bonus: Up to +0.2 for early lines
    - Ambiguity penalty: -0.2 if format is ambiguous without locale hint

    Args:
        candidate: DateCandidate to score

    Returns:
        Score from 0.0 to 1.0
    """
    # Base score from pattern priority
    base_score = 1.0 / (1.0 + math.log10(candidate.priority))

    # Strong prefix bonus
    if candidate.has_strong_prefix:
        base_score += 0.3

    # Line position bonus (earlier = better)
    # Line 0-5: +0.2, Line 10: +0.1, Line 20+: +0.0
    if candidate.line_position <= 20:
        line_bonus = 0.2 * (1.0 - candidate.line_position / 20.0)
        base_score += line_bonus

    # Ambiguity penalty
    if candidate.is_ambiguous and not candidate.detected_locale:
        base_score -= 0.2

    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, base_score))


def score_currency_candidate(candidate: CurrencyCandidate) -> float:
    """
    Score currency candidate based on evidence strength.

    Scoring factors:
    - Explicit mention (USD, CAD): 0.9 base
    - Symbol only ($, €): 0.6 base
    - Context count bonus: +0.05 per occurrence (max +0.3)
    - Symbol proximity bonus: Up to +0.1 based on distance to amount

    Args:
        candidate: CurrencyCandidate to score

    Returns:
        Score from 0.0 to 1.0
    """
    # Base score by explicitness
    if candidate.is_explicit:
        base_score = 0.9
    else:
        base_score = 0.6

    # Context count bonus (more mentions = higher confidence)
    # 1 mention: +0.0, 3 mentions: +0.1, 6+ mentions: +0.3
    context_bonus = min(0.3, (candidate.context_count - 1) * 0.05)
    base_score += context_bonus

    # Symbol proximity bonus (if set)
    if candidate.symbol_proximity < 10:
        proximity_bonus = 0.1 * (1.0 - candidate.symbol_proximity / 10.0)
        base_score += proximity_bonus

    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, base_score))


def select_top_candidates(
    candidates: List[T],
    score_func,
    top_n: int = 3
) -> List[tuple[T, float]]:
    """
    Select top N candidates from list using scoring function.

    Args:
        candidates: List of candidates to score
        score_func: Function that takes a candidate and returns a score
        top_n: Number of top candidates to return (default 3)

    Returns:
        List of (candidate, score) tuples, sorted by score descending

    Example:
        >>> top_3 = select_top_candidates(amount_candidates, score_amount_candidate, 3)
    """
    if not candidates:
        return []

    # Score all candidates
    scored = [(candidate, score_func(candidate)) for candidate in candidates]

    # Sort by score (descending)
    scored.sort(key=lambda x: x[1], reverse=True)

    # Return top N
    return scored[:top_n]


def select_best_candidate(
    candidates: List[T],
    score_func
) -> Optional[T]:
    """
    Select best candidate from list using scoring function.

    Args:
        candidates: List of candidates to score
        score_func: Function that takes a candidate and returns a score

    Returns:
        Highest-scoring candidate, or None if empty list

    Example:
        >>> best = select_best_candidate(amount_candidates, score_amount_candidate)
    """
    if not candidates:
        return None

    # Score all candidates
    scored = [(candidate, score_func(candidate)) for candidate in candidates]

    # Sort by score (descending)
    scored.sort(key=lambda x: x[1], reverse=True)

    # Return best candidate
    best_candidate, best_score = scored[0]

    # Threshold: only return if score > 0.3
    if best_score < 0.3:
        return None

    return best_candidate


def select_best_amount(
    candidates: List[AmountCandidate],
    text: str
) -> Optional[AmountCandidate]:
    """
    Select best amount candidate.

    Args:
        candidates: List of AmountCandidate objects
        text: Full text for context scoring

    Returns:
        Best candidate or None
    """
    if not candidates:
        return None

    # Score all candidates
    scored = [
        (candidate, score_amount_candidate(candidate, text))
        for candidate in candidates
    ]

    # Sort by score (descending)
    scored.sort(key=lambda x: x[1], reverse=True)

    # Return best if above threshold
    best_candidate, best_score = scored[0]
    if best_score < 0.3:
        return None

    return best_candidate


def select_best_vendor(
    candidates: List[VendorCandidate]
) -> Optional[VendorCandidate]:
    """
    Select best vendor candidate.

    Args:
        candidates: List of VendorCandidate objects

    Returns:
        Best candidate or None
    """
    return select_best_candidate(candidates, score_vendor_candidate)


def select_best_date(
    candidates: List[DateCandidate]
) -> Optional[DateCandidate]:
    """
    Select best date candidate.

    Args:
        candidates: List of DateCandidate objects

    Returns:
        Best candidate or None
    """
    return select_best_candidate(candidates, score_date_candidate)


def select_best_currency(
    candidates: List[CurrencyCandidate]
) -> Optional[CurrencyCandidate]:
    """
    Select best currency candidate.

    Args:
        candidates: List of CurrencyCandidate objects

    Returns:
        Best candidate or None
    """
    return select_best_candidate(candidates, score_currency_candidate)


# Top N candidate selection functions for review UI

def select_top_vendors(
    candidates: List[VendorCandidate],
    top_n: int = 3
) -> List[tuple[VendorCandidate, float]]:
    """Select top N vendor candidates with scores."""
    return select_top_candidates(candidates, score_vendor_candidate, top_n)


def select_top_amounts(
    candidates: List[AmountCandidate],
    text: str,
    top_n: int = 3
) -> List[tuple[AmountCandidate, float]]:
    """Select top N amount candidates with scores."""
    return select_top_candidates(
        candidates,
        lambda c: score_amount_candidate(c, text),
        top_n
    )


def select_top_dates(
    candidates: List[DateCandidate],
    top_n: int = 3
) -> List[tuple[DateCandidate, float]]:
    """Select top N date candidates with scores."""
    return select_top_candidates(candidates, score_date_candidate, top_n)


def select_top_currencies(
    candidates: List[CurrencyCandidate],
    top_n: int = 3
) -> List[tuple[CurrencyCandidate, float]]:
    """Select top N currency candidates with scores."""
    return select_top_candidates(candidates, score_currency_candidate, top_n)
