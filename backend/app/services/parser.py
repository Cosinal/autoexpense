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

        # Amount patterns
        self.amount_patterns = [
            # $99.99, $1,234.56
            r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            # TOTAL: 99.99, Total 99.99
            r'(?:total|amount|sum)[\s:]*\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
            # 99.99 at end of line (common in receipts)
            r'(\d{1,3}(?:,\d{3})*\.\d{2})\s*$',
        ]

        # Date patterns
        self.date_patterns = [
            # MM/DD/YYYY or MM-DD-YYYY
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            # DD/MM/YYYY or DD-MM-YYYY
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            # Month DD, YYYY (Jan 15, 2024)
            r'([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})',
            # YYYY-MM-DD (ISO format)
            r'(\d{4}-\d{2}-\d{2})',
        ]

        # Tax patterns
        self.tax_patterns = [
            # Tax: $5.99, TAX 5.99
            r'tax[\s:]*\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
            # Sales Tax, HST, GST, VAT
            r'(?:sales tax|hst|gst|vat)[\s:]*\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
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
        Usually the first line or most prominent text.

        Args:
            text: Receipt text

        Returns:
            Vendor name or None
        """
        try:
            lines = text.split('\n')

            # Try to find vendor in first few lines
            for line in lines[:5]:
                line = line.strip()

                # Skip empty lines, dates, and numbers
                if not line or len(line) < 3:
                    continue
                if re.match(r'^\d{1,2}[/-]\d{1,2}', line):  # Looks like a date
                    continue
                if re.match(r'^\d+\.?\d*$', line):  # Just a number
                    continue

                # Skip common receipt header words
                skip_words = ['receipt', 'invoice', 'bill', 'order', 'tax']
                if any(word in line.lower() for word in skip_words):
                    continue

                # This line likely contains the vendor name
                # Clean it up
                vendor = self._clean_vendor_name(line)
                if vendor and len(vendor) > 2:
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

        return name.strip()

    def extract_amount(self, text: str) -> Optional[Decimal]:
        """
        Extract total amount from receipt.

        Args:
            text: Receipt text

        Returns:
            Amount as Decimal or None
        """
        try:
            amounts = []

            # Try each pattern
            for pattern in self.amount_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    amount_str = match.group(1) if match.groups() else match.group(0)
                    # Remove commas and convert to decimal
                    amount_str = amount_str.replace(',', '').replace('$', '').strip()
                    try:
                        amount = Decimal(amount_str)
                        if amount > 0:
                            amounts.append(amount)
                    except (InvalidOperation, ValueError):
                        continue

            if not amounts:
                return None

            # Return the largest amount (usually the total)
            return max(amounts)

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
