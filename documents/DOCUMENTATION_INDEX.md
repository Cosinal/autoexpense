# AutoExpense Documentation Index

**Last Updated**: 2026-02-12
**Version**: 0.3.0 (unreleased)

This document provides a comprehensive index of all AutoExpense documentation, organized by topic.

---

## 📊 Current Status

### Parsing Accuracy (13 Real Receipts)
- **Overall**: 75.4% (49/65 fields)
- **Currency**: 100.0% ✓
- **Amount**: 84.6% ✓
- **Date**: 76.9%
- **Tax**: 69.2%
- **Vendor**: 46.2% ⚠️

**Target**: 90%+ overall accuracy

---

## 🏗️ Architecture Decision Records (ADRs)

Location: `documents/adr/`

### Active ADRs
1. **[ADR-0001: Review UI with ML Training Data Collection](adr/ADR-0001-review-ui-with-ml-training.md)**
   - Status: Implemented (v0.2.0)
   - Captures user corrections for future ML improvements
   - Review queue for low-confidence extractions

2. **[ADR-0002: Semantic Duplicate Detection Strategy](adr/ADR-0002-semantic-duplicate-detection.md)**
   - Status: Implemented (v0.2.0)
   - Prevents duplicate receipts from same email with multiple attachments
   - Vendor+amount+date matching (2 of 3 required)

3. **[ADR-0003: Person Name Detection in Vendor Extraction](adr/ADR-0003-person-name-vendor-filtering.md)**
   - Status: Implemented (v0.2.0)
   - Identifies customer names in forwarded emails
   - Heavy penalty (-0.6) for person names from email headers

4. **[ADR-0004: Bounding Box Spatial Extraction for Receipt Parsing](adr/ADR-0004-bbox-spatial-extraction.md)**
   - Status: Phase 1 Complete (v0.3.0)
   - Uses pytesseract bbox coordinates for spatial search
   - 100% accuracy on image receipts
   - Text PDFs still use pattern-based approach
   - **Next**: Phase 2 - Hybrid integration

---

## 📖 Strategic Documents

### Parser Improvement Strategies

**[Vendor Parsing Strategies - Complete Analysis](VENDOR_PARSING_STRATEGIES.md)**
- Current approach analysis (pattern-based scoring)
- Industry analysis: How Stripe/Ramp/Brex solve this
- 4-phase improvement roadmap:
  - Phase 1: Pattern improvements (46% → 65%)
  - Phase 2: Vendor database (65% → 80%)
  - Phase 3: LLM-assisted validation (80% → 90%)
  - Phase 4: ML model fine-tuning (90% → 95%+)
- Specific fixes for current failures
- Cost/benefit analysis for each approach

---

## 🔧 Implementation Guides

### Backend Implementation

**[Review UI Implementation Guide](backend/REVIEW_UI_IMPLEMENTATION.md)**
- Complete implementation of review queue feature
- API endpoints, database schema, parser enhancements
- User correction storage for ML training

### Parser Implementation

**[Bbox Phase 1 Results](../src/backend/BBOX_PHASE1_RESULTS.md)**
- Spatial extraction using bounding box coordinates
- Test results: 100% on images, N/A on text PDFs
- Integration notes and Phase 2 roadmap

**[Bbox README](../src/backend/README_BBOX.md)**
- BboxExtractor API documentation
- Usage examples and integration guide

**[Phase 1 Complete Summary](../src/backend/PHASE1_COMPLETE.md)**
- Deliverables and achievements
- Critical findings (text-based PDF limitation)
- Next steps for Phase 2

---

## 🧪 Testing & Quality

### Test Suites

**Regression Tests**: `src/backend/tests/test_parser_regression.py`
- 9 comprehensive tests covering diverse receipt formats
- Steam, GeoGuessr, LinkedIn, Uber, Sephora, Walmart, Apple
- Tax deduplication, debug metadata validation
- **Status**: All 9 passing ✓

**Parser Accuracy Tests**: `src/backend/tests/test_parser_accuracy.py`
- 14 synthetic test cases (edge cases included)
- **Status**: 80% accuracy (11/14 passing)

**Receipt Batch Tests**: Real receipts in `src/backend/tests/data/receipts/`
- 13 actual receipts (7 original + 3 PDFs + 3 emails)
- Each has expected results JSON file
- **Status**: 75.4% overall accuracy

### Test Data
- `tests/data/receipts/failed/` - Challenging receipts for debugging
- `tests/data/receipts/*.json` - Expected results for validation

---

## 📝 Project Documentation

### Core Files

**[CHANGELOG.md](../CHANGELOG.md)**
- Version history and release notes
- Current: v0.2.0 (released 2026-02-10)
- Next: v0.3.0 (unreleased - parser refactoring)

**[README.md](../README.md)**
- Project overview and setup instructions
- Features, tech stack, roadmap

