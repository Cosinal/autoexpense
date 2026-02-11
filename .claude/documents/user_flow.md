# AutoExpense: User Flow Documentation

**Last Updated**: 2026-02-10
**Purpose**: Document end-to-end user journeys from the user's perspective.

---

## Primary User Journey

### 1. Signup & Onboarding

**Current State** (needs improvement):
1. User visits autoexpense.io
2. Clicks "Sign Up"
3. Enters email + password
4. Lands on empty dashboard (⚠️ no guidance)

**Target State** (after improvements):
1. User visits autoexpense.io
2. Clicks "Sign Up"
3. Enters email + password
4. Receives email verification link
5. Clicks verification link
6. Sees onboarding wizard:
   - Step 1: "Welcome! Here's how AutoExpense works"
   - Step 2: "Connect your Gmail" (OAuth button)
   - Step 3: "Forward a test receipt or upload one"
7. Receives welcome email with intake address
8. Lands on dashboard with clear next steps

**Pain Points**:
- No guidance after signup
- Don't know how to forward receipts
- Don't know intake email address
- Blank dashboard is confusing

---

### 2. Receipt Upload (Manual)

**Flow**:
1. User clicks "Upload Receipt" button
2. Selects PDF or image file (drag-and-drop or file picker)
3. File uploads, shows loading spinner
4. OCR processes in background (30-60 seconds)
5. Receipt appears in list with parsed data
6. If confidence low, flagged for review (yellow badge)

**Success Path**:
- Receipt parses correctly
- User sees vendor, amount, date, currency, tax
- No action needed

**Failure Paths**:
- **File too large**: Error message "File must be under 10MB"
- **Unsupported format**: Error message "Only PDF, JPG, PNG supported"
- **OCR fails**: Shows blank fields, flags for review
- **Parser fails**: Shows partial data, flags uncertain fields

---

### 3. Email Ingestion (Automated)

**Flow**:
1. User forwards receipt to intake@autoexpense.io
2. Gmail receives email
3. Backend polls Gmail API (currently manual, needs cron)
4. Downloads attachment
5. Processes same as manual upload
6. User sees receipt in dashboard next time they check

**Pain Points**:
- Polling is manual (needs automated cron job)
- No real-time notification when receipt processed
- User doesn't know if forwarding worked

---

### 4. Review & Correction

**Flow**:
1. User sees "Review Queue (3)" badge on dashboard
2. Clicks "Review Queue" button
3. Lands on `/receipts/review` page
4. Sees receipt PDF preview on left, form on right
5. For each field (vendor, amount, date, currency, tax):
   - If low confidence: Shows top 3 candidates with scores
   - Radio buttons to select correct option
   - "Custom" option to type manually
6. User selects correct values
7. Clicks "Submit"
8. Receipt updated, removed from review queue
9. Next receipt loads automatically

**Success Path**:
- User finds correct value in top 3 candidates
- Quick radio button selection
- Moves through queue efficiently

**Failure Paths**:
- Correct value not in top 3 → User types manually
- PDF preview doesn't load → User can't verify
- Uncertain which candidate is correct → Guesses

---

### 5. Export to CSV

**Flow**:
1. User clicks "Export CSV" button
2. Optional: Applies filters (date range, vendor, min amount)
3. Clicks "Download"
4. CSV file downloads to browser
5. User opens in Excel or sends to accountant

**CSV Format**:
```
Vendor,Amount,Currency,Date,Tax,Confidence,Source
Uber,15.67,CAD,2026-02-09,2.04,0.85,email
Starbucks,7.89,CAD,2026-02-10,1.03,0.92,upload
```

**Pain Points**:
- CSV doesn't include receipt file URLs (accountant can't verify)
- No export to Excel (.xlsx) format
- No custom column selection

---

## Error Handling Flows

### OCR Fails (Text Extraction)

**Scenario**: Tesseract can't read receipt (faded ink, handwritten, etc.)

**Flow**:
1. OCR returns empty text
2. Parser has nothing to work with
3. Receipt saved with all fields null
4. Flagged for review
5. User sees "OCR failed - please review manually"
6. User types all fields manually

**Improvement Needed**: Show raw OCR text in review UI for debugging.

---

### Parser Fails (Extraction)

**Scenario**: OCR succeeds but parser can't find vendor/amount/date

**Flow**:
1. Parser returns low confidence (<0.5)
2. Receipt saved with uncertain fields
3. Flagged for review
4. User corrects via review UI

**Improvement Needed**: Better error messages ("Vendor not found - check receipt format").

---

### Duplicate Receipt

**Scenario**: User forwards same receipt twice

**Flow**:
1. File hash matches existing receipt → Skip
2. OR: Vendor+amount+date matches existing receipt → Skip (semantic duplicate)
3. Receipt not saved
4. User never knows (silent deduplication)

**Improvement Needed**: Show "Duplicate detected - skipped" notification.

---

### Upload Fails (Network/Server Error)

**Scenario**: Network error during upload

**Flow**:
1. Upload fails
2. User sees error message "Upload failed - please try again"
3. User retries

**Improvement Needed**: Auto-retry on transient failures.

---

## Key User Expectations

### Speed
- Upload → See receipt: <60 seconds
- Review correction → Update: <2 seconds
- Export CSV: <5 seconds

### Accuracy
- 90%+ fields parse correctly
- Low false positives on duplicates
- Correct currency detection

### Transparency
- Know when receipt is processing
- Understand why confidence is low
- See what parser extracted vs what OCR found

### Ease of Correction
- Top 3 candidates include correct value 80%+ of time
- Typing manual value is fast fallback
- Can correct any field, not just flagged ones

---

## Future Flows (Out of Scope for Lean Launch)

- **Receipt search**: Full-text search across vendor, notes, OCR text
- **Bulk operations**: Select multiple receipts → delete/export/tag
- **Receipt categorization**: Auto-tag as meals, travel, office supplies
- **Analytics**: Spending dashboard by category, vendor, time
- **Mobile upload**: Photo capture via phone camera

---

**Document Owner**: Product & Engineering
**Review Cadence**: Update when workflows change
