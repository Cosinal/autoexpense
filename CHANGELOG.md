# Changelog

All notable changes to AutoExpense will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_No unreleased changes yet._

---

## [0.2.0] - 2026-02-10

### Added

#### Review UI with ML Training Data Collection
- **Review Queue Page** (`/receipts/review`): New interface for correcting uncertain receipt extractions
  - Displays receipt PDF preview alongside correction form
  - Shows top 3 candidate options with confidence scores for each uncertain field
  - Provides custom input option as 4th choice
  - All 5 fields editable (vendor, amount, date, currency, tax) regardless of confidence
  - Navigation: Previous/Skip/Submit buttons for queue management

- **Review API Endpoints**:
  - `GET /review/pending` - Fetch receipts needing review (needs_review=true)
  - `POST /review/submit` - Submit corrections and store for ML training
  - `GET /review/corrections/export` - Export training data in JSONL format

- **Parser Candidate Capture**: Enhanced extraction to capture top 3 candidates per field
  - `select_top_vendors()`, `select_top_amounts()`, `select_top_dates()`, `select_top_currencies()`
  - Candidates stored in `ingestion_debug.review_candidates` with scores and pattern names

- **Database Schema**:
  - Added `user_corrections` JSONB column to store manual corrections
  - Added `corrected_at` TIMESTAMPTZ column to track correction time
  - GIN index on `user_corrections` for ML training queries

#### Semantic Duplicate Detection
- Prevents duplicate receipts from same email with multiple attachments (e.g., Invoice.pdf + Receipt.pdf)
- Checks for matching vendor+amount+date (requires 2 of 3)
- Applied after file-hash check but before receipt creation

#### Vendor Extraction Improvements
- **Person Name Detection**: Identifies and penalizes customer names in forwarded emails
  - Detects 2-3 word title-case names (e.g., "Jorden Shaw")
  - Applies -0.6 score penalty when from email headers
  - Maintains business indicator list to avoid false positives
- **Business Keyword Patterns**: Enhanced detection for "Clinic", "Eyeware", "Medical", etc.
- **Payable-To Pattern**: Extracts vendor from "Make cheques payable to..." text

### Changed

- **Parser Normalization**: OCR spacing normalization now applied globally (not just first 15 lines)
- **Review Form UX**: All fields now editable, not limited to low-confidence fields
- **Vendor Scoring**: Email header candidates now properly penalized if they look like person names

### Fixed

- Fixed vendor extraction preferring user name over actual merchant (e.g., "Jorden Shaw" vs "Uber")
- Fixed duplicate receipts created from same transaction with different filenames
- Fixed PDF preview detection using file_path instead of file_url
- Fixed vendor extraction from BILL TO sections (now skips customer info)

### Migration Notes

**Database Migration Required**:
```sql
-- Run: src/backend/migrations/add_review_columns.sql
-- Run: src/backend/migrations/add_user_corrections.sql
```

**User-Facing Changes**:
- New "Review Queue" button on receipts page (yellow badge)
- Receipts with confidence < 0.7 now flagged for manual review
- Users can correct any field, not just uncertain ones
- Corrections stored for future ML model improvements

### Files Changed

**Backend**:
- `src/backend/app/routers/review.py` - New review API (269 lines)
- `src/backend/app/services/parser.py` - Candidate capture, OCR normalization
- `src/backend/app/services/ingestion.py` - Semantic duplicate detection
- `src/backend/app/utils/scoring.py` - Person name detection, vendor scoring
- `src/backend/app/utils/candidates.py` - New candidate data structures
- `src/backend/migrations/add_review_columns.sql` - Database schema
- `src/backend/migrations/add_user_corrections.sql` - ML training schema

**Frontend**:
- `src/frontend/app/receipts/review/page.tsx` - Review UI (550 lines)
- `src/frontend/app/receipts/page.tsx` - Added Review Queue button

**Documentation**:
- `documents/backend/REVIEW_UI_IMPLEMENTATION.md` - Complete implementation guide
- `documents/adr/ADR-0001-review-ui-with-ml-training.md` - Architecture decision record
- `documents/adr/ADR-0002-semantic-duplicate-detection.md` - Duplicate strategy ADR
- `documents/adr/ADR-0003-person-name-vendor-filtering.md` - Name detection ADR

### Technical Debt

- Parser candidate capture has placeholder logic for some fields (needs enhancement)
- No automated ML training pipeline (export is manual)
- Review UI doesn't show raw OCR text for debugging
- No analytics dashboard for correction patterns

---

## [0.1.0] - 2026-02-09

### Initial Release

#### Core Features
- Email receipt ingestion via Gmail API forwarding
- OCR extraction using Tesseract (PDF and image support)
- Automatic parsing of vendor, amount, date, currency, tax
- Supabase backend (database + file storage)
- Next.js frontend with receipt listing
- Export to CSV functionality
- File-hash-based deduplication

#### Architecture
- FastAPI backend with routers pattern
- Candidate-based extraction with confidence scoring
- Content-addressed storage with SHA-256 hashing
- Row-level security (RLS) in Supabase

#### Integrations
- Gmail API (OAuth 2.0)
- Supabase (PostgreSQL + Storage)
- Tesseract OCR

---

## Legend

- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security improvements
