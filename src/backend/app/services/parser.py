"""
Receipt parser service for extracting structured data from OCR text.
"""

import re
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal, InvalidOperation


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
            # Priority 1: Explicit payment indicators (highest confidence)
            (1, r'(?:amount\s+paid|total\s+paid|grand\s+total|final\s+total)[\s:]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),
            # Priority 1: Markdown bold total (Sephora: **Total: $59.52**)
            (1, r'\*\*total[\s:]+\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})\*\*'),
            # Priority 1: Order Summary with pipe separator (Urban Outfitters)
            # Use negative lookbehind to exclude "subtotal"
            (1, r'(?:order\s+summary|payment\s+summary)[\s\S]{0,200}?(?<!sub)total:\s*\|\s*[A-Z]{0,2}\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),
            # Priority 1: Total with pipe and C$ (Urban Outfitters: Total: | C$93.79)
            # Use negative lookbehind to exclude "subtotal"
            (1, r'(?<!sub)total:\s*\|\s*C\$\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),
            # Priority 1: TOTAL CAD $ format (PSA Canada)
            (1, r'total\s+cad\s+\$\s*\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),
            # Priority 2: Table format with pipe separator and currency code (Steam)
            # Use negative lookbehind to exclude "subtotal"
            (2, r'(?<!sub)(?:total|grand\s+total)[\s:*]*\|\s*(\d{1,3}(?:,\d{3})*\.?\d{0,2})\s*(?:CAD|USD|EUR|GBP|AUD)'),
            # Priority 2: Markdown bold total with pipe
            (2, r'\*\*(?:total|amount\s+due)\*\*[\s:]*\|\s*(\d{1,3}(?:,\d{3})*\.?\d{0,2})'),
            # Priority 2: Total with strong context
            (2, r'(?:^|\n|\|)\s*total[\s:]+[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),
            # Priority 3: Amount followed by currency code
            (3, r'(\d{1,3}(?:,\d{3})*\.\d{2})\s+(?:CAD|USD|EUR|GBP|AUD|NZD|CHF)'),
            # Priority 3: Generic total/amount
            (3, r'(?:total|amount|sum|paid)[\s:\|]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),
            # Priority 4: Currency symbol (last resort)
            (4, r'[$€£¥]\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'),
            # Priority 4: € with spaces (European format)
            (4, r'€\s+(\d{1,3}(?:,\d{3})*\.\d{2})'),
        ]

        # Blacklist contexts - amounts to ignore
        self.blacklist_contexts = [
            'liability', 'coverage', 'insurance', 'limit', 'maximum',
            'up to', 'points', 'pts', 'booking reference', 'confirmation',
            'reference', 'miles', 'rewards'
        ]

        # Date patterns
        self.date_patterns = [
            # MM/DD/YYYY or MM-DD-YYYY
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            # DD/MM/YYYY or DD-MM-YYYY
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            # Month DD, YYYY (Jan 15, 2024)
            r'([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})',
            # Month DD/YYYY (April 9/2025)
            r'([A-Za-z]{3,9}\s+\d{1,2}/\d{4})',
            # YYYY-MM-DD (ISO format)
            r'(\d{4}-\d{2}-\d{2})',
            # NEW: Ordinal dates (23rd November 2025) - GeoGuessr fix
            r'(\d{1,2}(?:st|nd|rd|th)\s+[A-Za-z]{3,9}\s+\d{4})',
        ]

        # IMPROVED: Tax patterns with pipe separator support
        self.tax_patterns = [
            # VAT (23%): € 643.77 - with percentage and currency
            r'vat[\s:()%\d]*[$€£¥]?\s+(\d{1,3}(?:,\d{3})*\.\d{2})',
            # Tax: $5.99, TAX 5.99, VAT: € 5.99
            r'tax[\s:]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
            # Sales Tax, HST, GST with currency symbols
            r'(?:sales tax|hst|gst)[\s:()%]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
            # NEW: Pipe separator support (for "HST| $1.09")
            r'(?:hst|gst|tax|vat)\s*\|\s*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
            # NEW: HST/GST without colon (for "HST $1.09")
            r'(?:hst|gst)\s+[$€£¥]\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
            # NEW: Sephora fix - Country-prefix tax (CANADA GST/TPS (5%): $2.62)
            r'(?:[A-Z\s]+\s+)?(?:gst|hst|pst)(?:/[A-Z]+)?\s*\([^\)]+\):\s*\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
            # NEW: Urban Outfitters - Tax with pipe separator
            r'tax:\s*\|\s*[A-Z]{0,2}\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
            # NEW: GeoGuessr - Multi-line tax (Sales Tax\n$0.33)
            r'(?:sales\s+tax|tax\s+total)\s*\n\s*([A-Z]{2,3})?\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
        ]

        # Subtotal patterns
        self.subtotal_patterns = [
            r'(?:sub\s*total|subtotal)[\s:]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
            r'(?:trip\s+fare|fare)[\s:\|]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
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
        result = {
            'vendor': self.extract_vendor(text),
            'amount': self.extract_amount(text),
            'currency': self.extract_currency(text),
            'date': self.extract_date(text),
            'tax': self.extract_tax(text),
            'confidence': 0.0,  # Placeholder for confidence scoring
        }

        # Calculate rough confidence score
        result['confidence'] = self._calculate_confidence(result)

        return result

    def _normalize_ocr_spaces(self, text: str) -> str:
        """
        Remove OCR-induced extra spaces between characters.
        Handles cases like "L o v a b l e" → "Lovable"
        """
        # Detect pattern: single chars with spaces
        if re.search(r'[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]', text):
            # Iteratively remove spaces between single characters
            pattern = r'\b([A-Za-z])\s+(?=[A-Za-z](\s+|$))'
            while True:
                new_text = re.sub(pattern, r'\1', text)
                if new_text == text:
                    break
                text = new_text
        return text

    def extract_vendor(self, text: str) -> Optional[str]:
        """
        Extract vendor/merchant name from receipt text.
        Works for both physical receipts and email receipts.

        Args:
            text: Receipt text

        Returns:
            Vendor name or None
        """
        try:
            # Normalize OCR spacing issues
            text = self._normalize_ocr_spaces(text)
            lines = text.split('\n')

            # First, try to extract from email "From:" field if present
            # Example: "From: **Uber Receipts** <noreply@uber.com>"
            for line in lines[:15]:  # Check more lines for email headers
                if line.strip().lower().startswith('from:'):
                    # Extract name from "From: Name <email>"
                    match = re.search(r'from:\s*\*?\*?([^<\*]+?)[\*\s]*(?:<|$)', line, re.IGNORECASE)
                    if match:
                        vendor = self._clean_vendor_name(match.group(1))
                        if vendor and len(vendor) > 2:
                            # Remove common email words
                            vendor = re.sub(r'\b(receipts?|notifications?|noreply|no-reply)\b', '', vendor, flags=re.IGNORECASE).strip()
                            if vendor and len(vendor) > 2:
                                return vendor

            # Known vendor patterns - detect common brands
            known_vendors = {
                r'\buber\b': 'Uber',
                r'\bamazon\b': 'Amazon',
                r'\bairbnb\b': 'Airbnb',
                r'\blyft\b': 'Lyft',
                r'\bdoordash\b': 'DoorDash',
                r'\bgrubhub\b': 'Grubhub',
                r'\bskip\s*the\s*dishes\b': 'Skip The Dishes',
                r'\bair\s*canada\b': 'Air Canada',
                r'\bwestjet\b': 'WestJet',
                r'\bapple\b': 'Apple',
                r'\bwalmart\b': 'Walmart',
                r'\btarget\b': 'Target',
                r'\bstarbucks\b': 'Starbucks',
                r'\bmcdonald': 'McDonald\'s',
                r'\bpsa\s+submission\b': 'PSA Canada',
                r'\bpsacanada@': 'PSA Canada',
            }

            # Check for known vendors in the entire text
            text_lower = text.lower()
            for pattern, name in known_vendors.items():
                if re.search(pattern, text_lower):
                    return name

            # Prioritize lines with company indicators (Inc, LLC, etc.)
            # Handle both spaced names and camelCase (e.g., "Lovable Labs Inc" or "LovableLabsIncorporated")
            for line in lines[:30]:
                match = re.search(r'([A-Z][a-zA-Z\s]{2,60}?(?:Incorporated|Inc|LLC|Ltd|Limited|Corp|Corporation|Labs))', line)
                if match:
                    # Extract just the company name portion
                    vendor = self._clean_vendor_name(match.group(1))
                    if vendor and len(vendor) > 5:
                        # Check if this is a payment processor
                        vendor_lower = vendor.lower()
                        if vendor_lower in self.PAYMENT_PROCESSORS:
                            real_merchant = self._extract_real_merchant(text)
                            if real_merchant:
                                print(f"  → Payment processor detected: {vendor} -> Real merchant: {real_merchant}")
                                return real_merchant
                        return vendor

            # Fallback: Try to find vendor in first few non-header lines
            email_skip_patterns = [
                r'^\s*[-=]+\s*forwarded\s+message\s*[-=]+',  # Forwarded message headers
                r'^\s*from:\s*',  # Email from field
                r'^\s*to:\s*',  # Email to field
                r'^\s*date:\s*',  # Email date field
                r'^\s*subject:\s*',  # Email subject field
                r'^\s*sent:\s*',  # Email sent field
                r'^\s*cc:\s*',  # Email cc field
                r'^\s*\[?https?://',  # URLs
                r'^\s*mailto:',  # Email links
                # PDF page headers (Lovable fix)
                r'^\s*page\s+\d+',  # "page 1", "Page 1"
                r'^\s*page\s+\d+\s+of\s+\d+',  # "page 1 of 1"
                r'^\s*\d+\s+of\s+\d+',  # "1 of 1"
                r'^\s*p\s*a\s*g\s*e\s+\d+',  # "P a g e  1" (OCR spaced)
            ]

            for line in lines[:20]:
                line = line.strip()

                # Skip email forwarding headers
                skip_line = False
                for pattern in email_skip_patterns:
                    if re.match(pattern, line, re.IGNORECASE):
                        skip_line = True
                        break
                if skip_line:
                    continue

                # Remove leading garbage characters
                line = re.sub(r'^[^\w\s]+', '', line)

                # Skip empty lines, dates, and numbers
                if not line or len(line) < 3:
                    continue
                if re.match(r'^\d{1,2}[/-]\d{1,2}', line):  # Looks like a date
                    continue
                if re.match(r'^\d+\.?\d*$', line):  # Just a number
                    continue

                # Skip common receipt header words (but allow if part of company name)
                skip_words = ['receipt', 'invoice', 'bill', 'order', 'thanks', 'thank you', 'trip', 'ride', 'booking']
                if line.lower() in skip_words:  # Only skip if it's JUST that word
                    continue

                # This line likely contains the vendor name
                vendor = self._clean_vendor_name(line)
                if vendor and len(vendor) > 2:
                    # Make sure it's not just generic words
                    generic_phrases = ['your order', 'your trip', 'your receipt', 'your booking']
                    if vendor.lower() not in generic_phrases:
                        # Check if this is a payment processor
                        vendor_lower = vendor.lower()
                        if vendor_lower in self.PAYMENT_PROCESSORS:
                            real_merchant = self._extract_real_merchant(text)
                            if real_merchant:
                                print(f"  → Payment processor detected: {vendor} -> Real merchant: {real_merchant}")
                                return real_merchant
                        return vendor

            return None

        except Exception as e:
            print(f"Error extracting vendor: {str(e)}")
            return None

    def _extract_real_merchant(self, text: str) -> Optional[str]:
        """
        Extract actual merchant when vendor is a payment processor.

        Args:
            text: Receipt text

        Returns:
            Real merchant name or None
        """
        # Check bank statement line (e.g., "statement as: PADDLE.NET* GEOGUESSR")
        # Look for "statement as:" followed by the actual statement text (on same or next line)
        statement_match = re.search(
            r'statement\s+as:\s*\n?\s*([A-Z][A-Z0-9\s\.\*]+?)(?:\n|$)',
            text,
            re.IGNORECASE | re.MULTILINE
        )
        if statement_match:
            statement = statement_match.group(1).strip()
            # Split on * or multiple spaces to get merchant name
            parts = re.split(r'[\*\s]{2,}', statement)
            # Return last part (usually the merchant)
            for part in reversed(parts):
                if len(part) > 2 and part.upper() not in ['NET', 'COM', 'INC', 'PADDLE']:
                    return part.strip().title()

        # Check for product name in invoice
        product_match = re.search(
            r'(?:Product|Description|Item)\s*\n\s*([A-Z][a-zA-Z\s]{2,30}?)(?:\s+(?:Unlimited|Subscription|Pro|Monthly|Annual|Premium)|$)',
            text,
            re.MULTILINE
        )
        if product_match:
            product_name = product_match.group(1).strip()
            # Clean up common suffixes
            product_name = re.sub(r'\s+(Unlimited|Subscription|Pro|Monthly|Annual|Premium)$', '', product_name, flags=re.IGNORECASE)
            if len(product_name) > 2:
                return product_name

        return None

    def _clean_vendor_name(self, name: str) -> str:
        """Clean and format vendor name."""
        # Remove special characters except spaces and &
        name = re.sub(r'[^A-Za-z0-9\s&\'-]', '', name)

        # Title case
        name = name.title()

        # Remove extra whitespace
        name = ' '.join(name.split())

        # Limit to reasonable vendor name length (first 50 chars)
        # This prevents grabbing too much text
        words = name.split()
        if len(words) > 6:  # Most vendor names are 1-6 words
            name = ' '.join(words[:6])

        return name.strip()

    def extract_amount(self, text: str) -> Optional[Decimal]:
        """
        Extract total amount from receipt using priority-based matching.

        Args:
            text: Receipt text

        Returns:
            Amount as Decimal or None
        """
        try:
            # Try patterns in priority order (lower number = higher confidence)
            for priority, pattern in self.amount_patterns:
                matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))

                for match in matches:
                    # Get narrow context window around the match (±50 chars)
                    # This prevents false positives from unrelated blacklist terms elsewhere on the line
                    context_start = max(0, match.start() - 50)
                    context_end = min(len(text), match.end() + 50)
                    context_window = text[context_start:context_end].lower()

                    # Skip if in blacklisted context
                    if any(bl in context_window for bl in self.blacklist_contexts):
                        continue

                    # Skip subtotals (prefer "Total" over "Subtotal")
                    # Check IMMEDIATE preceding text (on same line or very close)
                    # Only check 20 chars before and after to ensure it's THIS amount's label
                    immediate_preceding = text[max(0, match.start() - 20):match.start()].lower()
                    immediate_following = text[match.end():min(len(text), match.end() + 10)].lower()

                    # Skip if THIS amount is explicitly labeled as subtotal
                    if 'subtotal' in immediate_preceding or 'subtotal' in immediate_following:
                        # Unless it says "grand total" or similar
                        if 'grand' not in immediate_preceding and 'grand' not in immediate_following:
                            continue

                    amount_str = match.group(1) if match.groups() else match.group(0)
                    amount_str = amount_str.replace(',', '').replace('$', '').replace('€', '').replace('£', '').replace('¥', '').strip()

                    try:
                        amount = Decimal(amount_str)

                        # Sanity checks
                        if amount <= 0:
                            continue

                        # Flag suspiciously large amounts from low-priority patterns
                        if amount > 10000 and priority > 2:
                            continue  # Skip large amounts from generic patterns

                        # Found valid amount from this priority level
                        return amount

                    except (InvalidOperation, ValueError):
                        continue

            # No amount found with any pattern
            return None

        except Exception as e:
            print(f"Error extracting amount: {str(e)}")
            return None

    def extract_currency(self, text: str) -> str:
        """
        Extract currency from receipt.

        Args:
            text: Receipt text

        Returns:
            Currency code (USD, EUR, etc.) or 'USD' as default
        """
        try:
            # Check for currency symbols
            for symbol, code in self.currency_map.items():
                if symbol in text:
                    return code

            # Check for currency codes
            for code in ['USD', 'EUR', 'GBP', 'CAD', 'AUD']:
                if code in text.upper():
                    return code

            # Default to USD
            return 'USD'

        except Exception as e:
            print(f"Error extracting currency: {str(e)}")
            return 'USD'

    def extract_date(self, text: str) -> Optional[str]:
        """
        Extract receipt date.

        Args:
            text: Receipt text

        Returns:
            Date in YYYY-MM-DD format or None
        """
        try:
            # Try each date pattern
            for pattern in self.date_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Try to parse the date
                    parsed_date = self._parse_date_string(match)
                    if parsed_date:
                        return parsed_date

            return None

        except Exception as e:
            print(f"Error extracting date: {str(e)}")
            return None

    def _parse_date_string(self, date_str: str) -> Optional[str]:
        """
        Parse various date formats into YYYY-MM-DD.

        Args:
            date_str: Date string in various formats

        Returns:
            Date in YYYY-MM-DD format or None
        """
        # Handle ordinal suffixes (1st, 2nd, 3rd, 23rd)
        if re.search(r'\d+(?:st|nd|rd|th)', date_str):
            # Remove ordinal suffix: "23rd November 2025" -> "23 November 2025"
            date_str = re.sub(r'(\d+)(?:st|nd|rd|th)', r'\1', date_str)

        # Common date format patterns
        formats = [
            '%m/%d/%Y', '%m-%d-%Y',
            '%d/%m/%Y', '%d-%m-%Y',
            '%Y-%m-%d',
            '%m/%d/%y', '%m-%d-%y',
            '%d/%m/%y', '%d-%m-%y',
            '%B %d, %Y', '%b %d, %Y',
            '%B %d %Y', '%b %d %Y',
            '%d %B %Y', '%d %b %Y',  # 23 November 2025 (after stripping ordinal)
            '%B %d/%Y', '%b %d/%Y',  # April 9/2025
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        return None

    def extract_tax(self, text: str) -> Optional[Decimal]:
        """
        Extract tax amount from receipt, summing multiple tax lines if present.
        (e.g., Sephora has both GST and HST that should be summed)

        Args:
            text: Receipt text

        Returns:
            Total tax amount as Decimal or None
        """
        try:
            taxes = []

            # Try each tax pattern
            for pattern in self.tax_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Handle tuple results from patterns with multiple groups
                    if isinstance(match, tuple):
                        match = match[-1]  # Take last group (the amount)

                    tax_str = match.replace(',', '').replace('$', '').strip()
                    try:
                        tax = Decimal(tax_str)
                        if tax > 0:
                            taxes.append(tax)
                    except (InvalidOperation, ValueError):
                        continue

            # Deduplicate taxes (same amount matched multiple times in receipt)
            # Use set to get unique values, then convert back to list
            if taxes:
                unique_taxes = list(set(taxes))
                total_tax = sum(unique_taxes)
                if len(unique_taxes) > 1:
                    print(f"  → Found {len(unique_taxes)} unique tax line(s), total: ${total_tax}")
                return total_tax

            return None

        except Exception as e:
            print(f"Error extracting tax: {str(e)}")
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
        total_fields = 5  # vendor, amount, currency, date, tax

        # Give points for each field found
        if parsed_data.get('vendor'):
            score += 0.25
        if parsed_data.get('amount'):
            score += 0.35  # Amount is most important
        if parsed_data.get('date'):
            score += 0.25
        if parsed_data.get('currency'):
            score += 0.05
        if parsed_data.get('tax'):
            score += 0.10

        return round(score, 2)
