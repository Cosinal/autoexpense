# ADR-0004: Bounding Box Spatial Extraction for Receipt Parsing

**Status**: Proposed
**Date**: 2026-02-11
**Deciders**: Engineering Team
**Tags**: parser, ocr, architecture

## Context

Our current receipt parser uses regex pattern matching on OCR-extracted text. With 13 test receipts, we've achieved 65.7% overall accuracy (target: 90%+).

### Current Approach Limitations

**1. Multi-line Issues**
- Air Canada receipt has "Harmonized Sales Tax - Canada - 100092287" on line 112
- Tax amount "2.65" appears as "RT00012.65" on line 113 (separate line, no spacing)
- Pattern extracts "12.65" instead of "2.65" - no reliable way to distinguish with regex alone

**2. OCR Spacing Artifacts**
- Anthropic receipt has spaces between every character: "H S T  -  C a n a d a"
- Preprocessing collapses spaces but creates new parsing issues
- Vendor extraction gets "I N V O I C" (partial word)

**3. Vendor Line Ambiguity**
- Early-line fallback strategy picks wrong lines (conjunctions, partial text)
- Skip patterns help but can't capture spatial context
- No way to know which line is "most prominent" or "header-like"

**4. Pattern Overfitting Risk**
- With only 13 receipts, patterns risk overfitting to specific formats
- Each fix for one receipt can break another
- Diminishing returns: Phase 1 (80% → 65.7%), Phase 2 (65.7% → 65.7%)

### Why Pattern-Based Has Hit a Wall

Regex patterns fundamentally lack spatial awareness:
- Can't measure "distance between label and value"
- Can't distinguish "number on same line" vs "number 2 lines down"
- Can't use font size, position, or proximity as signals

## Decision

**We will implement bounding box (bbox) coordinate-based extraction as the primary method for receipt parsing, with pattern-based as fallback.**

### Technical Approach

**1. OCR Enhancement**
- Use `pytesseract.image_to_data()` instead of `image_to_string()`
- Extract structured data for each word:
  ```python
  {
      'text': ['HST', '-', 'Canada', '3.92', ...],
      'left': [100, 150, 200, 450, ...],    # x coordinate
      'top': [50, 50, 50, 55, ...],         # y coordinate
      'width': [30, 10, 60, 40, ...],
      'height': [15, 15, 15, 15, ...],
      'conf': [95, 90, 92, 88, ...]         # confidence
  }
  ```

**2. Spatial Extraction Algorithm**
- **Find label**: Search for keywords ("HST", "Total", "Date") in text array
- **Get bbox**: Record coordinates of label position
- **Search region**: Define search area (e.g., "to the right", "below", "same line")
- **Find value**: Locate nearest number matching expected format in search region
- **Confidence score**: Distance-based scoring (closer = higher confidence)

**3. Example: Tax Extraction**
```python
# Find "HST" label at (100, 50)
hst_bbox = find_label("HST")

# Search right and down within 200px horizontal, 50px vertical
search_region = {
    'x_range': (hst_bbox.right, hst_bbox.right + 200),
    'y_range': (hst_bbox.top - 10, hst_bbox.top + 50)
}

# Find decimal number in region
tax_value = find_nearest_number(
    search_region,
    pattern=r'\d{1,3}\.\d{2}',
    direction='right-then-down'
)
```

**4. Integration Strategy**
- Add `BboxExtractor` class (new module)
- Modify `OCRService` to optionally return bbox data
- Update `ReceiptParser.parse()` to try bbox first, fallback to patterns
- Gradual rollout: start with tax/amount (highest impact), expand to all fields

## Alternatives Considered

### Alternative 1: LLM per Receipt
**Approach**: Send each receipt to GPT-4 Vision or Claude with extraction prompt

**Pros**:
- Highest accuracy potential (90%+ likely)
- Handles any format variation
- No pattern maintenance

**Cons**:
- **Cost**: $0.01-0.05 per receipt = $10-50 per 1000 receipts
- **Latency**: 2-5 seconds per receipt
- **Privacy**: Sending receipts to third-party API
- **Dependency**: Requires API key, network, external service

**Why Rejected**: User explicitly stated "I don't really want to do" this approach. Cost and privacy concerns for a personal expense tracker.

### Alternative 2: Continue Pattern Tuning
**Approach**: Keep adding regex patterns for edge cases

**Pros**:
- No architecture changes
- Incrementally improve

**Cons**:
- **Diminishing returns**: Phase 1 made things worse in some cases
- **Fragile**: Each fix risks breaking other receipts
- **Fundamental limit**: Regex can't solve spatial problems
- **Maintenance burden**: 50+ complex patterns already

**Why Rejected**: We've hit the limit of what patterns can achieve. Air Canada "RT00012.65" issue has no reliable pattern-based solution.

### Alternative 3: Hybrid (Pattern + LLM Fallback)
**Approach**: Use patterns, call LLM only for low-confidence extractions

**Pros**:
- Cost-effective (LLM only for ~10-20% of receipts)
- Better than pure patterns

**Cons**:
- Still requires external API
- Complexity of hybrid approach
- Doesn't solve root spatial issue

**Why Rejected**: Bbox approach gives spatial awareness without external dependencies.