---

## 🗺️ Roadmaps & Planning

### Current Focus: Parser Accuracy Improvement

**Priority 1: Vendor Extraction (46% → 65%)**
- [ ] Fix OCR normalization for early lines
- [ ] Improve early-line scoring (boost lines 0-2)
- [ ] Add retail keyword boost
- [ ] Enhance person name detection
- [ ] Better payment processor filtering

**Priority 2: Tax Extraction (69% → 85%)**
- [ ] Fix Air Canada multi-line issue (RT00012.65)
- [ ] Handle tax-free receipts
- [ ] Improve tax pattern coverage

**Priority 3: Date Extraction (77% → 90%)**
- [ ] Improve non-standard date format handling
- [ ] Better locale detection

**Priority 4: Vendor Database (Phase 2)**
- [ ] Build 500-1000 common vendor database
- [ ] Implement fuzzy matching (Levenshtein)
- [ ] Add airline/retail category detection

**Future: LLM Fallback (Phase 3)**
- [ ] Selective LLM validation (confidence < 0.7)
- [ ] Cost-optimized prompts (< 500 tokens)
- [ ] Self-hosted Ollama option for privacy

---

## 🧑‍💻 Development Resources

### Code Organization

**Backend**:
- `src/backend/app/services/` - Core services (OCR, parser, ingestion)
- `src/backend/app/routers/` - API endpoints
- `src/backend/app/utils/` - Shared utilities (scoring, candidates)
- `src/backend/migrations/` - Database migrations

**Frontend**:
- `src/frontend/app/` - Next.js pages and components
- `src/frontend/app/receipts/review/` - Review queue UI

### Key Classes

**Parser Stack**:
1. `OCRService` - Tesseract integration, text extraction
2. `BboxExtractor` - Spatial search using coordinates (Phase 1)
3. `ReceiptParser` - Pattern-based extraction with scoring
4. `IngestionService` - Receipt processing pipeline

**Utilities**:
- `scoring.py` - Candidate scoring algorithms
- `candidates.py` - Dataclasses for extraction candidates
- `money.py` - Currency and amount parsing

---

## 🔬 Research & Analysis

### Performance Analysis

**Current Bottlenecks**:
1. **Vendor extraction**: Lowest accuracy field (46.2%)
   - OCR spacing artifacts
   - Multi-line confusion
   - Payment processor dominance
2. **Tax extraction**: Multi-line patterns unreliable (69.2%)
3. **Date extraction**: Non-standard formats challenging (76.9%)

**Optimization Opportunities**:
- Selective LLM validation (30% of receipts) → $0.06 per 1000 receipts
- Vendor database → 0 cost, 15-20% improvement
- Bbox integration Phase 2 → Better for image receipts

---

## 📚 External References

### Tools & Libraries
- **Tesseract OCR**: https://github.com/tesseract-ocr/tesseract
- **pytesseract**: https://pypi.org/project/pytesseract/
- **LayoutLMv3** (ML option): https://arxiv.org/abs/2204.08387
- **Donut** (ML option): https://arxiv.org/abs/2111.15664

### Industry Resources
- Stripe ML Blog: https://stripe.com/blog/applied-ml
- Document AI Benchmarks: https://paperswithcode.com/task/document-information-extraction

---

## 🎯 Success Metrics

### Version 0.3.0 Goals
- [ ] Vendor accuracy: 65%+ (current: 46.2%)
- [ ] Tax accuracy: 85%+ (current: 69.2%)
- [ ] Date accuracy: 90%+ (current: 76.9%)
- [ ] Overall accuracy: 85%+ (current: 75.4%)

### Version 1.0.0 Goals
- [ ] Vendor accuracy: 90%+ (with Phase 2 database)
- [ ] Overall accuracy: 90%+
- [ ] Vendor database: 500+ merchants
- [ ] LLM fallback option available

---

## 📞 Getting Help

### When Working on Parser
1. Check **[Vendor Parsing Strategies](VENDOR_PARSING_STRATEGIES.md)** for approaches
2. Review **[ADR-0004](adr/ADR-0004-bbox-spatial-extraction.md)** for spatial extraction
3. Run regression tests: `python3 tests/test_parser_regression.py`
4. Test on real receipts: See batch test script examples

### When Adding Features
1. Create ADR in `documents/adr/`
2. Update `CHANGELOG.md` in Unreleased section
3. Add documentation to relevant section of this index
4. Write tests before implementation

### When Debugging
1. Check `tests/data/receipts/failed/` for similar cases
2. Use `debug` field in parser results for confidence scores
3. Run `demo_bbox_visualization.py` for spatial analysis
4. Check `VENDOR_PARSING_STRATEGIES.md` for specific fixes

---

**Document Version**: 1.0
**Maintainer**: Engineering Team
**Next Review**: After v0.3.0 release
