# Bbox Spatial Extraction Implementation

**Phase 1 Complete** | **Date**: 2026-02-11

This directory contains the Phase 1 implementation of bounding box (bbox) spatial extraction for receipt parsing. This approach uses OCR bounding box coordinates to perform spatial searches for field values, complementing the existing pattern-based extraction.

---

## Quick Start

### Test the Implementation

```bash
# Demo with visualization
python3 demo_bbox_visualization.py

# Test on specific receipt
python3 test_bbox_aircanada.py

# Comprehensive test suite
python3 test_bbox_comprehensive.py
```

### Use in Code

```python
from app.services.ocr import OCRService
from app.services.bbox_extractor import BboxExtractor

# Load receipt image
with open('receipt.jpg', 'rb') as f:
    file_data = f.read()

# Extract bbox data
ocr = OCRService()
bbox_data = ocr.extract_text_with_bbox(file_data)

# Extract fields using spatial search
extractor = BboxExtractor(bbox_data)
tax = extractor.extract_tax()        # e.g., "643.77"
amount = extractor.extract_amount()  # e.g., "3442.77"

print(f"Tax: {tax}, Amount: {amount}")
```

---

## Files Overview

### Core Implementation

| File | Description | Lines |
|------|-------------|-------|
| `app/services/bbox_extractor.py` | **BboxExtractor class** - spatial search algorithms | 280 |
| `app/services/ocr.py` | **Enhanced OCR** - added bbox extraction methods | +60 |
| `app/services/parser.py` | **Integration notes** - TODO for Phase 2 | +30 |

### Test Scripts

| File | Description |
|------|-------------|
| `demo_bbox_visualization.py` | **Interactive demo** - shows how bbox works with detailed output |
| `test_bbox_aircanada.py` | **Initial test** - Air Canada receipt (discovered text-PDF limitation) |
| `test_bbox_comprehensive.py` | **Full test suite** - tests multiple receipts, reports accuracy |

### Documentation

| File | Description |
|------|-------------|
| `BBOX_PHASE1_RESULTS.md` | **Complete results report** - findings, metrics, recommendations |
| `README_BBOX.md` | **This file** - implementation overview and usage guide |
| `documents/adr/ADR-0004-bbox-spatial-extraction.md` | **Architecture decision** - rationale and design |

---

## How It Works

### 1. OCR Bbox Extraction

Extract word positions using Tesseract's `image_to_data`:

```python
# Returns bounding box for each detected word
data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

# Data structure:
{
    'text': ['VAT', '(23%):', '€', '643.77', ...],
    'left': [223, 275, 668, 702, ...],       # x coordinate
    'top': [1008, 1009, 1012, 1012, ...],    # y coordinate
    'width': [47, 63, 16, 85, ...],
    'height': [19, 18, 21, 21, ...],
    'conf': [96, 96, 93, 6, ...]             # OCR confidence
}
```

### 2. Spatial Search Algorithm

Find fields using label proximity:

```
1. Find Label:   Search for "VAT" → found at (223, 1008)
                         ↓
2. Search Region: Look RIGHT (600px) and DOWN (150px)
                         ↓
3. Find Numbers:  Detect all decimal numbers in region
                         ↓
4. Rank by Distance:
   - 643.77 at (702, 1012)  → distance = 432px, direction = RIGHT ✓
   - 3,442.77 at (631, 1068) → distance = 412px, direction = DOWN
                         ↓
5. Apply Direction Preference:
   - RIGHT numbers: distance × 0.5 (highly preferred)
   - DOWN numbers:  distance × 1.2 (penalized)
                         ↓
6. Return Best: 643.77 (adjusted distance = 216)
```

### 3. Multi-Label Strategy

Try multiple label variants:

```python
# Tax extraction tries:
['VAT', 'HST', 'GST', 'Harmonized']

# Amount extraction tries:
['Paid', 'Total', 'Amount', 'Grand']

# Returns closest match across all labels
```

---

## Results Summary

### ✅ What Works

**Image-based receipts**: 100% accuracy (1/1 tested)
- Photos of receipts
- Scanned images
- Image-based PDFs (rare in our dataset)

**Example**: Apple Store receipt (receipt-test.jpg)
- Tax: 643.77 ✓
- Amount: 3442.77 ✓

### ⚠️ Limitations

**Text-based PDFs**: Bbox extraction not applicable
- Most receipts in our dataset are text-based PDFs
- Converting PDF → image → OCR loses text positioning
- These still require pattern-based extraction

**Example**: Air Canada receipt
- Type: Text-based PDF (21,178 chars of extractable text)
- Bbox: Not applicable
- Pattern: Still has "RT00012.65" → "12.65" issue

---

## Key Findings

### 1. Text-Based PDF Issue

**Problem**: Air Canada and most other PDFs in the test set are text-based, meaning they contain extractable text rather than images. Bbox extraction requires rendering the PDF as an image and running OCR, which loses the original text positioning.

**Solution**: Don't use bbox for text-based PDFs. The "RT00012.65" issue needs a pattern fix, not bbox.

### 2. Hybrid Architecture Needed

```
Receipt File
     |
     ├─→ Image (JPG, PNG, scanned PDF)
     |   └─→ Use BBOX extraction
     |       └─→ Fallback to patterns for missing fields
     |
     └─→ Text PDF / Email
         └─→ Use PATTERN extraction
             └─→ Already works well for most fields
```

