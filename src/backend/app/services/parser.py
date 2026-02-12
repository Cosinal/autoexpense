"""
Receipt parser service for extracting structured data from OCR text.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.utils.money import parse_money, MoneyFormat
from app.utils.candidates import (
    AmountCandidate,
    DateCandidate,
    VendorCandidate,
    CurrencyCandidate,
    create_amount_candidate,
    create_vendor_candidate,
    create_date_candidate,
    create_currency_candidate,
)
from app.utils.scoring import (
    select_best_amount,
    select_best_vendor,
    select_best_date,
    select_best_currency,
    select_top_amounts,
    select_top_vendors,
    select_top_dates,
    select_top_currencies,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PatternSpec:
    """A named regex pattern with example and notes for documentation."""
    name: str
    pattern: str
    example: str
    notes: Optional[str] = None
    priority: Optional[int] = None
    flags: int = re.IGNORECASE
    compiled: re.Pattern = field(default=None, init=False, compare=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, 'compiled', re.compile(self.pattern, self.flags))


@dataclass
class ParseContext:
    """
    Context object carrying metadata hints from upstream to the parser.

    These hints improve parsing accuracy without hardcoding vendor-specific logic.
    All fields are optional and can be None.
    """
    sender_domain: Optional[str] = None  # Email sender domain (e.g., "sephora.com")
    sender_name: Optional[str] = None    # Email sender display name
    subject: Optional[str] = None        # Email subject line
    user_locale: Optional[str] = None    # User's locale hint (e.g., "US", "EU")
    user_currency: Optional[str] = None  # User's preferred currency (e.g., "USD")
    billing_country: Optional[str] = None  # User's billing country if known


class ReceiptParser:
    """Service for parsing receipt text and extracting structured data."""

    # PHASE 1: Scoring weight constants (documented for maintainability)
    # Early-line boosting: Vendor typically appears in first 3 lines
    EARLY_LINE_BOOST = {
        0: 0.25,  # Line 0 (very first line) - strong boost
        1: 0.15,  # Line 1 - moderate boost
        2: 0.10,  # Line 2 - small boost
        # Lines 3+: use line position penalty instead
    }

    # Business context weights: Additional score for business indicators
    BUSINESS_CONTEXT_WEIGHTS = {
        'retail': 0.15,       # "Store", "Shop", "Market", "Outlet"
        'service': 0.12,      # "Clinic", "Salon", "Spa", "Services"
        'food': 0.12,         # "Restaurant", "Cafe", "Bar", "Grill"
        'professional': 0.10, # "Inc", "LLC", "Ltd", "Corp"
        'medical': 0.15,      # "Medical", "Dental", "Optical", "Pharmacy"
    }

    # Confidence thresholds for Phase 2/3 fallback
    CONFIDENCE_THRESHOLDS = {
        'high': 0.8,      # Very confident, no fallback needed
        'medium': 0.6,    # Moderately confident, consider DB lookup (Phase 2)
        'low': 0.4,       # Low confidence, needs LLM arbitration (Phase 3)
        'reject': 0.3,    # Too uncertain, mark for manual review
    }

    def __init__(self):
        """Initialize parser with regex patterns."""
        self._init_patterns()
        self._forwarded_email_cache = {}  # Cache forwarded detection results

    def _init_patterns(self):
        """Initialize regex patterns for parsing."""

        # IMPROVED: Priority-based amount patterns (lower number = higher priority)
        self.amount_patterns = [
            PatternSpec(
                name='explicit_payment',
                pattern=r'(?:amount\s+paid|total\s+paid|grand\s+total|final\s+total)[\s:]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='Amount Paid: $59.52',
                notes='Explicit payment indicators (highest confidence)',
                priority=1,
                flags=re.IGNORECASE | re.MULTILINE,
            ),
            PatternSpec(
                name='markdown_bold_total',
                pattern=r'\*\*total[\s:]+\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})\*\*',
                example='**Total: $59.52**',
                notes='Markdown bold total (Sephora)',
                priority=1,
                flags=re.IGNORECASE | re.MULTILINE,
            ),
            PatternSpec(
                name='order_summary_pipe',
                pattern=r'(?:order\s+summary|payment\s+summary)[\s\S]{0,200}?(?<!sub)total:\s*\|\s*[A-Z]{0,2}\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='Order Summary ... Total: | C$93.79',
                notes='Order Summary with pipe separator (Urban Outfitters)',
                priority=1,
                flags=re.IGNORECASE | re.MULTILINE,
            ),
            PatternSpec(
                name='total_pipe_cad',
                pattern=r'(?<!sub)total:\s*\|\s*C\$\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='Total: | C$93.79',
                notes='Total with pipe and C$ (Urban Outfitters)',
                priority=1,
                flags=re.IGNORECASE | re.MULTILINE,
            ),
            PatternSpec(
                name='total_cad_format',
                pattern=r'total\s+cad\s+\$\s*\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='TOTAL CAD $ 153.84',
                notes='TOTAL CAD $ format (PSA Canada)',
                priority=1,
                flags=re.IGNORECASE | re.MULTILINE,
            ),
            PatternSpec(
                name='table_pipe_currency',
                pattern=r'(?<!sub)(?:total|grand\s+total)[\s:*]*\|\s*(\d{1,3}(?:,\d{3})*\.?\d{0,2})\s*(?:CAD|USD|EUR|GBP|AUD)',
                example='Total | 6.99 CAD',
                notes='Table format with pipe separator and currency code (Steam)',
                priority=2,
                flags=re.IGNORECASE | re.MULTILINE,
            ),
            PatternSpec(
                name='markdown_bold_pipe',
                pattern=r'\*\*(?:total|amount\s+due)\*\*[\s:]*\|\s*(\d{1,3}(?:,\d{3})*\.?\d{0,2})',
                example='**Total** | 59.52',
                notes='Markdown bold total with pipe',
                priority=2,
                flags=re.IGNORECASE | re.MULTILINE,
            ),
            PatternSpec(
                name='total_strong_context',
                pattern=r'(?:^|\n|\|)\s*total[\s:]+[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='Total: $59.52',
                notes='Total with strong context',
                priority=2,
                flags=re.IGNORECASE | re.MULTILINE,
            ),
            PatternSpec(
                name='generic_total',
                pattern=r'(?<!sub)(?<!Sub)(?<!SUB)(?:total|amount|sum|paid)[\s:\|]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='Total $59.52',
                notes='Generic total/amount (exclude subtotal)',
                priority=3,
                flags=re.IGNORECASE | re.MULTILINE,
            ),
            PatternSpec(
                name='amount_currency_code',
                pattern=r'(\d{1,3}(?:,\d{3})*\.\d{2})\s+(?:CAD|USD|EUR|GBP|AUD|NZD|CHF)',
                example='59.52 CAD',
                notes='Amount followed by currency code (lower priority)',
                priority=4,
                flags=re.IGNORECASE | re.MULTILINE,
            ),
            PatternSpec(
                name='currency_symbol',
                pattern=r'[$€£¥]\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                example='$59.52',
                notes='Currency symbol (last resort)',
                priority=4,
                flags=re.IGNORECASE | re.MULTILINE,
            ),
            PatternSpec(
                name='euro_spaced',
                pattern=r'€\s+(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='€ 59.52',
                notes='Euro with spaces (European format)',
                priority=4,
                flags=re.IGNORECASE | re.MULTILINE,
            ),
        ]

        # Blacklist contexts - amounts to ignore
        self.blacklist_contexts = [
            'liability', 'coverage', 'insurance', 'limit', 'maximum',
            'up to', 'points', 'pts', 'booking reference', 'confirmation',
            'reference', 'miles', 'rewards',
            'tax breakdown', 'breakdown', 'tax %'  # Tax detail sections
        ]

        # Date patterns
        self.date_patterns = [
            PatternSpec(
                name='numeric_date_ambiguous',
                pattern=r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                example='01/15/2024',
                notes='MM/DD/YYYY or DD/MM/YYYY — resolved by locale detection',
            ),
            PatternSpec(
                name='month_name_date',
                pattern=r'([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})',
                example='Jan 15, 2024',
            ),
            PatternSpec(
                name='month_slash_date',
                pattern=r'([A-Za-z]{3,9}\s+\d{1,2}/\d{4})',
                example='April 9/2025',
            ),
            PatternSpec(
                name='iso_date',
                pattern=r'(\d{4}-\d{2}-\d{2})',
                example='2024-01-15',
            ),
            PatternSpec(
                name='date_paid_issued',
                pattern=r'date\s+(?:paid|issued|of\s+issue)[\s:]*([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})',
                example='Date paid October 26, 2025',
                notes='Explicit date paid/issued indicator (high confidence - Anthropic/Air Canada fix)',
                priority=1,
            ),
            PatternSpec(
                name='ordinal_date',
                pattern=r'(\d{1,2}(?:st|nd|rd|th)\s+[A-Za-z]{3,9}\s+\d{4})',
                example='23rd November 2025',
                notes='Ordinal dates (GeoGuessr fix)',
            ),
        ]

        # IMPROVED: Tax patterns with pipe separator support
        # Note: "Tax total" and "Tax breakdown" lines are summary re-statements,
        # not additional tax lines — only patterns that match primary tax labels.
        self.tax_patterns = [
            PatternSpec(
                name='vat_with_percent',
                pattern=r'vat[\s:()%\d\|]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='VAT (23%): € 643.77',
            ),
            PatternSpec(
                name='tax_generic',
                pattern=r'tax[\s:\|]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='Tax: $5.99',
            ),
            PatternSpec(
                name='sales_tax_hst_gst',
                pattern=r'(?:sales tax|hst|gst|pst)[\s:()%\d\|]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='HST: $1.09',
            ),
            PatternSpec(
                name='percent_gst_hst',
                pattern=r'\d+%\s+(?:gst|hst|pst)(?:/[A-Z]+)?[\s:]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='5% GST/HST       19.75',
                notes='Percentage prefix GST/HST format (Louis Vuitton fix)',
            ),
            PatternSpec(
                name='harmonized_sales_tax',
                pattern=r'harmonized\s+sales\s+tax[^\n]*\n[^\n]*?(\d{1,2}\.\d{2})$',
                example='Harmonized Sales Tax - Canada - 100092287\nRT00012.65',
                notes='Full "Harmonized Sales Tax" multi-line - extracts amount at end of next line (Air Canada fix)',
                flags=re.IGNORECASE | re.MULTILINE,
            ),
            PatternSpec(
                name='tax_pipe_separator',
                pattern=r'(?:hst|gst|tax|vat)\s*\|\s*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='HST| $1.09',
                notes='Pipe separator support',
            ),
            PatternSpec(
                name='hst_gst_no_colon',
                pattern=r'(?:hst|gst)\s+[$€£¥]\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='HST $1.09',
            ),
            PatternSpec(
                name='country_prefix_tax',
                pattern=r'(?:[A-Z\s]+\s+)?(?:gst|hst|pst)(?:/[A-Z]+)?\s*\([^\)]+\)[\s:]*(?:[A-Z]{2,3})?\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='HST - Canada (14% on CA$28.00) CA$3.92',
                notes='Country-prefix tax with optional colon and currency code (Anthropic fix)',
            ),
            PatternSpec(
                name='tax_pipe_urban',
                pattern=r'tax:\s*\|\s*[A-Z]{0,2}\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='Tax: | C$10.79',
                notes='Urban Outfitters - tax with pipe separator',
            ),
            PatternSpec(
                name='sales_tax_multiline',
                pattern=r'sales\s+tax\s*\n\s*([A-Z]{2,3})?\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='Sales Tax\n$0.33',
                notes='GeoGuessr - multi-line sales tax (excludes "Tax total" summary lines)',
            ),
            PatternSpec(
                name='linkedin_gst',
                pattern=r'(?:gst|hst|pst)[\s:]*\d+%[\s\S]*?(?:[A-Z]{2,3})?\s*\$\s*\d{1,3}(?:,\d{3})*\.\d{2}[\s\S]{0,50}?([A-Z]{2,3})?\s*\$\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='GST : 5% ... CA $ 1.19 ... CA $ 1.19',
                notes='LinkedIn - GST/HST/PST with percentage, multi-line amount',
            ),
        ]

        # Subtotal patterns
        self.subtotal_patterns = [
            PatternSpec(
                name='subtotal',
                pattern=r'(?:sub\s*total|subtotal)[\s:]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='Subtotal: $50.00',
            ),
            PatternSpec(
                name='trip_fare',
                pattern=r'(?:trip\s+fare|fare)[\s:\|]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='Trip Fare: $10.00',
            ),
        ]

        # Email skip patterns (pre-compiled)
        self.email_skip_patterns = [
            re.compile(r'^\s*[-=]+\s*forwarded\s+message\s*[-=]+', re.IGNORECASE),
            re.compile(r'^\s*from:\s*', re.IGNORECASE),
            re.compile(r'^\s*to:\s*', re.IGNORECASE),
            re.compile(r'^\s*date:\s*', re.IGNORECASE),
            re.compile(r'^\s*subject:\s*', re.IGNORECASE),
            re.compile(r'^\s*sent:\s*', re.IGNORECASE),
            re.compile(r'^\s*cc:\s*', re.IGNORECASE),
            re.compile(r'^\s*\[?https?://', re.IGNORECASE),
            re.compile(r'^\s*mailto:', re.IGNORECASE),
            re.compile(r'^\s*page\s+\d+', re.IGNORECASE),
            re.compile(r'^\s*page\s+\d+\s+of\s+\d+', re.IGNORECASE),
            re.compile(r'^\s*\d+\s+of\s+\d+', re.IGNORECASE),
            re.compile(r'^\s*p\s*a\s*g\s*e\s+\d+', re.IGNORECASE),
        ]

        # Currency symbols
        self.currency_map = {
            '$': 'USD',
            '€': 'EUR',
            '£': 'GBP',
            '¥': 'JPY',
            'USD': 'USD',
            'EUR': 'EUR',
            'GBP': 'GBP',
            'CAD': 'CAD',
        }

    def parse(self, text: str, context: Optional[ParseContext] = None, bbox_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Parse receipt text and extract all available fields.

        Args:
            text: OCR-extracted text from receipt
            context: Optional context with email metadata hints
            bbox_data: Optional bounding box data for spatial extraction (Phase 2)

        Returns:
            Dictionary with parsed fields and candidate options for review

        TODO Phase 2: Integrate bbox spatial extraction
        =============================================
        When bbox_data is provided (image-based receipts):
        1. Try bbox extraction first using BboxExtractor
        2. Use bbox results for fields with high confidence
        3. Fall back to pattern-based for missing/low-confidence fields
        4. Merge results with confidence scoring

        Example integration:
            if bbox_data:
                from app.services.bbox_extractor import BboxExtractor
                bbox_extractor = BboxExtractor(bbox_data)

                # Try bbox extraction
                bbox_tax = bbox_extractor.extract_tax()
                bbox_amount = bbox_extractor.extract_amount()

                # Use bbox results if available, fallback to patterns
                result['tax'] = bbox_tax if bbox_tax else self.extract_tax(text)
                result['amount'] = bbox_amount if bbox_amount else self.extract_amount(text)

        See: BBOX_PHASE1_RESULTS.md for full integration plan
        """
        # Normalize OCR spacing issues globally before parsing
        # Handles cases like "O c t o b e r 2 6" → "October 26"
        text = self._normalize_ocr_spaces(text)

        debug = {
            'patterns_matched': {},
            'confidence_per_field': {},
            'warnings': [],
            'review_candidates': {}  # Top candidates for manual review
        }

        result = {
            'vendor': self.extract_vendor(text, context=context, _debug=debug),
            'amount': self.extract_amount(text, context=context, _debug=debug),
            'currency': self.extract_currency(text, context=context, _debug=debug),
            'date': self.extract_date(text, context=context, _debug=debug),
            'tax': self.extract_tax(text, _debug=debug),
            'confidence': 0.0,
            'debug': debug,
        }

        # Validate amount consistency (subtotal + tax ≈ total)
        self._validate_amount_consistency(
            result['amount'],
            result['tax'],
            text,
            debug
        )

        result['confidence'] = self._calculate_confidence(result)

        # Capture top candidates for fields that need review (confidence < 0.7)
        self._capture_review_candidates(text, context, result, debug)

        # PHASE 1 LAUNCH: Explicit review flag for safety-critical routing
        # Prevent auto-export when any critical field has low confidence
        result['needs_review'] = self._requires_review(result, debug)

        return result

    def _requires_review(
        self,
        result: Dict[str, Any],
        debug: Dict[str, Any]
    ) -> bool:
        """
        Determine if receipt needs manual review before export.

        PHASE 1 LAUNCH: Critical safety gate to prevent silent errors.

        Returns True if ANY of:
        - Overall confidence < 0.7
        - Vendor confidence < 0.7 (critical for categorization)
        - Amount confidence < 0.7 (critical for accounting)
        - Amount validation failed (subtotal + tax != total)
        - Any extraction completely failed (None/missing)

        Args:
            result: Parsed receipt data
            debug: Debug metadata with confidence scores

        Returns:
            True if receipt should be reviewed before export
        """
        # Check overall confidence
        if result.get('confidence', 0.0) < 0.7:
            return True

        # Check critical field confidence
        confidence_per_field = debug.get('confidence_per_field', {})

        vendor_conf = confidence_per_field.get('vendor', 0.0)
        amount_conf = confidence_per_field.get('amount', 0.0)

        if vendor_conf < 0.7 or amount_conf < 0.7:
            return True

        # Check if any critical field is missing
        if result.get('vendor') is None or result.get('amount') is None:
            return True

        # Check amount consistency validation
        validation = debug.get('amount_validation', {})
        if validation and not validation.get('is_consistent', True):
            return True  # Inconsistent subtotal+tax should be reviewed

        return False

    def _capture_review_candidates(
        self,
        text: str,
        context: Optional[ParseContext],
        result: Dict[str, Any],
        debug: Dict[str, Any]
    ) -> None:
        """
        Capture top 3 candidates for each field to present in review UI.

        Only captures candidates for fields with low confidence that need review.
        """
        review_candidates = {}

        # Check each field's confidence
        confidence_per_field = debug.get('confidence_per_field', {})

        # Vendor candidates (if confidence < 0.7)
        vendor_conf = confidence_per_field.get('vendor', 0.0)
        if vendor_conf < 0.7 and 'vendor_candidates' in debug:
            review_candidates['vendor'] = {
                'current_value': result.get('vendor'),
                'confidence': vendor_conf,
                'options': debug['vendor_candidates']  # Top 3 from extract_vendor
            }

        # Amount candidates (if confidence < 0.7)
        amount_conf = confidence_per_field.get('amount', 0.0)
        if amount_conf < 0.7 and 'amount_candidates' in debug:
            review_candidates['amount'] = {
                'current_value': str(result.get('amount')) if result.get('amount') else None,
                'confidence': amount_conf,
                'options': debug['amount_candidates']  # Top 3 from extract_amount
            }

        # Date candidates (if confidence < 0.7)
        date_conf = confidence_per_field.get('date', 0.0)
        if date_conf < 0.7 and 'date_candidates' in debug:
            review_candidates['date'] = {
                'current_value': result.get('date'),
                'confidence': date_conf,
                'options': debug['date_candidates']  # Top 3 from extract_date
            }

        # Currency candidates (if confidence < 0.7)
        currency_conf = confidence_per_field.get('currency', 0.0)
        if currency_conf < 0.7 and 'currency_candidates' in debug:
            review_candidates['currency'] = {
                'current_value': result.get('currency'),
                'confidence': currency_conf,
                'options': debug['currency_candidates']  # Top 3 from extract_currency
            }

        debug['review_candidates'] = review_candidates

    def _normalize_ocr_spaces(self, text: str) -> str:
        """
        Remove OCR-induced extra spaces between characters.
        Handles cases like:
        - "L o v a b l e" → "Lovable" (character-level spacing)
        - "H S T  -  C a n a d a" → "HST - Canada" (excessive spacing)
        - "I n v o i c e" → "Invoice" (single-char spacing)

        Phase 1 Enhanced: More aggressive for very high space ratios.
        """
        # Detect excessive spacing (>35% of sample is spaces = likely spaced OCR)
        sample = text[:500]  # Check first 500 chars
        if len(sample) > 0:
            space_ratio = sample.count(' ') / len(sample)

            if space_ratio > 0.45:
                # VERY aggressive normalization for extreme spacing (> 45%)
                # Remove ALL single spaces between single characters
                # "I n v o i c e" → "Invoice"
                text = re.sub(r'\b([A-Za-z])\s+(?=[A-Za-z]\b)', r'\1', text)
                # Then collapse remaining multiple spaces
                text = re.sub(r'\s{2,}', ' ', text)
                return text
            elif space_ratio > 0.35:
                # Aggressive normalization for highly-spaced OCR
                # Collapse multiple spaces to single space
                text = re.sub(r'\s{2,}', ' ', text)
                # Also try character-level fix
                if re.search(r'[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]', text):
                    text = re.sub(r'\b([A-Za-z])\s+(?=[A-Za-z]\b)', r'\1', text)
                return text

        # Normal character-level spacing fix for less severe cases
        if re.search(r'[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]', text):
            pattern = r'\b([A-Za-z])\s+(?=[A-Za-z](\s+|$))'
            while True:
                new_text = re.sub(pattern, r'\1', text)
                if new_text == text:
                    break
                text = new_text
        return text

    def _normalize_vendor_ocr(self, text: str, is_early_line: bool = False) -> str:
        """
        Aggressive OCR normalization specifically for vendor extraction.
        Handles cases like "I N V O I C E" → "INVOICE" and "H S T" → "HST".

        Phase 1 Launch: Extra aggressive normalization for early lines (0-10)
        where vendor names typically appear.

        Args:
            text: Text to normalize
            is_early_line: If True, apply even more aggressive normalization
        """
        # PHASE 1 LAUNCH: Extra aggressive for early lines (header area)
        if is_early_line:
            # Handle both uppercase AND lowercase single-char spacing
            # "I N V O I C E" → "INVOICE"
            # "i n v o i c e" → "invoice"
            if re.search(r'[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]', text):
                # Remove ALL single spaces between single characters (upper or lower)
                text = re.sub(r'\b([A-Za-z])\s+(?=[A-Za-z]\b)', r'\1', text)
        else:
            # Standard aggressive normalization (capitals only)
            # "I N V O I C E" → "INVOICE"
            if re.search(r'[A-Z]\s+[A-Z]\s+[A-Z]', text):
                # Remove all single spaces between single capital letters
                text = re.sub(r'\b([A-Z])\s+(?=[A-Z]\b)', r'\1', text)

        # Step 2: Collapse multiple spaces
        text = re.sub(r'\s{2,}', ' ', text)

        # Step 3: Remove noise characters (preserve hyphens, apostrophes, &)
        text = re.sub(r'[^\w\s&\'-]', '', text)

        # Step 4: Title case for consistency
        text = text.title()

        return text.strip()

    def _detect_forwarded_email(self, text: str, context: Optional[ParseContext]) -> bool:
        """
        Detect if email was forwarded.

        Phase 1 Enhancement: Helps avoid extracting forwarder name as vendor.
        Returns True if email appears to be forwarded.
        """
        # Cache results to avoid re-computing
        cache_key = hash(text[:500])  # Use first 500 chars as key
        if cache_key in self._forwarded_email_cache:
            return self._forwarded_email_cache[cache_key]

        is_forwarded = False

        # Check forwarding indicators in text
        forwarding_patterns = [
            r'[-=]+\s*forwarded message\s*[-=]+',
            r'---------- forwarded',
            r'begin forwarded message',
            r'from:.*\n.*to:.*\n.*subject:',  # Multiple headers = forwarded
        ]

        for pattern in forwarding_patterns:
            if re.search(pattern, text[:1000], re.IGNORECASE):
                is_forwarded = True
                break

        # Check if sender domain is personal email (likely forwarded)
        if not is_forwarded and context and context.sender_domain:
            personal_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com',
                              'icloud.com', 'me.com', 'live.com', 'aol.com']
            if any(domain in context.sender_domain.lower() for domain in personal_domains):
                is_forwarded = True

        self._forwarded_email_cache[cache_key] = is_forwarded
        return is_forwarded

    def _combine_multiline_vendors(self, lines: List[str]) -> List[str]:
        """
        Combine adjacent lines that look like split vendor names.

        Phase 1 Launch: Enhanced for airline names ("Air\\nCanada") and business keywords.

        Args:
            lines: List of text lines

        Returns:
            List with combined vendor names where applicable
        """
        combined = []
        i = 0

        # Document labels and metadata that should NOT be combined
        document_labels = [
            'receipt', 'invoice', 'bill', 'order', 'paid', 'tax',
            'confirmation', 'booking', 'itinerary', 'ticket', 'statement'
        ]

        # Business keywords that strongly suggest vendor continuation
        business_keywords = ['store', 'shop', 'market', 'cafe', 'coffee', 'restaurant',
                            'clinic', 'medical', 'pharmacy', 'hotel', 'spa', 'salon',
                            'eyeware', 'eyecare', 'optical', 'optometry', 'dental',
                            'airlines', 'airways', 'air']

        while i < len(lines):
            line = lines[i].strip()

            # Check if next line continues the vendor name
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()

                # Check if either line is a document label
                is_doc_label = (
                    line.lower() in document_labels or
                    next_line.lower() in document_labels or
                    # Also check for partial matches
                    any(label in line.lower() for label in document_labels) or
                    any(label in next_line.lower() for label in document_labels)
                )

                # PHASE 1 LAUNCH: Airline-specific combination
                # "Air" + anything capitalized (e.g., "Air Canada", "Air France")
                airline_pattern = (
                    line.lower() == 'air' and
                    next_line and
                    next_line[0].isupper() and
                    len(next_line) < 25 and
                    not re.search(r'\d', next_line) and
                    not is_doc_label
                )

                # PHASE 1 LAUNCH: Business keyword combination
                # First line + "Store" / "Shop" / etc. (e.g., "Apple Store", "Browz Eyeware")
                business_continuation = (
                    line and next_line and
                    next_line.lower() in business_keywords and
                    len(line) < 25 and
                    line[0].isupper() and
                    not re.search(r'\d', line) and
                    not is_doc_label
                )

                # Standard combination logic (more permissive than before)
                # - Both are short (< 25 chars each, increased from 20)
                # - Both start with capital letter
                # - No numbers in either (avoid combining with amounts)
                # - Combined length < 50 chars
                # - Not document labels
                standard_combine = (
                    line and next_line and
                    len(line) < 25 and len(next_line) < 25 and
                    line[0].isupper() and next_line[0].isupper() and
                    not re.search(r'\d', line) and
                    not re.search(r'\d', next_line) and
                    len(line + ' ' + next_line) < 50 and
                    not is_doc_label
                )

                should_combine = airline_pattern or business_continuation or standard_combine

                if should_combine:
                    combined.append(line + ' ' + next_line)
                    i += 2
                    continue

            combined.append(line)
            i += 1

        return combined

    def extract_vendor(self, text: str, context: Optional[ParseContext] = None, _debug=None) -> Optional[str]:
        """
        Extract vendor/merchant name using structural scoring (no hardcoded vendor lists).

        Phase 1 Enhanced: Multi-stage pipeline with improved candidate generation.

        Args:
            text: Receipt text
            context: Optional parse context with email metadata

        Returns:
            Vendor name or None
        """
        try:
            candidates: List[VendorCandidate] = []

            # PHASE 1 ENHANCEMENT: Detect forwarded emails early
            is_forwarded = self._detect_forwarded_email(text, context)
            if _debug is not None:
                _debug['vendor_is_forwarded'] = is_forwarded

            # Text is already normalized by parse() method
            lines = text.split('\n')

            # PHASE 1 ENHANCEMENT: Combine multi-line vendor names
            # E.g., "Apple\nStore" → "Apple Store"
            combined_lines = self._combine_multiline_vendors(lines)
            if _debug is not None:
                _debug['vendor_combined_lines'] = len(combined_lines) != len(lines)

            # Strategy 1: Use ParseContext email metadata (highest confidence)
            if context:
                if context.sender_name:
                    cleaned = self._clean_vendor_name(context.sender_name)
                    if cleaned and len(cleaned) > 2:
                        # Remove generic terms
                        cleaned = re.sub(r'\b(receipts?|notifications?|noreply|no-reply)\b', '', cleaned, flags=re.IGNORECASE).strip()
                        if cleaned and len(cleaned) > 2:
                            candidate = create_vendor_candidate(
                                value=cleaned,
                                pattern_name='context_sender_name',
                                match_span=(0, 0),
                                raw_text=context.sender_name,
                                line_position=0,
                                from_email_header=True
                            )
                            candidates.append(candidate)

                if context.subject:
                    # Extract potential vendor from subject
                    subject_match = re.search(r'(?:receipt|order|confirmation).*?(?:from|at)\s+([A-Z][a-zA-Z\s]{2,30})', context.subject, re.IGNORECASE)
                    if subject_match:
                        cleaned = self._clean_vendor_name(subject_match.group(1))
                        if cleaned and len(cleaned) > 2:
                            candidate = create_vendor_candidate(
                                value=cleaned,
                                pattern_name='context_subject',
                                match_span=(0, 0),
                                raw_text=context.subject,
                                line_position=0,
                                from_subject=True
                            )
                            candidates.append(candidate)

            # Strategy 2: Extract from email "From:" field if present in text
            for line_idx, line in enumerate(lines[:15]):
                if line.strip().lower().startswith('from:'):
                    match = re.search(r'from:\s*\*?\*?([^<\*]+?)[\*\s]*(?:<|$)', line, re.IGNORECASE)
                    if match:
                        vendor = self._clean_vendor_name(match.group(1))
                        if vendor and len(vendor) > 2:
                            vendor = re.sub(r'\b(receipts?|notifications?|noreply|no-reply)\b', '', vendor, flags=re.IGNORECASE).strip()
                            if vendor and len(vendor) > 2:
                                candidate = create_vendor_candidate(
                                    value=vendor,
                                    pattern_name='from_header_in_text',
                                    match_span=(0, len(line)),
                                    raw_text=line,
                                    line_position=line_idx,
                                    from_email_header=True
                                )
                                candidates.append(candidate)

            # Strategy 3: Look for "payable to" or "make cheques payable to" (high confidence)
            for line_idx, line in enumerate(lines[:50]):
                match = re.search(r'(?:make\s+)?(?:cheques?|checks?)\s+payable\s+to\s+([A-Z][A-Z\s]+?)(?:\s+and|$|\.|,)', line, re.IGNORECASE)
                if match:
                    vendor = self._clean_vendor_name(match.group(1))
                    if vendor and len(vendor) > 3:
                        candidate = create_vendor_candidate(
                            value=vendor,
                            pattern_name='payable_to',
                            match_span=match.span(1),
                            raw_text=line,
                            line_position=line_idx
                        )
                        candidates.append(candidate)

            # Strategy 4: Look for business-type keywords (medical, retail, services)
            # These indicate a business entity even without legal suffix
            business_keywords = ['Clinic', 'Medical', 'Eyeware', 'Eyecare', 'Optometry', 'Optical', 'Pharmacy', 'Restaurant', 'Cafe', 'Shop', 'Store', 'Hotel', 'Spa', 'Salon']
            for line_idx, line in enumerate(lines[:30]):
                for keyword in business_keywords:
                    if keyword in line:
                        # Extract business name around the keyword (up to 60 chars total)
                        # Pattern: Look for capital letters before keyword, then keyword, then rest of name
                        pattern = rf'([A-Z][a-zA-Z\s&-]{{0,40}}{keyword}(?:\s+&\s+[A-Z][a-zA-Z]+)?(?:\s*\([^)]+\))?)'
                        match = re.search(pattern, line)
                        if match:
                            vendor = self._clean_vendor_name(match.group(1))
                            if vendor and len(vendor) > 3:
                                # Remove person name patterns (FirstName LastNameBusinessName)
                                # If vendor starts with two capitalized words before business keyword, remove first two
                                words_before_keyword = vendor[:vendor.find(keyword)].strip().split()
                                if len(words_before_keyword) >= 2:
                                    # Check if first two words look like person name (both short, capitalized)
                                    if all(len(w) < 10 and w[0].isupper() for w in words_before_keyword[:2]):
                                        # Remove the first two words (likely person name)
                                        vendor = vendor[vendor.find(words_before_keyword[-1]):]

                                # Verify it's not part of patient/customer info
                                context_start = max(0, match.start() - 100)
                                context = line[context_start:match.start()].lower()
                                if 'bill to' not in context and 'patient' not in context:
                                    candidate = create_vendor_candidate(
                                        value=vendor,
                                        pattern_name='business_keyword',
                                        match_span=match.span(1),
                                        raw_text=line,
                                        line_position=line_idx
                                    )
                                    candidates.append(candidate)
                                    break  # Found vendor with this keyword, stop checking other keywords

            # Strategy 5: Look for company suffixes (structural scoring)
            # Skip payment processors - these are intermediaries, not the actual vendor
            payment_processors = ['paddle', 'stripe', 'paypal', 'square', 'shopify',
                                 'braintree', 'authorize', 'adyen', 'klarna', 'affirm',
                                 'payment', 'processor', 'merchant']

            for line_idx, line in enumerate(lines[:30]):
                # Skip lines containing payment processor names (check before extraction)
                if any(proc in line.lower() for proc in payment_processors):
                    continue

                match = re.search(r'([A-Z][a-zA-Z\s]{2,60}?(?:Incorporated|Inc|LLC|Ltd|Limited|Corp|Corporation|Labs))', line)
                if match:
                    vendor = self._clean_vendor_name(match.group(1))
                    if vendor and len(vendor) > 5:
                        candidate = create_vendor_candidate(
                            value=vendor,
                            pattern_name='company_suffix',
                            match_span=(match.start(), match.end()),
                            raw_text=match.group(0),
                            line_position=line_idx
                        )
                        candidates.append(candidate)

            # Strategy 4: Fallback to early lines with structural filtering
            # PHASE 1 ENHANCEMENT: Use combined_lines (multi-line aggregation)
            # Track if we're in a customer/bill-to section to avoid picking up customer name
            in_customer_section = False
            customer_section_end_line = -1

            # Map combined line indices back to original line indices for position tracking
            lines_to_use = combined_lines if len(combined_lines) < len(lines) else lines

            for line_idx, line in enumerate(lines_to_use[:20]):
                line = line.strip()

                # Detect customer/bill-to section start
                if re.search(r'\b(BILL\s+TO|CUSTOMER|SOLD\s+TO|SHIP\s+TO)\b', line, re.IGNORECASE):
                    in_customer_section = True
                    customer_section_end_line = line_idx + 5  # Skip next 5 lines after this marker
                    continue

                # Skip lines in customer section (customer name/address)
                if in_customer_section and line_idx <= customer_section_end_line:
                    continue

                # Reset customer section flag after we've passed it
                if line_idx > customer_section_end_line:
                    in_customer_section = False

                # Skip email forwarding headers
                skip_line = False
                for pattern in self.email_skip_patterns:
                    if pattern.match(line):
                        skip_line = True
                        break
                if skip_line:
                    continue

                # Remove leading garbage characters
                line = re.sub(r'^[^\w\s]+', '', line)

                if not line or len(line) < 3:
                    continue
                if re.match(r'^\d{1,2}[/-]\d{1,2}', line):
                    continue
                if re.match(r'^\d+\.?\d*$', line):
                    continue

                # Skip document type labels and generic headers (pattern-based)
                skip_patterns = [
                    r'^\s*receipt\s*$',
                    r'^\s*invoice\s*$',
                    r'^\s*bill\s*$',
                    r'^\s*order\s*$',
                    r'^\s*thanks?\s*$',
                    r'^\s*thank\s+you\s*$',
                    r'^\s*trip\s*$',
                    r'^\s*ride\s*$',
                    r'^\s*booking\s*$',
                    r'^\s*tax\s+invoice\s*$',
                    r'^\s*paid\s*$',
                    r'^\s*receipt\s+number\b',  # Skip "Receipt Number: 123"
                    r'^\s*invoice\s+(number|#)\b',
                    r'^\s*invoice\s+from\b',  # Skip "Invoice from"
                    r'^\s*booking\s+(confirmation|reference)\b',  # Skip "Booking Confirmation"
                    r'^\s*(order\s+)?confirmation\s*$',
                    r'^\s*itinerary\b',
                    r'^\s*(and|or|but|of|to|for|in|from|via)\s+',  # Skip lines starting with conjunctions/prepositions
                    r'\btariffsopens\b',  # Skip OCR artifact
                    # PHASE 1 LAUNCH: Skip customer/billing section headers
                    r'^\s*invoice\s+to\b',  # Skip "Invoice To: Customer Name"
                    r'^\s*bill\s+to\b',  # Skip "Bill To: Customer Name"
                    r'^\s*billed\s+to\b',  # Skip "Billed To: Customer Name"
                    r'^\s*sold\s+to\b',  # Skip "Sold To: Customer Name"
                    r'^\s*ship\s+to\b',  # Skip "Ship To: Customer Address"
                    r'^\s*customer\b',  # Skip "Customer: Name" or "Customer Details"
                ]
                skip_line = False
                for pattern in skip_patterns:
                    if re.match(pattern, line, re.IGNORECASE):
                        skip_line = True
                        break
                if skip_line:
                    continue

                # Skip lines that look like table headers (multiple capitalized words or common headers)
                # e.g., "BALANCE DUE DATE INVOICE NO", "Date Description Practitioner"
                if len(line.split()) >= 3 and line.isupper():
                    continue

                # Skip common invoice table headers (case-insensitive)
                lower_line = line.lower()
                table_header_patterns = [
                    'code description price',
                    'item description quantity',
                    'description qty price',
                    'date description practitioner'
                ]
                if any(pattern in lower_line for pattern in table_header_patterns):
                    continue

                # Skip lines that look like addresses (postal codes, state/province codes)
                # Canadian: A1A 1A1
                if re.search(r'\b[A-Z]\d[A-Z]\s*\d[A-Z]\d\b', line, re.IGNORECASE):
                    continue
                # UK: EC1V 8BT
                if re.search(r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}\b', line):
                    continue
                # US ZIP: 12345 or 12345-6789
                if re.search(r'\b\d{5}(?:-\d{4})?\b', line):
                    continue

                # Skip lines that look like dates
                if re.search(r'\d{1,2}(?:st|nd|rd|th)\s+[A-Za-z]{3,9}\s+\d{4}', line):
                    continue
                if re.search(r'[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}', line):
                    continue

                # PHASE 1 LAUNCH: Apply vendor-specific OCR normalization
                # Extra aggressive for early lines (0-10) where vendor names appear
                # Handles "I N V O I C" → "Invoice", "H S T" → "Hst", "i n v o i c e" → "invoice"
                is_early_line = line_idx < 10
                normalized_line = self._normalize_vendor_ocr(line, is_early_line=is_early_line)
                vendor = self._clean_vendor_name(normalized_line)
                if vendor and len(vendor) > 2:
                    # Person name filtering is handled by scoring function (_looks_like_person_name)
                    # which has more sophisticated checks for business indicators

                    # Skip payment processors (intermediaries, not actual vendors)
                    payment_processors = ['paddle', 'stripe', 'paypal', 'square', 'shopify',
                                         'braintree', 'authorize', 'adyen', 'klarna', 'affirm']
                    if any(proc in vendor.lower() for proc in payment_processors):
                        continue

                    # Skip amount-like patterns (e.g., "Ca699" from "CA$6.99")
                    # Match: 2-3 letters followed by digits, or starts with currency code
                    if re.match(r'^[A-Za-z]{2,3}\d+$', vendor) or re.match(r'^(USD|CAD|EUR|GBP|AUD)\s*\d', vendor, re.IGNORECASE):
                        continue

                    generic_phrases = ['your order', 'your trip', 'your receipt', 'your booking']
                    if vendor.lower() not in generic_phrases:
                        candidate = create_vendor_candidate(
                            value=vendor,
                            pattern_name='early_line',
                            match_span=(0, len(line)),
                            raw_text=line,
                            line_position=line_idx
                        )
                        candidates.append(candidate)

            # Select best candidate using structural scoring with forwarding awareness
            result = select_best_vendor(
                candidates,
                is_forwarded=is_forwarded,
                context=context,
                return_score=True
            )

            if result:
                best, score = result  # Unpack (candidate, score) tuple

                # Record provenance in debug
                if _debug is not None:
                    _debug['patterns_matched']['vendor'] = best.pattern_name
                    # Use real score from scoring function (not hardcoded)
                    _debug['confidence_per_field']['vendor'] = round(score, 2)

                    # Capture top 3 candidates for review UI
                    top_3 = select_top_vendors(
                        candidates,
                        is_forwarded=is_forwarded,
                        context=context,
                        top_n=3
                    )
                    _debug['vendor_candidates'] = [
                        {
                            'value': c.value,
                            'score': round(score, 2),
                            'pattern': c.pattern_name
                        }
                        for c, score in top_3
                    ]

                return best.value

            return None

        except (re.error, AttributeError, IndexError):
            logger.warning("Error extracting vendor", exc_info=True)
            return None

    def _clean_vendor_name(self, name: str, preserve_case: bool = False) -> str:
        """
        Clean and format vendor name.

        Args:
            name: Raw vendor name
            preserve_case: If True, don't apply title case (preserve original formatting)

        Returns:
            Cleaned vendor name
        """
        # Remove special characters (preserve &, ', -)
        name = re.sub(r'[^A-Za-z0-9\s&\'-]', '', name)

        # Apply title case unless preserving original
        if not preserve_case:
            name = name.title()

        # Normalize whitespace
        name = ' '.join(name.split())

        # Limit to 6 words (prevent extracting too much text)
        words = name.split()
        if len(words) > 6:
            name = ' '.join(words[:6])

        return name.strip()

    def extract_amount(self, text: str, context: Optional[ParseContext] = None, _debug=None) -> Optional[Decimal]:
        """
        Extract total amount from receipt using candidate-based scoring.

        Args:
            text: Receipt text
            context: Optional parse context with email metadata

        Returns:
            Amount as Decimal or None
        """
        try:
            candidates: List[AmountCandidate] = []

            # Generate candidates from all patterns
            for spec in self.amount_patterns:
                matches = list(spec.compiled.finditer(text))

                for match in matches:
                    # Extract amount string from capture group
                    amount_str = match.group(1) if match.groups() else match.group(0)
                    raw_text = match.group(0)

                    # Parse amount using shared money utility
                    # Use context hint if available
                    format_hint = None
                    if context and context.user_locale:
                        format_hint = MoneyFormat.EUROPEAN if context.user_locale == 'EU' else MoneyFormat.US

                    amount = parse_money(amount_str, format_hint=format_hint)

                    if amount is None or amount <= 0:
                        continue

                    # Skip unreasonably large amounts for low-priority patterns
                    if amount > 10000 and spec.priority > 2:
                        continue

                    # Create candidate with context analysis
                    candidate = create_amount_candidate(
                        value=amount,
                        pattern_name=spec.name,
                        match_span=(match.start(), match.end()),
                        raw_text=raw_text,
                        priority=spec.priority,
                        text=text
                    )

                    candidates.append(candidate)

            # Select best candidate using scoring
            result = select_best_amount(candidates, text, return_score=True)

            if result:
                best, score = result  # Unpack (candidate, score) tuple

                # Record provenance in debug metadata
                if _debug is not None:
                    _debug['patterns_matched']['amount'] = best.pattern_name
                    # Use real score from scoring function (not 1.0/priority)
                    _debug['confidence_per_field']['amount'] = round(score, 2)
                    _debug['amount_match_span'] = best.match_span

                    # Capture top 3 candidates for review UI
                    top_3 = select_top_amounts(candidates, text, top_n=3)
                    _debug['amount_candidates'] = [
                        {
                            'value': str(c.value),
                            'score': round(score, 2),
                            'pattern': c.pattern_name
                        }
                        for c, score in top_3
                    ]

                return best.value

            return None

        except (re.error, AttributeError):
            logger.warning("Error extracting amount", exc_info=True)
            return None

    def _detect_currency_in_text(self, text: str) -> Optional[str]:
        """
        Detect an explicit currency indicator in a text snippet.

        Returns a 3-letter currency code, or None. Intentionally does NOT
        infer USD from a bare '$' — that fallback lives in extract_currency
        so it doesn't override the Canadian-indicator heuristic.
        """
        text_upper = text.upper()
        for code in ('CAD', 'USD', 'EUR', 'GBP', 'AUD', 'NZD', 'JPY'):
            if code in text_upper:
                return code
        if 'C$' in text or 'C $' in text:
            return 'CAD'
        if '€' in text:
            return 'EUR'
        if '£' in text:
            return 'GBP'
        if '¥' in text:
            return 'JPY'
        return None

    def extract_currency(self, text: str, context: Optional[ParseContext] = None, _debug=None) -> Optional[str]:
        """
        Extract currency from receipt using candidate-based scoring.

        BREAKING CHANGE: Returns None when evidence is weak, instead of defaulting to USD.
        Upstream services should handle defaulting with provenance tracking.

        Args:
            text: Receipt text
            context: Optional parse context with email metadata

        Returns:
            Currency code (USD, EUR, etc.) or None if evidence is weak
        """
        try:
            candidates: List[CurrencyCandidate] = []
            text_upper = text.upper()

            # Strategy 1: Explicit currency codes near amount
            if _debug is not None and 'amount_match_span' in _debug:
                start, end = _debug['amount_match_span']
                vicinity = text[max(0, start - 200):min(len(text), end + 200)]
                vicinity_upper = vicinity.upper()

                for code in ['CAD', 'USD', 'EUR', 'GBP', 'AUD', 'NZD', 'JPY']:
                    if code in vicinity_upper:
                        candidate = create_currency_candidate(
                            value=code,
                            pattern_name='explicit_near_amount',
                            match_span=(start, end),
                            raw_text=code,
                            priority=1,
                            is_explicit=True,
                            text=text
                        )
                        candidates.append(candidate)

            # Strategy 2: Currency codes near keywords (TOTAL, AMOUNT)
            for keyword in ['TOTAL', 'AMOUNT', 'CHARGED', 'PAID']:
                keyword_positions = [i for i in range(len(text_upper)) if text_upper.startswith(keyword, i)]

                for pos in keyword_positions:
                    keyword_context = text_upper[pos:pos+100]

                    for code in ['CAD', 'USD', 'EUR', 'GBP', 'AUD', 'NZD', 'JPY']:
                        if code in keyword_context:
                            candidate = create_currency_candidate(
                                value=code,
                                pattern_name='explicit_near_keyword',
                                match_span=(pos, pos + len(keyword)),
                                raw_text=code,
                                priority=2,
                                is_explicit=True,
                                text=text
                            )
                            candidates.append(candidate)

            # Strategy 3: CAD heuristic (GST/PST/CANADA indicators + Canadian provinces)
            canadian_indicators = ['CANADA', 'GST', 'PST', 'HST']
            canadian_provinces = [' AB ', ' BC ', ' MB ', ' NB ', ' NL ', ' NS ', ' ON ', ' PE ', ' QC ', ' SK ']  # Space-padded to avoid false matches

            has_canadian_indicator = any(ind in text_upper for ind in canadian_indicators)
            has_province_code = any(prov in text_upper for prov in canadian_provinces)

            if has_canadian_indicator or has_province_code:
                # Check if USD is explicitly mentioned near keywords
                has_usd_override = False
                for keyword in ['TOTAL', 'AMOUNT']:
                    keyword_positions = [i for i in range(len(text_upper)) if text_upper.startswith(keyword, i)]
                    for pos in keyword_positions:
                        if 'USD' in text_upper[pos:pos+100]:
                            has_usd_override = True
                            break

                if not has_usd_override:
                    indicator_source = 'province_code' if has_province_code else 'GST/PST/CANADA'
                    candidate = create_currency_candidate(
                        value='CAD',
                        pattern_name='cad_heuristic',
                        match_span=(0, 0),
                        raw_text=indicator_source,
                        priority=3,
                        is_explicit=False,
                        text=text
                    )
                    candidates.append(candidate)

            # Strategy 4: C$ prefix
            if 'C$' in text or 'C $' in text:
                candidate = create_currency_candidate(
                    value='CAD',
                    pattern_name='c_dollar_symbol',
                    match_span=(0, 0),
                    raw_text='C$',
                    priority=2,
                    is_explicit=False,
                    text=text
                )
                candidates.append(candidate)

            # Strategy 5: Currency symbols
            symbol_map = {
                '€': 'EUR',
                '£': 'GBP',
                '¥': 'JPY',
            }

            for symbol, code in symbol_map.items():
                if symbol in text:
                    candidate = create_currency_candidate(
                        value=code,
                        pattern_name='currency_symbol',
                        match_span=(0, 0),
                        raw_text=symbol,
                        priority=4,
                        is_explicit=False,
                        text=text
                    )
                    candidates.append(candidate)

            # Strategy 6: Generic $ symbol (weakest evidence)
            if '$' in text and not any(c.value in ['CAD', 'USD'] for c in candidates):
                # Use context hint if available
                if context and context.user_currency:
                    code = context.user_currency
                else:
                    # Weak evidence - don't add candidate
                    # Return None to let upstream handle defaulting
                    pass

            # Select best candidate
            result = select_best_currency(candidates, return_score=True)

            if result:
                best, score = result  # Unpack (candidate, score) tuple

                if _debug is not None:
                    _debug['patterns_matched']['currency'] = best.pattern_name
                    # Use real score from scoring function (not hardcoded 0.9/0.6)
                    _debug['confidence_per_field']['currency'] = round(score, 2)

                    # Capture top 3 candidates for review UI
                    top_3 = select_top_currencies(candidates, top_n=3)
                    _debug['currency_candidates'] = [
                        {
                            'value': c.value,
                            'score': round(score, 2),
                            'pattern': c.pattern_name
                        }
                        for c, score in top_3
                    ]

                return best.value

            # No strong evidence found - return None
            # Upstream services will handle defaulting with provenance
            if _debug is not None:
                _debug['warnings'].append('No strong currency evidence found')

            return None

        except (re.error, AttributeError):
            logger.warning("Error extracting currency", exc_info=True)
            return None

    def _detect_date_locale(self, text: str) -> str:
        """
        Detect date locale from receipt context to disambiguate MM/DD vs DD/MM.

        Returns:
            'MM/DD' for North American, 'DD/MM' for European
        """
        text_upper = text.upper()
        if any(t in text_upper for t in ('GST', 'PST', 'HST', 'CANADA')):
            return 'MM/DD'  # North American
        if '£' in text or 'VAT' in text_upper:
            return 'DD/MM'  # European
        return 'MM/DD'  # Default to North American

    def _parse_numeric_date_with_locale(self, date_str: str, locale: str) -> Optional[str]:
        """Parse a numeric date string using locale to resolve MM/DD vs DD/MM ambiguity.

        Tries locale-preferred format first, then falls back to opposite locale if primary fails.
        This handles cases where locale detection is wrong or dates are ambiguous.
        """
        sep = '/' if '/' in date_str else '-'
        parts = date_str.split(sep)
        if len(parts) != 3:
            return None

        # Set primary and fallback formats based on locale
        if locale == 'DD/MM':
            primary_formats = [f'%d{sep}%m{sep}%Y', f'%d{sep}%m{sep}%y']
            fallback_formats = [f'%m{sep}%d{sep}%Y', f'%m{sep}%d{sep}%y']
        else:
            primary_formats = [f'%m{sep}%d{sep}%Y', f'%m{sep}%d{sep}%y']
            fallback_formats = [f'%d{sep}%m{sep}%Y', f'%d{sep}%m{sep}%y']

        # Try primary formats first (locale-preferred)
        for fmt in primary_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        # Try fallback formats (opposite locale) if primary fails
        for fmt in fallback_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        return None

    def extract_date(self, text: str, context: Optional[ParseContext] = None, _debug=None) -> Optional[str]:
        """
        Extract receipt date using candidate-based scoring.

        Args:
            text: Receipt text
            context: Optional parse context with email metadata

        Returns:
            Date in YYYY-MM-DD format or None
        """
        try:
            candidates: List[DateCandidate] = []

            # Determine locale for ambiguous date parsing
            # Use context if available, otherwise detect from text
            if context and context.user_locale:
                locale = 'DD/MM' if context.user_locale == 'EU' else 'MM/DD'
            else:
                locale = self._detect_date_locale(text)

            # Split text into lines for line position tracking
            lines = text.split('\n')
            line_offsets = []
            offset = 0
            for line in lines:
                line_offsets.append(offset)
                offset += len(line) + 1  # +1 for newline

            # Generate candidates from all date patterns
            for spec in self.date_patterns:
                for match in spec.compiled.finditer(text):
                    date_str = match.group(1)

                    # Determine if this pattern is ambiguous
                    is_ambiguous = spec.name == 'numeric_date_ambiguous'

                    # Parse date based on pattern type
                    if is_ambiguous:
                        parsed_date = self._parse_numeric_date_with_locale(date_str, locale)
                    else:
                        parsed_date = self._parse_date_string(date_str)

                    if not parsed_date:
                        continue

                    # Find line position
                    match_start = match.start()
                    line_position = 0
                    for idx, line_offset in enumerate(line_offsets):
                        if match_start >= line_offset:
                            line_position = idx
                        else:
                            break

                    # Create candidate
                    candidate = create_date_candidate(
                        value=parsed_date,
                        pattern_name=spec.name,
                        match_span=(match.start(), match.end()),
                        raw_text=match.group(0),
                        priority=spec.priority or 100,
                        line_position=line_position,
                        text=text,
                        is_ambiguous=is_ambiguous,
                        detected_locale=locale if is_ambiguous else None
                    )
                    candidates.append(candidate)

            # Select best candidate using scoring
            result = select_best_date(candidates, return_score=True)

            if result:
                best, score = result  # Unpack (candidate, score) tuple

                # Record provenance in debug
                if _debug is not None:
                    _debug['patterns_matched']['date'] = best.pattern_name
                    # Use real score from scoring function (not hardcoded 0.7/0.9)
                    _debug['confidence_per_field']['date'] = round(score, 2)

                    # Capture top 3 candidates for review UI
                    top_3 = select_top_dates(candidates, top_n=3)
                    _debug['date_candidates'] = [
                        {
                            'value': c.value,
                            'score': round(score, 2),
                            'pattern': c.pattern_name
                        }
                        for c, score in top_3
                    ]

                return best.value

            return None

        except (re.error, ValueError, AttributeError):
            logger.warning("Error extracting date", exc_info=True)
            return None

    def _parse_date_string(self, date_str: str) -> Optional[str]:
        """
        Parse various date formats into YYYY-MM-DD.

        Args:
            date_str: Date string in various formats

        Returns:
            Date in YYYY-MM-DD format or None
        """
        if re.search(r'\d+(?:st|nd|rd|th)', date_str):
            date_str = re.sub(r'(\d+)(?:st|nd|rd|th)', r'\1', date_str)

        formats = [
            '%m/%d/%Y', '%m-%d-%Y',
            '%d/%m/%Y', '%d-%m-%Y',
            '%Y-%m-%d',
            '%m/%d/%y', '%m-%d-%y',
            '%d/%m/%y', '%d-%m-%y',
            '%B %d, %Y', '%b %d, %Y',
            '%B %d %Y', '%b %d %Y',
            '%d %B %Y', '%d %b %Y',
            '%B %d/%Y', '%b %d/%Y',
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        return None

    def extract_tax(self, text: str, _debug=None) -> Optional[Decimal]:
        """
        Extract tax amount from receipt, summing multiple tax lines if present.
        (e.g., Sephora has both GST and HST that should be summed)

        Deduplicates by the character span of the captured amount group so that
        the same text position is never counted twice even if multiple patterns
        match it.

        Args:
            text: Receipt text

        Returns:
            Total tax amount as Decimal or None
        """
        try:
            seen_spans: set = set()  # (start, end) of each captured amount group
            taxes = []

            for spec in self.tax_patterns:
                for match in spec.compiled.finditer(text):
                    amount_span = match.span(match.lastindex or 1)
                    if amount_span in seen_spans:
                        continue
                    seen_spans.add(amount_span)

                    amount_group = match.group(match.lastindex or 1)
                    tax_str = amount_group.replace(',', '').replace('$', '').strip()
                    try:
                        tax = Decimal(tax_str)
                        if tax > 0:
                            taxes.append(tax)
                    except (InvalidOperation, ValueError):
                        continue

            if taxes:
                total_tax = sum(taxes)
                logger.debug("Found %d tax line(s), total: %s", len(taxes), total_tax)
                if _debug is not None:
                    _debug['patterns_matched']['tax'] = f'{len(taxes)}_lines'
                    _debug['confidence_per_field']['tax'] = 0.9
                return total_tax
            return None

        except (re.error, AttributeError, InvalidOperation):
            logger.warning("Error extracting tax", exc_info=True)
            return None

    def _validate_amount_consistency(
        self,
        amount: Optional[Decimal],
        tax: Optional[Decimal],
        text: str,
        _debug: Optional[Dict] = None
    ) -> bool:
        """
        Sanity check: If subtotal and tax exist, verify subtotal + tax ≈ total.

        This helps detect extraction errors where we pick up the wrong amount.

        Args:
            amount: Extracted total amount
            tax: Extracted tax amount
            text: Full receipt text
            _debug: Optional debug metadata dictionary

        Returns:
            True if consistent or check cannot be performed (not enough data)
            False if inconsistent (likely extraction error)
        """
        if not amount or not tax:
            return True  # Can't validate without both

        # Try to find subtotal in text
        subtotal_patterns = [
            r'(?:sub\s*total|subtotal)[\s:]*\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
            r'(?:before\s*tax)[\s:]*\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
        ]

        subtotal = None
        for pattern in subtotal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    subtotal_str = match.group(1).replace(',', '')
                    subtotal = Decimal(subtotal_str)
                    break
                except (InvalidOperation, ValueError):
                    continue

        if not subtotal:
            return True  # No subtotal found, can't validate

        # Check: subtotal + tax ≈ total (within 1% tolerance or $0.02)
        calculated_total = subtotal + tax
        tolerance = max(amount * Decimal('0.01'), Decimal('0.02'))
        is_consistent = abs(calculated_total - amount) <= tolerance

        # Record validation in debug metadata
        if _debug is not None:
            _debug['amount_validation'] = {
                'subtotal': str(subtotal),
                'tax': str(tax),
                'calculated_total': str(calculated_total),
                'extracted_total': str(amount),
                'tolerance': str(tolerance),
                'is_consistent': is_consistent
            }

            if not is_consistent:
                _debug['warnings'].append(
                    f'Amount inconsistency: subtotal ({subtotal}) + tax ({tax}) = {calculated_total} != total ({amount})'
                )

        return is_consistent

    def _calculate_confidence(self, parsed_data: Dict[str, Any]) -> float:
        """
        Calculate confidence score using per-field evidence from extraction.

        Uses confidence_per_field scores from debug metadata, weighted by field importance.

        Args:
            parsed_data: Dictionary of parsed fields including debug metadata

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Get per-field confidence scores from debug metadata
        confidence_per_field = parsed_data.get('debug', {}).get('confidence_per_field', {})

        # Field weights (sum to 1.0)
        weights = {
            'amount': 0.35,    # Most critical field
            'vendor': 0.25,    # Important for categorization
            'date': 0.25,      # Important for tracking
            'currency': 0.05,  # Less critical, often inferred
            'tax': 0.10,       # Nice to have but not critical
        }

        score = 0.0

        # Add weighted scores for fields that were extracted
        for field, weight in weights.items():
            if parsed_data.get(field) is not None:
                # Use per-field confidence if available, otherwise use presence bonus
                field_confidence = confidence_per_field.get(field, 0.5)
                score += weight * field_confidence
            # If field is None and expected, no score

        # Penalty for warnings (e.g., weak currency evidence)
        warnings = parsed_data.get('debug', {}).get('warnings', [])
        if warnings:
            penalty = min(0.1, len(warnings) * 0.05)
            score -= penalty

        # Ensure score is in valid range
        score = max(0.0, min(1.0, score))

        return round(score, 2)
