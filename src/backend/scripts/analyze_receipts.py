"""
Script to download and analyze problematic receipts from Supabase storage.
"""

import os
import sys
import re
from decimal import Decimal
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.utils.supabase import get_supabase_client
from app.services.parser import ReceiptParser
from app.config import settings

USER_ID = "407b70ad-8e64-43a1-81b4-da0977066e6d"
DOWNLOAD_DIR = "/tmp/receipt_analysis"

def download_file(supabase, file_path: str, output_path: str):
    """Download file from Supabase storage."""
    try:
        # Download the file
        response = supabase.storage.from_(settings.RECEIPT_BUCKET).download(file_path)

        # Write to disk
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(response)

        print(f"Downloaded: {file_path} -> {output_path}")
        return True
    except Exception as e:
        print(f"Error downloading {file_path}: {str(e)}")
        return False


def analyze_text_file(file_path: str, parser: ReceiptParser):
    """Analyze a text file receipt."""
    print(f"\n{'='*80}")
    print(f"ANALYZING: {os.path.basename(file_path)}")
    print(f"{'='*80}\n")

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Show the raw content
    print("RAW CONTENT:")
    print("-" * 80)
    print(content[:1500])  # First 1500 chars
    if len(content) > 1500:
        print(f"\n... (truncated, total length: {len(content)} chars)")
    print("-" * 80)

    # Parse the receipt
    parsed = parser.parse(content)

    print("\nPARSED RESULTS:")
    print("-" * 80)
    for key, value in parsed.items():
        print(f"{key:12s}: {value}")
    print("-" * 80)

    # Test tax patterns specifically
    print("\nTAX PATTERN ANALYSIS:")
    print("-" * 80)

    # Look for HST, GST, tax-related lines
    tax_lines = []
    for line in content.split('\n'):
        if re.search(r'\b(tax|hst|gst|vat)\b', line, re.IGNORECASE):
            tax_lines.append(line.strip())

    if tax_lines:
        print("Lines containing tax keywords:")
        for line in tax_lines:
            print(f"  > {line}")
    else:
        print("No lines found with tax keywords")

    # Test each tax pattern manually
    print("\nTesting tax patterns:")
    for i, pattern in enumerate(parser.tax_patterns, 1):
        matches = re.findall(pattern, content, re.IGNORECASE)
        print(f"  Pattern {i}: {pattern[:50]}... -> {len(matches)} matches")
        if matches:
            print(f"    Matches: {matches[:3]}")  # Show first 3

    print("-" * 80)

    # AMOUNT PATTERN ANALYSIS
    print("\nAMOUNT PATTERN ANALYSIS:")
    print("-" * 80)

    # Look for lines with "total" or "amount"
    amount_lines = []
    for line in content.split('\n'):
        if re.search(r'\b(total|amount|sum|paid)\b', line, re.IGNORECASE):
            amount_lines.append(line.strip())

    if amount_lines:
        print("Lines containing amount keywords:")
        for line in amount_lines[:10]:
            print(f"  > {line}")
    else:
        print("No lines found with amount keywords")

    # Test each amount pattern manually
    print("\nTesting amount patterns:")
    for i, (priority, pattern) in enumerate(parser.amount_patterns, 1):
        matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
        print(f"  Pattern {i} (priority {priority}): {len(matches)} matches")
        if matches:
            print(f"    Matches: {matches[:5]}")  # Show first 5

    # Look for all dollar amounts
    print("\nAll dollar signs found:")
    dollar_pattern = r'\$\s*(\d+\.?\d*)'
    dollar_matches = re.findall(dollar_pattern, content)
    if dollar_matches:
        print(f"  Found {len(dollar_matches)} amounts: {dollar_matches[:10]}")

    print("-" * 80)

    return parsed, content


