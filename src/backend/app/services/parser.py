"""
Receipt parser service for extracting structured data from OCR text.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal, InvalidOperation

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


class ReceiptParser:
    """Service for parsing receipt text and extracting structured data."""

    # Known payment processors (value is the normalized name)
    PAYMENT_PROCESSORS = {
        'paddle.com market ltd': 'paddle',
        'paddle.com': 'paddle',
        'paddle': 'paddle',
        'market ltd': 'paddle',  # GeoGuessr case
        'stripe': 'stripe',
        'square': 'square',
        'paypal': 'paypal',
    }

    def __init__(self):
        """Initialize parser with regex patterns."""
        self._init_patterns()

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
            'reference', 'miles', 'rewards'
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
                pattern=r'(?:[A-Z\s]+\s+)?(?:gst|hst|pst)(?:/[A-Z]+)?\s*\([^\)]+\):\s*\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                example='CANADA GST/TPS (5%): $2.62',
                notes='Sephora fix - country-prefix tax',
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

        # Known vendor patterns (pre-compiled)
        self.known_vendor_patterns = [
            (re.compile(r'\buber\b', re.IGNORECASE), 'Uber'),
            (re.compile(r'\bamazon\b', re.IGNORECASE), 'Amazon'),
            (re.compile(r'\bairbnb\b', re.IGNORECASE), 'Airbnb'),
            (re.compile(r'\blyft\b', re.IGNORECASE), 'Lyft'),
            (re.compile(r'\bdoordash\b', re.IGNORECASE), 'DoorDash'),
            (re.compile(r'\bgrubhub\b', re.IGNORECASE), 'Grubhub'),
            (re.compile(r'\bskip\s*the\s*dishes\b', re.IGNORECASE), 'Skip The Dishes'),
            (re.compile(r'\bair\s*canada\b', re.IGNORECASE), 'Air Canada'),
            (re.compile(r'\bwestjet\b', re.IGNORECASE), 'WestJet'),
            (re.compile(r'\bapple\b', re.IGNORECASE), 'Apple'),
            (re.compile(r'\bwalmart\b', re.IGNORECASE), 'Walmart'),
            (re.compile(r'\btarget\b', re.IGNORECASE), 'Target'),
            (re.compile(r'\bstarbucks\b', re.IGNORECASE), 'Starbucks'),
            (re.compile(r'\bmcdonald', re.IGNORECASE), "McDonald's"),
            (re.compile(r'\bpsa\s+submission\b', re.IGNORECASE), 'PSA Canada'),
            (re.compile(r'\bpsacanada@', re.IGNORECASE), 'PSA Canada'),
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

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse receipt text and extract all available fields.

        Args:
            text: OCR-extracted text from receipt

        Returns:
            Dictionary with parsed fields
        """
        debug = {'patterns_matched': {}, 'confidence_per_field': {}, 'warnings': []}
        result = {
            'vendor': self.extract_vendor(text, _debug=debug),
            'amount': self.extract_amount(text, _debug=debug),
            'currency': self.extract_currency(text, _debug=debug),
            'date': self.extract_date(text, _debug=debug),
            'tax': self.extract_tax(text, _debug=debug),
            'confidence': 0.0,
            'debug': debug,
        }

        result['confidence'] = self._calculate_confidence(result)

        return result

    def _normalize_ocr_spaces(self, text: str) -> str:
        """
        Remove OCR-induced extra spaces between characters.
        Handles cases like "L o v a b l e" → "Lovable"
        """
        if re.search(r'[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]', text):
            pattern = r'\b([A-Za-z])\s+(?=[A-Za-z](\s+|$))'
            while True:
                new_text = re.sub(pattern, r'\1', text)
                if new_text == text:
                    break
                text = new_text
        return text

    def extract_vendor(self, text: str, _debug=None) -> Optional[str]:
        """
        Extract vendor/merchant name from receipt text.
        Works for both physical receipts and email receipts.

        Args:
            text: Receipt text

        Returns:
            Vendor name or None
        """
        try:
            # Normalize OCR spacing for header lines only
            lines = text.split('\n')
            header_lines = lines[:15]
            normalized_header = '\n'.join(self._normalize_ocr_spaces(line) for line in header_lines)
            text = normalized_header + ('\n' + '\n'.join(lines[15:]) if len(lines) > 15 else '')
            lines = text.split('\n')

            # First, try to extract from email "From:" field if present
            for line in lines[:15]:
                if line.strip().lower().startswith('from:'):
                    match = re.search(r'from:\s*\*?\*?([^<\*]+?)[\*\s]*(?:<|$)', line, re.IGNORECASE)
                    if match:
                        vendor = self._clean_vendor_name(match.group(1))
                        if vendor and len(vendor) > 2:
                            vendor = re.sub(r'\b(receipts?|notifications?|noreply|no-reply)\b', '', vendor, flags=re.IGNORECASE).strip()
                            if vendor and len(vendor) > 2:
                                if _debug is not None:
                                    _debug['patterns_matched']['vendor'] = 'from_header'
                                    _debug['confidence_per_field']['vendor'] = 0.9
                                return vendor

            # Check for known vendors in the entire text
            for compiled, name in self.known_vendor_patterns:
                if compiled.search(text):
                    if _debug is not None:
                        _debug['patterns_matched']['vendor'] = f'known_vendor:{name}'
                        _debug['confidence_per_field']['vendor'] = 0.95
                    return name

            # Prioritize lines with company indicators (Inc, LLC, etc.)
            for line in lines[:30]:
                match = re.search(r'([A-Z][a-zA-Z\s]{2,60}?(?:Incorporated|Inc|LLC|Ltd|Limited|Corp|Corporation|Labs))', line)
                if match:
                    vendor = self._clean_vendor_name(match.group(1))
                    if vendor and len(vendor) > 5:
                        vendor_lower = vendor.lower()
                        if vendor_lower in self.PAYMENT_PROCESSORS:
                            real_merchant = self._extract_real_merchant(text)
                            if real_merchant:
                                logger.debug("Payment processor detected: %s -> %s", vendor, real_merchant)
                                if _debug is not None:
                                    _debug['patterns_matched']['vendor'] = 'payment_processor_real_merchant'
                                    _debug['confidence_per_field']['vendor'] = 0.8
                                return real_merchant
                        if _debug is not None:
                            _debug['patterns_matched']['vendor'] = 'company_indicator'
                            _debug['confidence_per_field']['vendor'] = 0.85
                        return vendor

            # Fallback: Try to find vendor in first few non-header lines
            for line in lines[:20]:
                line = line.strip()

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

                skip_words = ['receipt', 'invoice', 'bill', 'order', 'thanks', 'thank you', 'trip', 'ride', 'booking']
                if line.lower() in skip_words:
                    continue

                vendor = self._clean_vendor_name(line)
                if vendor and len(vendor) > 2:
                    generic_phrases = ['your order', 'your trip', 'your receipt', 'your booking']
                    if vendor.lower() not in generic_phrases:
                        vendor_lower = vendor.lower()
                        if vendor_lower in self.PAYMENT_PROCESSORS:
                            real_merchant = self._extract_real_merchant(text)
                            if real_merchant:
                                logger.debug("Payment processor detected: %s -> %s", vendor, real_merchant)
                                if _debug is not None:
                                    _debug['patterns_matched']['vendor'] = 'payment_processor_real_merchant'
                                    _debug['confidence_per_field']['vendor'] = 0.8
                                return real_merchant
                        if _debug is not None:
                            _debug['patterns_matched']['vendor'] = 'fallback_first_line'
                            _debug['confidence_per_field']['vendor'] = 0.5
                        return vendor

            return None

        except (re.error, AttributeError, IndexError):
            logger.warning("Error extracting vendor", exc_info=True)
            return None

    def _extract_real_merchant(self, text: str) -> Optional[str]:
        """
        Extract actual merchant when vendor is a payment processor.

        Args:
            text: Receipt text

        Returns:
            Real merchant name or None
        """
        statement_match = re.search(
            r'statement\s+as:\s*\n?\s*([A-Z][A-Z0-9\s\.\*]+?)(?:\n|$)',
            text,
            re.IGNORECASE | re.MULTILINE
        )
        if statement_match:
            statement = statement_match.group(1).strip()
            parts = re.split(r'[\*\s]{2,}', statement)
            for part in reversed(parts):
                if len(part) > 2 and part.upper() not in ['NET', 'COM', 'INC', 'PADDLE']:
                    return part.strip().title()

        product_match = re.search(
            r'(?:Product|Description|Item)\s*\n\s*([A-Z][a-zA-Z\s]{2,30}?)(?:\s+(?:Unlimited|Subscription|Pro|Monthly|Annual|Premium)|$)',
            text,
            re.MULTILINE
        )
        if product_match:
            product_name = product_match.group(1).strip()
            product_name = re.sub(r'\s+(Unlimited|Subscription|Pro|Monthly|Annual|Premium)$', '', product_name, flags=re.IGNORECASE)
            if len(product_name) > 2:
                return product_name

        return None

    def _clean_vendor_name(self, name: str) -> str:
        """Clean and format vendor name."""
        name = re.sub(r'[^A-Za-z0-9\s&\'-]', '', name)
        name = name.title()
        name = ' '.join(name.split())
        words = name.split()
        if len(words) > 6:
            name = ' '.join(words[:6])
        return name.strip()

    def extract_amount(self, text: str, _debug=None) -> Optional[Decimal]:
        """
        Extract total amount from receipt using priority-based matching.

        Args:
            text: Receipt text

        Returns:
            Amount as Decimal or None
        """
        try:
            for spec in self.amount_patterns:
                matches = list(spec.compiled.finditer(text))

                for match in matches:
                    context_start = max(0, match.start() - 50)
                    context_end = min(len(text), match.end() + 50)
                    context_window = text[context_start:context_end].lower()

                    if any(bl in context_window for bl in self.blacklist_contexts):
                        continue

                    preceding_text = text[max(0, match.start() - 150):match.start()].lower()
                    following_text = text[match.end():min(len(text), match.end() + 30)].lower()

                    if 'subtotal' in preceding_text or 'subtotal' in following_text:
                        if 'grand' not in preceding_text and 'grand' not in following_text:
                            match_text = match.group(0).lower()
                            if any(keyword in match_text for keyword in ['total', 'amount', 'paid', 'sum']):
                                pass
                            elif 'total' in text[max(0, match.start() - 50):match.start()].lower() and \
                                 'subtotal' not in text[max(0, match.start() - 50):match.start()].lower():
                                pass
                            else:
                                continue

                    amount_str = match.group(1) if match.groups() else match.group(0)
                    amount_str = amount_str.replace(',', '').replace('$', '').replace('€', '').replace('£', '').replace('¥', '').strip()

                    try:
                        amount = Decimal(amount_str)

                        if amount <= 0:
                            continue

                        if amount > 10000 and spec.priority > 2:
                            continue

                        if _debug is not None:
                            _debug['patterns_matched']['amount'] = spec.name
                            _debug['confidence_per_field']['amount'] = 1.0 / spec.priority
                            _debug['amount_match_span'] = (match.start(), match.end())

                        return amount

                    except (InvalidOperation, ValueError):
                        continue

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

    def extract_currency(self, text: str, _debug=None) -> str:
        """
        Extract currency from receipt with context awareness.

        First looks near the matched amount span (most specific evidence),
        then falls back to document-level heuristics.

        Args:
            text: Receipt text

        Returns:
            Currency code (USD, EUR, etc.) or 'USD' as default
        """
        try:
            # Strategy 0: Look near the amount match span — currency of the
            # specific transaction amount, not just any currency in the doc.
            if _debug is not None and 'amount_match_span' in _debug:
                start, end = _debug['amount_match_span']
                vicinity = text[max(0, start - 200):min(len(text), end + 200)]
                currency = self._detect_currency_in_text(vicinity)
                if currency:
                    return currency

            text_upper = text.upper()

            # Strategy 1: Check for Canadian indicators first
            # Many Canadian receipts don't say CAD explicitly near the total.
            if 'CANADA' in text_upper or 'GST' in text_upper or 'PST' in text_upper:
                for keyword in ['TOTAL', 'AMOUNT', 'CHARGED', 'PAID']:
                    keyword_positions = [i for i in range(len(text_upper)) if text_upper.startswith(keyword, i)]
                    for pos in keyword_positions:
                        context = text_upper[pos:pos+100]
                        if 'USD' in context:
                            return 'USD'

                return 'CAD'

            # Strategy 2: Look for currency near "TOTAL" or "AMOUNT" keywords
            for keyword in ['TOTAL', 'AMOUNT', 'CHARGED', 'PAID']:
                keyword_positions = [i for i in range(len(text_upper)) if text_upper.startswith(keyword, i)]

                for pos in keyword_positions:
                    context = text_upper[pos:pos+100]

                    for code in ['CAD', 'USD', 'EUR', 'GBP', 'AUD', 'NZD', 'JPY']:
                        if code in context:
                            return code

                    if 'C$' in text[pos:pos+100]:
                        return 'CAD'

                    if '€' in text[pos:pos+100]:
                        return 'EUR'
                    if '£' in text[pos:pos+100]:
                        return 'GBP'
                    if '¥' in text[pos:pos+100]:
                        return 'JPY'

            # Strategy 3: Count currency occurrences
            currency_counts = {}
            for code in ['CAD', 'USD', 'EUR', 'GBP', 'AUD', 'NZD', 'JPY']:
                count = text_upper.count(code)
                if count > 0:
                    currency_counts[code] = count

            if currency_counts:
                return max(currency_counts, key=currency_counts.get)

            # Strategy 4: Check for C$ prefix anywhere
            if 'C$' in text or 'C $' in text:
                return 'CAD'

            # Strategy 5: Check for symbols
            if '€' in text:
                return 'EUR'
            if '£' in text:
                return 'GBP'
            if '¥' in text:
                return 'JPY'

            # Strategy 6: If we see $ but no currency code, default to USD
            if '$' in text:
                return 'USD'

            return 'USD'

        except (re.error, AttributeError):
            logger.warning("Error extracting currency", exc_info=True)
            return 'USD'

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
        """Parse a numeric date string using locale to resolve MM/DD vs DD/MM ambiguity."""
        sep = '/' if '/' in date_str else '-'
        parts = date_str.split(sep)
        if len(parts) != 3:
            return None

        if locale == 'DD/MM':
            formats = [f'%d{sep}%m{sep}%Y', f'%d{sep}%m{sep}%y']
        else:
            formats = [f'%m{sep}%d{sep}%Y', f'%m{sep}%d{sep}%y']

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        return None

    def extract_date(self, text: str, _debug=None) -> Optional[str]:
        """
        Extract receipt date.

        Args:
            text: Receipt text

        Returns:
            Date in YYYY-MM-DD format or None
        """
        try:
            locale = self._detect_date_locale(text)

            for spec in self.date_patterns:
                for match in spec.compiled.finditer(text):
                    date_str = match.group(1)
                    if spec.name == 'numeric_date_ambiguous':
                        parsed_date = self._parse_numeric_date_with_locale(date_str, locale)
                    else:
                        parsed_date = self._parse_date_string(date_str)
                    if parsed_date:
                        if _debug is not None:
                            _debug['patterns_matched']['date'] = spec.name
                            _debug['confidence_per_field']['date'] = 0.9
                        return parsed_date

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

    def _calculate_confidence(self, parsed_data: Dict[str, Any]) -> float:
        """
        Calculate confidence score for parsed data.

        Args:
            parsed_data: Dictionary of parsed fields

        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.0

        if parsed_data.get('vendor'):
            score += 0.25
        if parsed_data.get('amount'):
            score += 0.35
        if parsed_data.get('date'):
            score += 0.25
        if parsed_data.get('currency'):
            score += 0.05
        if parsed_data.get('tax'):
            score += 0.10

        return round(score, 2)