## Consequences

### Positive

**1. Handles Multi-line Naturally**
- "Harmonized Sales Tax" on line 112, "RT00012.65" on line 113
- Bbox finds "HST" label, searches below, finds "2.65" at coordinates (150, 114)
- No regex pattern needed to bridge lines

**2. Robust to OCR Variations**
- Spacing artifacts less problematic (coordinates still correct)
- Can use confidence scores to filter low-quality OCR
- Font size and position provide additional signals

**3. Vendor Extraction Improvement**
- Can prioritize text at top of receipt (y < 100)
- Can prefer larger fonts (height > 20px)
- Can avoid footer regions (y > 80% of page height)

**4. No External Dependencies**
- Uses pytesseract (already a dependency)
- No API calls, no additional cost
- Privacy-preserving (all local processing)

**5. Explainable Results**
- Can visualize bbox matches (debugging aid)
- Clear confidence scores based on distance
- Easier to understand failures (show spatial diagram)

### Negative

**1. Implementation Complexity**
- New `BboxExtractor` class (~300-500 lines)
- OCR changes to extract bbox data
- Parser integration and fallback logic
- Testing coordinate calculations

**2. Performance Impact**
- `image_to_data()` is slower than `image_to_string()` (~1.5-2x)
- Additional processing for bbox search
- Estimated: +500ms per receipt (still acceptable for background processing)

**3. Image-Only Limitation**
- Bbox only works for images/PDFs (not pure text emails)
- Need to maintain pattern-based fallback for emails
- Hybrid system complexity

**4. Coordinate Accuracy Depends on OCR Quality**
- Poor scans = wrong coordinates
- Rotated images need pre-processing
- Very low-quality receipts may fail

### Risks

**1. OCR Bbox Quality Unknown**
- Tesseract bbox accuracy not yet tested on receipts
- May have issues with:
  - Rotated text
  - Curved receipts (photos)
  - Very small fonts
- **Mitigation**: Test on 13-receipt set, measure bbox accuracy before full rollout

**2. Coordinate System Complexity**
- Off-by-one errors in bbox calculations
- Search region tuning per field type
- Edge cases (text at page boundaries)
- **Mitigation**: Comprehensive unit tests, visual debugging tool

**3. Fallback Strategy Critical**
- If bbox fails, must gracefully fallback to patterns
- Pattern-based code still needs maintenance
- **Mitigation**: Clear fallback triggers (bbox unavailable, low confidence, no matches)

## Implementation Plan

### Phase 1: Prototype & Validation (Week 1)
1. Implement basic bbox extraction in OCRService
2. Create BboxExtractor with tax/amount extraction only
3. Test on Air Canada receipt (RT00012.65 issue)
4. Measure accuracy improvement on single field

**Success criteria**: Air Canada tax extracts 2.65 (currently 12.65)

### Phase 2: Full Field Coverage (Week 2)
1. Expand to all fields (vendor, date, currency, tax, amount)
2. Integrate with ReceiptParser
3. Implement pattern-based fallback
4. Test on all 13 receipts

**Success criteria**: Overall accuracy ≥85%

### Phase 3: Optimization & Refinement (Week 3)
1. Tune search regions per field
2. Add confidence scoring
3. Performance optimization
4. Visual debugging tool

**Success criteria**: Overall accuracy ≥90%, <2s per receipt

### Phase 4: Production Rollout (Week 4)
1. A/B test bbox vs pattern on new receipts
2. Monitor accuracy and performance
3. Gradual rollout to 100% of receipts
4. Update documentation

**Success criteria**: 90%+ sustained accuracy, no production issues

## Success Metrics

**Before (Pattern-Based)**:
- Overall accuracy: 65.7%
- Tax accuracy: 57.1%
- Vendor accuracy: 28.6%
- Air Canada tax: 12.65 (wrong)

**After (Bbox-Based) - Target**:
- Overall accuracy: ≥90%
- Tax accuracy: ≥90%
- Vendor accuracy: ≥80%
- Air Canada tax: 2.65 (correct)

**Leading Indicators** (Phase 1):
- Bbox extraction working for 12/13 receipts
- Tax field accuracy improved to ≥80%
- No regressions on currently working fields

## References

- **Tesseract Documentation**: https://github.com/tesseract-ocr/tesseract/blob/main/doc/ImprovedQualityInTesseract4.00.md
- **pytesseract image_to_data**: https://pypi.org/project/pytesseract/
- **Pattern Debugging Report**: `/PATTERN_DEBUGGING_REPORT.md`
- **Related ADRs**: ADR-0001 (review UI), ADR-0002 (duplicate detection), ADR-0003 (person names)

## Notes

- This ADR was created after pattern-based approach hit diminishing returns (Phase 1: 65.7%, Phase 2: 65.7%)
- User feedback: "Could we go for a moving bbox approach?" - spatial awareness needed
- Test set expanded from 7 to 13 receipts to reduce overfitting risk
- PSA Canada invoice note: "PSA" is acceptable (vendor doesn't explicitly state "PSA Canada")

---

**Last Updated**: 2026-02-11
**Author**: Engineering Team
**Reviewers**: TBD
**Implementation Status**: Not Started