def analyze_pdf(file_path: str):
    """Analyze a PDF file."""
    print(f"\n{'='*80}")
    print(f"ANALYZING PDF: {os.path.basename(file_path)}")
    print(f"{'='*80}\n")

    try:
        import PyPDF2

        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            num_pages = len(pdf_reader.pages)
            print(f"PDF has {num_pages} page(s)")
            print("\nEXTRACTED TEXT:")
            print("-" * 80)

            full_text = ""
            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                full_text += text + "\n"
                print(f"\n--- Page {i+1} ---")
                print(text[:1000])  # First 1000 chars per page
                if len(text) > 1000:
                    print(f"... (truncated, page length: {len(text)} chars)")

            print("-" * 80)

            # Parse with our parser
            parser = ReceiptParser()
            parsed = parser.parse(full_text)

            print("\nPARSED RESULTS:")
            print("-" * 80)
            for key, value in parsed.items():
                print(f"{key:12s}: {value}")
            print("-" * 80)

            # Look for all dollar amounts
            print("\nALL DOLLAR AMOUNTS FOUND:")
            print("-" * 80)
            amount_pattern = r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
            amounts = re.findall(amount_pattern, full_text)
            if amounts:
                for amt in amounts:
                    print(f"  ${amt}")
            else:
                print("  No dollar amounts found")

            # Look for booking reference
            print("\nBOOKING REFERENCE ANALYSIS:")
            print("-" * 80)
            booking_patterns = [
                r'booking\s+(?:reference|code|number|confirmation)[:\s]*([A-Z0-9]{6,})',
                r'confirmation[:\s]*([A-Z0-9]{6,})',
                r'reference[:\s]*([A-Z0-9]{6,})',
            ]
            for pattern in booking_patterns:
                matches = re.findall(pattern, full_text, re.IGNORECASE)
                if matches:
                    print(f"  Found: {matches}")

            print("-" * 80)

            # VENDOR ANALYSIS (for Lovable PDFs)
            print("\nVENDOR ANALYSIS:")
            print("-" * 80)

            # Look for "P A G E" pattern (garbled OCR)
            if "P A G E" in full_text or "P A G E 1 O" in full_text:
                print("  WARNING: Found garbled 'P A G E' pattern")
                page_lines = [line for line in full_text.split('\n') if 'P A G E' in line or 'PAGE' in line][:5]
                for line in page_lines:
                    print(f"    > {line.strip()}")

            # Look for company names
            company_keywords = ['invoice', 'receipt', 'lovable', 'company', 'ltd', 'inc', 'llc', 'corp']
            print("\n  Lines with company keywords:")
            for line in full_text.split('\n')[:30]:  # First 30 lines
                if any(kw in line.lower() for kw in company_keywords):
                    print(f"    > {line.strip()}")

            # Check first 10 lines for vendor
            print("\n  First 10 lines (likely vendor location):")
            for i, line in enumerate(full_text.split('\n')[:10], 1):
                if line.strip():
                    print(f"    {i}: {line.strip()}")

            print("-" * 80)

            return parsed, full_text

    except ImportError:
        print("PyPDF2 not installed. Installing...")
        os.system("pip install PyPDF2")
        return analyze_pdf(file_path)
    except Exception as e:
        print(f"Error analyzing PDF: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None


def test_pattern_fixes(content: str):
    """Test proposed pattern fixes."""
    print(f"\n{'='*80}")
    print("TESTING PROPOSED PATTERN FIXES")
    print(f"{'='*80}\n")

    # Original patterns
    original_patterns = [
        r'vat[\s:()%\d]*[$€£¥]?\s+(\d{1,3}(?:,\d{3})*\.\d{2})',
        r'tax[\s:]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
        r'(?:sales tax|hst|gst)[\s:()%]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
    ]

    # Proposed improved patterns
    improved_patterns = [
        # Original patterns
        r'vat[\s:()%\d]*[$€£¥]?\s+(\d{1,3}(?:,\d{3})*\.\d{2})',
        r'tax[\s:]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
        r'(?:sales tax|hst|gst)[\s:()%]*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
        # NEW: Handle "HST| $1.09" format (pipe separator)
        r'(?:hst|gst|tax|vat)\s*\|\s*[$€£¥]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
        # NEW: Handle "HST $1.09" without colon
        r'(?:hst|gst)\s+[$€£¥]\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
    ]

    print("ORIGINAL PATTERNS:")
    for i, pattern in enumerate(original_patterns, 1):
        matches = re.findall(pattern, content, re.IGNORECASE)
        print(f"{i}. {pattern[:60]}...")
        print(f"   Matches: {len(matches)}")
        if matches:
            print(f"   Values: {matches[:5]}")

    print("\n" + "-"*80 + "\n")

    print("IMPROVED PATTERNS:")
    for i, pattern in enumerate(improved_patterns, 1):
        matches = re.findall(pattern, content, re.IGNORECASE)
        print(f"{i}. {pattern[:60]}...")
        print(f"   Matches: {len(matches)}")
        if matches:
            print(f"   Values: {matches[:5]}")

    print("-" * 80)


def main():
    """Main analysis function."""
    print("Receipt Parser Analysis Tool")
    print("="*80)

    # Initialize
    supabase = get_supabase_client()
    parser = ReceiptParser()

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # Files to analyze - Steam and Lovable receipts (with actual storage names)
    files_to_analyze = [
        {
            'path': f'{USER_ID}/8d3f7351-64a6-46d1-aaa6-ebfc8fe42e2b_email_19c30b1e.txt',
            'local': f'{DOWNLOAD_DIR}/steam_email.txt',
            'type': 'text'
        },
        {
            'path': f'{USER_ID}/cac795c8-cc25-437d-9ee1-87abdbfd4eae_Invoice-NEQQK5NF-0007.pdf',
            'local': f'{DOWNLOAD_DIR}/lovable_invoice.pdf',
            'type': 'pdf'
        },
        {
            'path': f'{USER_ID}/39cfed0d-8710-42ff-b205-b62f0ce212a7_Receipt-2556-3007.pdf',
            'local': f'{DOWNLOAD_DIR}/lovable_receipt.pdf',
            'type': 'pdf'
        }
    ]

    results = []

    for file_info in files_to_analyze:
        # Download file
        success = download_file(supabase, file_info['path'], file_info['local'])

        if success:
            # Analyze based on type
            if file_info['type'] == 'text':
                parsed, content = analyze_text_file(file_info['local'], parser)
                if content:
                    results.append({
                        'file': file_info['path'],
                        'parsed': parsed,
                        'content': content
                    })
                    # Test pattern fixes
                    test_pattern_fixes(content)
            elif file_info['type'] == 'pdf':
                parsed, content = analyze_pdf(file_info['local'])
                if content:
                    results.append({
                        'file': file_info['path'],
                        'parsed': parsed,
                        'content': content
                    })

    # Final summary
    print(f"\n{'='*80}")
    print("ANALYSIS SUMMARY")
    print(f"{'='*80}\n")

    for result in results:
        print(f"File: {os.path.basename(result['file'])}")
        print(f"  Vendor: {result['parsed'].get('vendor')}")
        print(f"  Amount: {result['parsed'].get('amount')}")
        print(f"  Tax: {result['parsed'].get('tax')}")
        print(f"  Date: {result['parsed'].get('date')}")
        print()


if __name__ == '__main__':
    main()
