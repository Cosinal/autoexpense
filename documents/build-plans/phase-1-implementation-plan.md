# Phase 1 Implementation Plan
**Goal:** Achieve the complete Phase 1 vision from roadmap-openai.md

---

## Gap Analysis

### Already Complete ✓
1. Email attachment processing (PDF, JPG, PNG)
2. OCR pipeline with Tesseract
3. Receipt parsing (vendor, amount, date, currency, tax)
4. Supabase storage with RLS
5. Dashboard with filters
6. CSV export with monthly summaries
7. Sync button for manual email polling

### Missing Features
1. **Email body as receipt** - Process HTML/text emails when no attachments
2. **Web photo upload** - Upload interface in dashboard
3. **InputDocument abstraction** - Unified data model for all input types
4. **HTML receipt parser** - Extract structured data from HTML emails
5. **Bulk upload UI** - Multi-file upload support

---

## Implementation Phases

### Phase 1A: Email Body Processing (2-3 hours)
**Priority: HIGH** - Core missing feature

**Tasks:**
1. Update email service to detect "no attachments" scenario
2. Extract HTML body from emails
3. Convert HTML to text/image for OCR
4. Route email body through existing OCR pipeline
5. Test with Uber, Amazon, airline receipts

**Files to modify:**
- `backend/app/services/email.py` - Add HTML extraction
- `backend/app/services/ingestion.py` - Add email body handling
- `backend/app/services/ocr.py` - Add HTML-to-text processing

**Success criteria:**
- Uber receipt emails are processed without attachments
- Amazon order confirmations extracted correctly
- Airline receipts captured

---

### Phase 1B: Web Photo Upload (2 hours)
**Priority: HIGH** - Critical UX feature

**Tasks:**
1. Create upload page in frontend
2. Add file upload API endpoint
3. Support multi-file selection
4. Route uploads through OCR pipeline
5. Show upload progress

**New files:**
- `frontend/app/upload/page.tsx` - Upload interface
- `backend/app/routers/upload.py` - Upload endpoint

**Files to modify:**
- `frontend/app/receipts/page.tsx` - Add "Upload" button
- `backend/app/main.py` - Include upload router

**Success criteria:**
- User can select multiple photos
- Photos are processed immediately
- Receipts appear in dashboard within 30 seconds

---

### Phase 1C: InputDocument Abstraction (1-2 hours)
**Priority: MEDIUM** - Architecture improvement

**Tasks:**
1. Create InputDocument model
2. Add source_type field (email_attachment, email_body, upload)
3. Update receipts table to include source tracking
4. Migrate existing data

**New files:**
- `backend/app/models/input_document.py`
- `database/migrations/003_add_source_type.sql`

**Success criteria:**
- All receipts tagged with source type
- Dashboard can filter by source
- Export includes source information

---

### Phase 1D: HTML Receipt Parser (2-3 hours)
**Priority: MEDIUM** - Enhanced parsing

**Tasks:**
1. Create HTML-specific parser
2. Add vendor-specific templates (Uber, Amazon, etc.)
3. Fallback to OCR if template fails
4. Extract structured data from common receipt emails

**New files:**
- `backend/app/services/html_parser.py`
- `backend/app/services/templates/` - Vendor templates

**Success criteria:**
- Uber receipts parsed with >90% accuracy
- Amazon orders captured correctly
- Generic HTML receipts fallback to OCR

---

### Phase 1E: Enhanced Bulk Upload (1 hour)
**Priority: LOW** - Already mostly works via email

**Tasks:**
1. Add drag-and-drop to upload page
2. Show processing status for each file
3. Handle errors gracefully
4. Add file size validation (10MB limit)

**Files to modify:**
- `frontend/app/upload/page.tsx`

---

## Implementation Order (Recommended)

### Sprint 1: Core Missing Features (4-5 hours)
1. Phase 1A: Email body processing
2. Phase 1B: Web photo upload

**Why:** These are the two critical gaps preventing full Phase 1 vision

### Sprint 2: Polish & Enhancement (3-4 hours)
3. Phase 1C: InputDocument abstraction
4. Phase 1D: HTML receipt parser
5. Phase 1E: Enhanced bulk upload

---

## Milestones

### Milestone 1: Complete Intake ✓ (Sprint 1)
- Email attachments working
- Email bodies working
- Web uploads working

### Milestone 2: Processing Reliability (Sprint 2)
- OCR accuracy >80%
- HTML parsing for common vendors
- Source tracking implemented

### Milestone 3: UX Polish (Already complete!)
- Dashboard usable ✓
- Export functional ✓
- Filters working ✓

### Milestone 4: Ready for Pilot
- All Phase 1 features complete
- Documentation for user onboarding
- Error handling robust

---

## Success Metrics (Phase 1 Complete)

- ✓ ≥80% receipts captured automatically
- ✓ CSV usable by accountant without manual cleanup
- ✓ User prefers AutoExpense over manual download
- ✓ All 4 input methods working (email attachment, email body, photo upload, bulk)

---

## Estimated Time to Complete

**Sprint 1 (Critical):** 4-5 hours
**Sprint 2 (Polish):** 3-4 hours

**Total:** 7-9 hours to achieve full Phase 1 vision

---

## Next Steps

1. Confirm implementation priority
2. Start with Sprint 1 (Email body + Photo upload)
3. Test with real receipts (Uber, Amazon, etc.)
4. Polish and deploy

---

**Ready to build this together?** 🚀
