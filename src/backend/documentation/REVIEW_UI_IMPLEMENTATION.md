# Review UI with Candidate Options - Implementation Guide

## Overview

This feature allows users to manually review and correct receipt extractions with low confidence. The system presents the top 3 candidate options for each uncertain field, plus a custom input option. All corrections are stored for future ML training.

## ✅ Completed Backend Implementation

### 1. **Scoring Functions** (`app/utils/scoring.py`)
- ✅ Added `select_top_candidates()` - Returns top N candidates with scores
- ✅ Added field-specific functions:
  - `select_top_vendors()`
  - `select_top_amounts()`
  - `select_top_dates()`
  - `select_top_currencies()`

### 2. **Parser Updates** (`app/services/parser.py`)
- ✅ Added `review_candidates` to debug metadata
- ✅ Added `_capture_review_candidates()` method
- ✅ Captures top 3 options for fields with confidence < 0.7

### 3. **Database Schema** (`migrations/add_user_corrections.sql`)
- ✅ Added `user_corrections` JSONB column
- ✅ Added `corrected_at` TIMESTAMPTZ column
- ✅ Added GIN index for querying corrected receipts
- ✅ Schema designed for ML training export

**user_corrections Format:**
```json
{
  "vendor": {
    "original": "Acuvue Oasys 1-Day",
    "corrected_to": "Browz Eyeware & Eyecare",
    "candidates": ["Acuvue Oasys", "Jorden Shaw", "Browz Eyeware"],
    "confidence": 0.42,
    "corrected_by": "user_id"
  }
}
```

### 4. **Review API** (`app/routers/review.py`)
- ✅ `POST /review/submit` - Submit manual corrections
- ✅ `GET /review/pending` - Get receipts needing review
- ✅ `GET /review/corrections/export` - Export corrections for ML training

### 5. **Main App** (`app/main.py`)
- ✅ Registered review router

## 🔨 To Complete

### 1. **Run Database Migration** ✅ DONE

```bash
# In Supabase SQL Editor, run:
cat migrations/add_user_corrections.sql
```

Or via psql:
```bash
psql $DATABASE_URL -f migrations/add_user_corrections.sql
```

**Status:** Migration completed by user on 2026-02-10.

### 2. **Enhance Parser to Store Actual Candidates** ✅ DONE

~~Currently `_capture_review_candidates()` creates placeholder structures. We need to:~~

**Status:** Completed! Parser now captures actual top 3 candidates with scores.

**Implementation Details:**
- Modified `extract_vendor()` to store top 3 vendor candidates in `_debug['vendor_candidates']`
- Modified `extract_amount()` to store top 3 amount candidates in `_debug['amount_candidates']`
- Modified `extract_date()` to store top 3 date candidates in `_debug['date_candidates']`
- Modified `extract_currency()` to store top 3 currency candidates in `_debug['currency_candidates']`
- Updated `_capture_review_candidates()` to pull from these debug arrays instead of using empty placeholders

**Example Output:**
```json
{
  "vendor_candidates": [
    {"value": "Browz Eyeware", "score": 0.75, "pattern": "business_keyword"},
    {"value": "Acuvue Oasys", "score": 0.44, "pattern": "early_line"},
    {"value": "Contact Lens Co", "score": 0.40, "pattern": "early_line"}
  ],
  "amount_candidates": [
    {"value": "257.25", "score": 1.0, "pattern": "total_strong_context"},
    {"value": "245.00", "score": 0.98, "pattern": "generic_total"}
  ]
}
```

**Tested:** End-to-end test confirms candidates are captured, stored in database, and retrievable via review API.

### 3. **Frontend Review UI** ✅ DONE

Created review queue page at `/receipts/review`.

**Implementation Details:**

**File:** `src/frontend/app/receipts/review/page.tsx`

**Features Implemented:**
1. ✅ Fetches receipts needing review from GET `/review/pending`
2. ✅ Displays receipt preview (PDF iframe) side-by-side with correction form
3. ✅ Shows current extraction with confidence scores
4. ✅ Presents top 3 candidate options as radio buttons for each uncertain field
5. ✅ Displays confidence score and pattern name for each option
6. ✅ Provides custom input field as 4th option for any field
7. ✅ Submits corrections via POST `/review/submit`
8. ✅ Removes reviewed receipts from queue
9. ✅ Navigation: Previous/Skip/Submit buttons
10. ✅ Empty state when no receipts need review

**Navigation:**
- Added "Review Queue" button to main receipts page (`/receipts`)
- Yellow badge to stand out as action item

**User Flow:**
1. User clicks "Review Queue" button from receipts page
2. System loads all receipts with `needs_review: true`
3. User sees receipt preview on left, correction form on right
4. For each uncertain field:
   - Shows current value with confidence %
   - Lists top 3 options with their scores and patterns
   - Provides custom input option
