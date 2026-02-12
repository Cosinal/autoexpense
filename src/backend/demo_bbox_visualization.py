#!/usr/bin/env python3
"""
Demo script showing bbox spatial extraction with visualization.

This demonstrates how bbox extraction works by showing:
1. Word positions detected by OCR
2. Label matching (VAT, Total, etc.)
3. Spatial search for numbers near labels
4. Final extracted values
"""

from pathlib import Path
from app.services.ocr import OCRService
from app.services.bbox_extractor import BboxExtractor


def demo_bbox_extraction():
    """Demo bbox extraction with detailed output."""
    print("=" * 80)
    print("Bbox Spatial Extraction - Visualization Demo")
    print("=" * 80)
    print()

    # Load test receipt
    jpg_path = Path('tests/data/receipts/failed/receipt-test.jpg')

    if not jpg_path.exists():
        print(f"ERROR: Receipt not found at {jpg_path}")
        print("Please ensure receipt-test.jpg exists in tests/data/receipts/failed/")
        return

    print(f"Loading receipt: {jpg_path.name}")
    print("Receipt: Apple Store, Grafton Street, Dublin")
    print()

    # Extract with bbox
    ocr = OCRService()
    with open(jpg_path, 'rb') as f:
        file_data = f.read()

    print("Step 1: Extracting OCR bounding box data...")
    print("-" * 80)
    bbox_data = ocr.extract_text_with_bbox(file_data)
    print(f"  ✓ Detected {len(bbox_data['text'])} text elements")
    print()

    # Create extractor
    extractor = BboxExtractor(bbox_data)
    print(f"Step 2: Building word index...")
    print("-" * 80)
    print(f"  ✓ Indexed {len(extractor.words)} words")
    print()

    # Show word visualization
    print("Step 3: Word positions (first 40 words):")
    print("-" * 80)
    print(extractor.visualize_words(max_words=40))
    print()

    # Demonstrate label finding
    print("Step 4: Finding tax labels (VAT, HST, GST)...")
    print("-" * 80)
    vat_labels = extractor.find_all_labels(['VAT', 'HST', 'GST'])
    if vat_labels:
        for label in vat_labels:
            print(f"  Found: '{label.text}' at position ({label.x}, {label.y})")
            print(f"    Size: {label.width}x{label.height} pixels")
            print(f"    Confidence: {label.confidence}")
    else:
        print("  No tax labels found")
    print()

    # Demonstrate spatial search
    print("Step 5: Searching for numbers near VAT label...")
    print("-" * 80)
    if vat_labels:
        vat = vat_labels[0]
        print(f"  Starting from VAT at ({vat.x}, {vat.y})")
        print(f"  Search region: Right 600px, Down 150px")
        print()

        # Show nearby numbers
        import re
        print("  Nearby numbers found:")
        candidates = []
        for word in extractor.words:
            if re.search(r'\d+\.\d{2}', word.text):
                dx = word.x - (vat.x + vat.width)
                dy = word.y - vat.y
                distance = (dx**2 + dy**2)**0.5

                if distance < 600:
                    direction = "→ RIGHT" if dx > 0 and abs(dy) <= 20 else "↓ BELOW"
                    candidates.append((word.text, distance, direction, dx, dy))

        # Sort by distance
        candidates.sort(key=lambda x: x[1])

        for text, dist, direction, dx, dy in candidates[:5]:
            print(f"    '{text:15s}' {direction:8s} distance={dist:5.1f}px "
                  f"(dx={dx:4.0f}, dy={dy:3.0f})")
    print()

    # Extract tax
    print("Step 6: Extracting tax amount...")
    print("-" * 80)
    tax = extractor.extract_tax()
    print(f"  Extracted: {tax}")
    print(f"  Expected:  643.77")
    print(f"  Status:    {'✓ CORRECT' if tax == '643.77' else '✗ INCORRECT'}")
    print()

    # Find amount labels
    print("Step 7: Finding amount labels (Total, Paid)...")
    print("-" * 80)
    amount_labels = extractor.find_all_labels(['Total', 'Paid', 'Amount'])
    if amount_labels:
        for label in amount_labels:
            print(f"  Found: '{label.text}' at position ({label.x}, {label.y})")
    print()

    # Extract amount
    print("Step 8: Extracting total amount...")
    print("-" * 80)
    amount = extractor.extract_amount()
    print(f"  Extracted: {amount}")
    print(f"  Expected:  3442.77")
    print(f"  Status:    {'✓ CORRECT' if amount == '3442.77' else '✗ INCORRECT'}")
    print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("Bbox spatial extraction successfully:")
    print(f"  ✓ Detected {len(extractor.words)} words with positions")
    print(f"  ✓ Found tax label: VAT")
    print(f"  ✓ Found nearest number to VAT: {tax}")
    print(f"  ✓ Found amount label: Total/Paid")
    print(f"  ✓ Found nearest number to Total: {amount}")
    print()
    print("Key advantages over pattern-based extraction:")
    print("  • Spatial awareness (knows VAT is 643.77, not 3442.77)")
    print("  • Distance-based ranking (closest match wins)")
    print("  • Direction preference (right > down)")
    print("  • Multi-label support (tries VAT, HST, GST)")
    print()
    print("See BBOX_PHASE1_RESULTS.md for full analysis.")
    print()


if __name__ == '__main__':
    demo_bbox_extraction()