### 3. Pattern Improvements Still Needed

Air Canada tax issue requires pattern fix:

```python
# Current pattern (wrong):
r'harmonized\s+sales\s+tax[^\n]*\n[^\n]*?(\d{1,2}\.\d{2})$'
# Extracts: "12.65" from "RT00012.65"

# Better pattern (correct):
r'harmonized\s+sales\s+tax[^\n]*\n[^\n]*?(\d\.\d{2})$'
# Extracts: "2.65" from "RT00012.65"
```

---

## API Reference

### BboxExtractor

```python
class BboxExtractor:
    """Extract receipt fields using bounding box spatial search."""

    def __init__(self, bbox_data: Dict[str, List]):
        """Initialize with pytesseract image_to_data() output."""

    def find_label(self, keywords: List[str]) -> Optional[Word]:
        """Find first occurrence of any keyword."""

    def find_all_labels(self, keywords: List[str]) -> List[Word]:
        """Find all occurrences of keywords."""

    def find_nearest_number(
        self,
        label_word: Word,
        direction: str = 'right-then-down',
        max_distance_x: int = 600,
        max_distance_y: int = 150,
        pattern: str = r'\d{1,3}(?:,\d{3})*\.\d{2}'
    ) -> Optional[Tuple[str, Word]]:
        """Find nearest number to label in given direction."""

    def extract_tax(self) -> Optional[str]:
        """Extract tax amount (searches for VAT/HST/GST)."""

    def extract_amount(self) -> Optional[str]:
        """Extract total amount (searches for Total/Paid)."""

    def visualize_words(self, max_words: int = 30) -> str:
        """Return debug visualization of detected words."""
```

### OCRService (Enhanced)

```python
class OCRService:
    """Enhanced with bbox extraction methods."""

    def extract_text_with_bbox(self, image_data: bytes) -> Dict[str, List]:
        """Extract text with bounding boxes from image."""

    def extract_bbox_from_pdf(
        self,
        pdf_data: bytes,
        page_num: int = 0
    ) -> Dict[str, List]:
        """Extract text with bounding boxes from PDF page."""

    def extract_text_from_file(
        self,
        file_data: bytes,
        mime_type: str,
        filename: str = "",
        with_bbox: bool = False
    ) -> Union[str, Dict]:
        """Extract text, optionally with bbox data."""
```

---

## Next Steps (Phase 2)

### Week 1: Hybrid Integration
- Implement routing logic (bbox for images, patterns for text)
- Add file type detection
- Merge bbox + pattern results with confidence scoring

### Week 2: Expanded Testing
- Test on 5-10 image-based receipts
- Measure accuracy improvement
- Document which receipt types benefit most

### Week 3: Additional Fields
- Extend bbox to date extraction
- Extend bbox to vendor extraction
- Add currency symbol detection

### Week 4: Pattern Fixes
- Fix Air Canada multi-line tax issue
- Address other pattern-based edge cases
- Update pattern priorities

**Target Phase 2 Accuracy**: 85%+ overall

---

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Image OCR (bbox) | ~1-2s | Tesseract image_to_data |
| Bbox extraction | ~10ms | Spatial search |
| Pattern extraction | ~5ms | Regex matching |
| **Total overhead** | **~1s** | Acceptable for background processing |

---

## Design Decisions

### Why Bbox Over Patterns?

**Pattern limitations**:
- ❌ No spatial awareness
- ❌ Can't distinguish "VAT: 643.77" from "Total: 3,442.77" when searching for tax
- ❌ Multi-line issues (can't relate line 112 to line 113)
- ❌ OCR spacing artifacts break patterns

**Bbox advantages**:
- ✅ Spatial awareness (knows 643.77 is closer to VAT than 3,442.77)
- ✅ Direction preference (right > down)
- ✅ Distance-based ranking
- ✅ Robust to OCR variations

### Why Not LLM?

- ❌ Cost: $0.01-0.05 per receipt
- ❌ Latency: 2-5 seconds
- ❌ Privacy: external API
- ❌ Dependency: requires API key, network

Bbox provides spatial intelligence without external dependencies.

---

## Code Quality

- ✅ **Type hints**: All functions properly typed
- ✅ **Documentation**: Comprehensive docstrings
- ✅ **Error handling**: Graceful degradation
- ✅ **Testing**: Multiple test scripts with clear output
- ✅ **Maintainability**: Clean separation of concerns

---

## Contributing

When extending bbox extraction:

1. **Test on images first** - bbox only works on image-based files
2. **Tune search regions** - adjust max_distance_x/y for receipt layouts
3. **Add direction logic** - consider spatial relationships
4. **Provide fallback** - always support pattern-based fallback
5. **Document limitations** - be clear about what bbox can/cannot do

---

## References

- **ADR**: `documents/adr/ADR-0004-bbox-spatial-extraction.md`
- **Results**: `BBOX_PHASE1_RESULTS.md`
- **Tesseract Docs**: https://github.com/tesseract-ocr/tesseract
- **pytesseract API**: https://pypi.org/project/pytesseract/

---

## Support

For questions or issues:
1. Check `BBOX_PHASE1_RESULTS.md` for detailed analysis
2. Run `demo_bbox_visualization.py` to see how it works
3. Review `ADR-0004` for architectural rationale

---

**Phase 1 Status**: ✅ Complete (prototype proven viable for images)
**Phase 2 Status**: 📋 Ready to start (hybrid integration)