5. User selects corrections and clicks "Submit Corrections"
6. System stores corrections in `user_corrections` for ML training
7. Receipt marked as reviewed and removed from queue
8. Next receipt automatically loaded

**Components Needed:** (original spec below for reference)

1. **ReviewQueue.tsx** - List of receipts needing review
```tsx
interface ReviewReceipt {
  id: string;
  vendor?: string;
  amount?: string;
  date?: string;
  needs_review: true;
  review_reason: string;
  ingestion_debug: {
    review_candidates: {
      vendor?: CandidateOptions;
      amount?: CandidateOptions;
      date?: CandidateOptions;
    }
  }
}

interface CandidateOptions {
  current_value: string;
  confidence: number;
  options: Array<{value: string, score: number, pattern: string}>;
}
```

2. **ReviewForm.tsx** - Form for correcting a single receipt
```tsx
// For each field with low confidence:
<FieldReview
  fieldName="vendor"
  currentValue="Acuvue Oasys"
  confidence={0.42}
  candidates={[
    {value: "Acuvue Oasys 1-Day", score: 0.42},
    {value: "Browz Eyeware & Eyecare", score: 0.35},
    {value: "Jorden Shaw", score: 0.25}
  ]}
  onSelect={(value) => handleCorrection('vendor', value)}
/>

// Radio buttons for options
{candidates.map(c => (
  <label>
    <input type="radio" name={fieldName} value={c.value} />
    {c.value} (confidence: {(c.score * 100).toFixed(0)}%)
  </label>
))}

// Custom input option
<label>
  <input type="radio" name={fieldName} value="custom" />
  Other: <input type="text" />
</label>
```

3. **Submit Corrections**
```tsx
const submitReview = async (receiptId, corrections) => {
  const response = await fetch('/api/review/submit', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      receipt_id: receiptId,
      corrections: {
        vendor: {
          original: "Acuvue Oasys",
          corrected_to: "Browz Eyeware & Eyecare",
          candidates: ["Acuvue Oasys", "Jorden Shaw", "Browz Eyeware"],
          confidence: 0.42
        }
      },
      user_id: currentUser.id
    })
  });
};
```

### 4. **Frontend Routes** ✅ DONE

~~Add to `src/frontend/app/receipts/review/page.tsx`:~~

**Status:** Complete! Route created and integrated.

```tsx
'use client'

import { useState, useEffect } from 'react'

export default function ReviewQueuePage() {
  const [receipts, setReceipts] = useState([])

  useEffect(() => {
    fetchPendingReviews()
  }, [])

  const fetchPendingReviews = async () => {
    const response = await fetch('/api/review/pending?user_id=' + userId)
    const data = await response.json()
    setReceipts(data.receipts)
  }

  return (
    <div>
      <h1>Review Queue ({receipts.length})</h1>
      {receipts.map(receipt => (
        <ReviewCard key={receipt.id} receipt={receipt} />
      ))}
    </div>
  )
}
```

## 📊 ML Training Data Export

Once users start making corrections, export training data:

```bash
curl "http://localhost:8000/review/corrections/export?user_id=admin&format=jsonl" > training_data.jsonl
```

Each line contains:
- Original OCR text (if stored)
- Original extractions
- User corrections
- Candidate options presented
- Confidence scores
- Timestamp

This data can train a model to:
1. Improve extraction accuracy
2. Better rank candidates
3. Predict when review is needed
4. Learn vendor-specific patterns from user corrections

## 🎯 Usage Flow

1. **Receipt Processed**
   - Parser extracts fields with confidence scores
   - Low confidence fields (< 0.7) → `needs_review = true`
   - Top 3 candidates stored in `ingestion_debug.review_candidates`

2. **User Reviews**
   - Opens review queue (`/receipts/review`)
   - Sees receipts flagged for review
   - For each uncertain field, sees 3 options + custom
   - Selects correct value or enters custom

3. **Correction Submitted**
   - POST to `/review/submit`
   - Receipt updated with corrected values
   - Original + correction stored in `user_corrections`
   - `needs_review` set to `false`

4. **ML Training**
   - Periodic export of all corrections
   - Train model on user feedback
   - Deploy improved parser
   - Repeat cycle

## 🔍 Benefits

1. **Better UX**: Users see likely options instead of blank field
2. **Faster Review**: Click radio button vs typing full value
3. **ML Training**: Every correction improves the system
4. **Transparency**: Users see why parser made its choice (confidence scores)
5. **Continuous Improvement**: System learns from mistakes

## Next Steps

1. Run database migration
2. Complete parser candidate capture
3. Build frontend review UI components
4. Test review flow end-to-end
5. Start collecting correction data
6. Plan ML model training pipeline
