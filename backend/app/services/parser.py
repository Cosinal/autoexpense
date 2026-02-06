"""
Receipt parser service for extracting structured data from OCR text.
"""

import re
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal, InvalidOperation


class ReceiptParser:
    """Service for parsing receipt text and extracting structured data."""

    def __init__(self):
        """Initialize parser with regex patterns."""
        self._init_patterns()

    def _init_patterns(self):
        """Initialize regex patterns for parsing."""

        # IMPROVED: Priority-based amount patterns (lower number = higher priority)
        self.amount_patterns = [
            # Priority 1: Explicit payment indicators (highest confidence)
            (1, r'(?:amount\s+paid|total\s+paid|grand\s+total|final\s+total)[\s:]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),
            # Priority 2: Total with strong context
            (2, r'(?:^|\n|\|)\s*total[\s:]+[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'),
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
            }

            # Check for known vendors in the entire text
            text_lower = text.lower()
            for pattern, name in known_vendors.items():
                if re.search(pattern, text_lower):
                    return name

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
                        return vendor

            return None

        except Exception as e:
            print(f"Error extracting vendor: {str(e)}")
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
        # Common date format patterns
        formats = [
            '%m/%d/%Y', '%m-%d-%Y',
            '%d/%m/%Y', '%d-%m-%Y',
            '%Y-%m-%d',
            '%m/%d/%y', '%m-%d-%y',
            '%d/%m/%y', '%d-%m-%y',
            '%B %d, %Y', '%b %d, %Y',
            '%B %d %Y', '%b %d %Y',
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
        Extract tax amount from receipt.

        Args:
            text: Receipt text

        Returns:
            Tax amount as Decimal or None
        """
        try:
            # Try each tax pattern
            for pattern in self.tax_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    tax_str = match.replace(',', '').replace('$', '').strip()
                    try:
                        tax = Decimal(tax_str)
                        if tax > 0:
                            return tax
                    except (InvalidOperation, ValueError):
                        continue

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
