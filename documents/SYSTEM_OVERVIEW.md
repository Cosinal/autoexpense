# AutoExpense System Overview

**Version**: 1.0
**Last Updated**: 2026-02-10

---

## Architecture Summary

AutoExpense is a **3-tier web application** following a **layered service architecture** pattern:

```
┌─────────────────────────────────────────────────────────┐
│                    USER LAYER                            │
│  ┌────────────────┐              ┌─────────────────┐   │
│  │  Web Browser   │              │  Mobile Browser │   │
│  │  (Desktop)     │              │  (Responsive)   │   │
│  └────────┬───────┘              └────────┬────────┘   │
└───────────┼───────────────────────────────┼────────────┘
            │                               │
            │         HTTPS/TLS             │
            ▼                               ▼
┌───────────────────────────────────────────────────────────┐
│              PRESENTATION LAYER                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Next.js 15 Frontend (React 19 + Tailwind CSS)   │    │
│  │  • Server-side rendering (SSR)                    │    │
│  │  • Client-side routing (App Router)               │    │
│  │  • Supabase Auth client integration               │    │
│  └────────────┬──────────────────────────────────────┘   │
└────────────── │ ─────────────────────────────────────────┘
               │ REST API calls
               │ (JSON over HTTPS)
               ▼
┌───────────────────────────────────────────────────────────┐
│               APPLICATION LAYER                            │
│  ┌──────────────────────────────────────────────────┐    │
│  │  FastAPI Backend (Python 3.11+)                   │    │
│  │                                                    │    │
│  │  ┌──────────────┐  ┌──────────────┐             │    │
│  │  │   Routers    │  │   Services   │             │    │
│  │  │  (HTTP API)  │◄─┤   (Business  │             │    │
│  │  │              │  │    Logic)    │             │    │
│  │  └──────────────┘  └──────┬───────┘             │    │
│  │                            │                      │    │
│  │  ┌──────────────┐  ┌──────▼───────┐             │    │
│  │  │    Utils     │  │   External   │             │    │
│  │  │  (Helpers)   │  │  Integrations│             │    │
│  │  └──────────────┘  └──────────────┘             │    │
│  └────────────┬──────────────────────────────────────┘   │
└────────────── │ ─────────────────────────────────────────┘
               │ Database queries,
               │ File operations
               ▼
┌───────────────────────────────────────────────────────────┐
│                  DATA LAYER                                │
│  ┌────────────────────┐       ┌─────────────────────┐    │
│  │  Supabase          │       │  Supabase Storage   │    │
│  │  PostgreSQL 15     │       │  (S3-compatible)    │    │
│  │  • receipts        │       │  • PDF files        │    │
│  │  • processed_emails│       │  • Image files      │    │
│  │  • users           │       │  (SHA-256 hashed)   │    │
│  │  • review_candidates│      └─────────────────────┘    │
│  └────────────────────┘                                   │
│                                                            │
│  ┌────────────────────┐       ┌─────────────────────┐    │
│  │  Redis (unused)    │       │  Celery (unused)    │    │
│  │  (Future: cache)   │       │  (Future: async)    │    │
│  └────────────────────┘       └─────────────────────┘    │
└───────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────┐
│               EXTERNAL SERVICES                            │
│  ┌────────────────┐  ┌────────────────┐                  │
│  │  Gmail API     │  │  Tesseract OCR │                  │
│  │  (Inbox sync)  │  │  (Text extract)│                  │
│  └────────────────┘  └────────────────┘                  │
└───────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### Frontend (Next.js 15 + React 19)

**Technology Stack**:
- **Framework**: Next.js 15.1.7 with App Router
- **UI Library**: React 19.0.0
- **Styling**: Tailwind CSS 3.4.17
- **State Management**: React Context (minimal, no Redux/Zustand)
- **HTTP Client**: Native fetch API
- **Auth**: Supabase Auth client (@supabase/supabase-js)

**Directory Structure**:
```
src/frontend/
├── app/                    # Next.js App Router pages
│   ├── login/page.tsx      # Login page
│   ├── signup/page.tsx     # Signup page
│   ├── receipts/
│   │   ├── page.tsx        # Receipt list (main dashboard)
│   │   └── review/page.tsx # Review queue for corrections
│   └── layout.tsx          # Root layout with providers
├── components/             # Reusable UI components (currently minimal)
├── lib/                    # Utilities and configurations
│   └── supabase.ts         # Supabase client initialization
├── public/                 # Static assets
└── .env.local              # Environment variables
```

**Key Pages**:
- `/` → Redirects to `/login` or `/receipts` based on auth
- `/login` → Email/password authentication
- `/signup` → User registration
- `/receipts` → Main dashboard with receipt table, filters, export
- `/receipts/review` → Review queue for uncertain extractions

**Authentication Flow**:
1. User signs up via Supabase Auth (email/password)
2. Frontend stores session in browser (Supabase handles cookies)
3. On each API call, frontend retrieves user ID from session
4. ⚠️ **CRITICAL BUG**: Frontend sends user_id as query param to backend without verification

**Current State**:
- ✅ Functional UI with receipt listing, filtering, export
- ✅ Review queue for correcting low-confidence extractions
- ❌ No component reusability (pages are 300-600 lines)
- ❌ Zero tests (no Jest, no React Testing Library)
- ❌ Poor mobile experience (tables overflow)
- ❌ No loading states or error boundaries

---

### Backend (FastAPI + Python)

**Technology Stack**:
- **Framework**: FastAPI 0.115.6
- **Server**: Uvicorn 0.34.0
- **Database Client**: Supabase Python SDK 2.14.0
- **OCR**: Pytesseract 0.3.13 + Tesseract CLI
- **Image Processing**: Pillow 11.0.0
- **Email**: Google API Python Client 2.158.0
- **Job Queue**: Celery 5.4.0 (configured but unused)
- **Cache**: Redis (configured but unused)

**Layered Architecture**:

```
Backend (src/backend/app/)
├── main.py                          # FastAPI app initialization, CORS, middleware
├── config.py                        # Environment variables, settings
├── routers/                         # HTTP API endpoints (request/response)
│   ├── receipts.py                  # GET/DELETE receipts, list with filters
│   ├── upload.py                    # POST file upload endpoint
│   ├── sync.py                      # POST Gmail inbox sync
│   ├── export.py                    # GET CSV export
│   └── review.py                    # Review queue API (pending, submit, export)
├── services/                        # Business logic layer
│   ├── ingestion.py                 # Receipt processing orchestration
│   ├── parser.py                    # OCR text → structured data extraction
│   ├── ocr.py                       # PDF/image → text extraction (Tesseract)
│   ├── storage.py                   # File upload to Supabase Storage
│   └── email.py                     # Gmail API integration
├── models/                          # Pydantic data models
│   └── receipt.py                   # ReceiptData, ReceiptResponse schemas
├── utils/                           # Helper functions
│   ├── scoring.py                   # Candidate confidence scoring
│   ├── candidates.py                # Candidate data structures
│   └── money.py                     # Currency/amount parsing
├── database/                        # Database schema SQL
│   └── schema.sql                   # Table definitions, RLS policies
├── migrations/                      # Database migrations
│   ├── add_review_columns.sql
│   └── add_user_corrections.sql
└── tests/                           # Test suite (~2,115 lines)
    ├── test_critical_fixes.py       # Core parser regression tests
    ├── test_end_to_end.py           # Full ingestion pipeline
    └── test_ingestion_integration.py
```

**Request Flow** (Upload Endpoint Example):
```
1. POST /upload (file, user_id)
   ↓
2. upload.py router validates file type/size
   ↓
3. IngestionService._process_source()
   ├─→ StorageService.upload() → Supabase Storage
   ├─→ OCRService.extract_text() → Tesseract
   ├─→ ParserService.parse() → Structured data
   ├─→ _check_semantic_duplicate() → Deduplication
   └─→ supabase.table('receipts').insert() → Database
   ↓
4. Return receipt_id + parsed data
```

**Key Services**:

**IngestionService** (`services/ingestion.py`)
- Orchestrates receipt processing pipeline
- Handles file-hash deduplication
- Semantic duplicate detection (vendor+amount+date)
- Calls OCR, parser, storage services
- Creates database records

**ParserService** (`services/parser.py`)
- Extracts vendor, amount, date, currency, tax from OCR text
- Uses regex patterns with confidence scoring
- Captures top 3 candidates per field for review UI
- Applies normalization and heuristics (e.g., person name detection)

**OCRService** (`services/ocr.py`)
- Converts PDF/images to text via Tesseract
- Handles multi-page PDFs
- Pre-processes images (contrast, deskew)

**StorageService** (`services/storage.py`)
- Content-addressed storage (SHA-256 hash as filename)
- Uploads to Supabase private bucket
- Deduplication by file hash

**EmailService** (`services/email.py`)
- Gmail API integration (OAuth 2.0)
- Polls inbox for new receipts
- Downloads attachments
- Marks emails as processed

**Current State**:
- ✅ Clean separation of concerns (routers → services → models)
- ✅ Good test coverage for core logic
- ❌ **CRITICAL**: No authentication/authorization on API
- ❌ No rate limiting
- ❌ No async processing (OCR blocks for 30+ seconds)
- ❌ No error retry logic for external APIs

---

### Database Schema (Supabase PostgreSQL)

**Tables**:

**`receipts`** - Core receipt records
```sql
CREATE TABLE receipts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    vendor TEXT,
    amount NUMERIC(10, 2),
    currency TEXT DEFAULT 'CAD',
    date DATE,
    tax NUMERIC(10, 2),
    confidence NUMERIC(3, 2),
    file_url TEXT,
    file_path TEXT,
    file_hash TEXT,
    source TEXT,  -- 'email' | 'upload' | 'api'
    needs_review BOOLEAN DEFAULT FALSE,
    user_corrections JSONB,  -- Manual corrections for ML training
    corrected_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_receipts_user_id ON receipts(user_id);
CREATE INDEX idx_receipts_date ON receipts(date);
CREATE INDEX idx_receipts_vendor ON receipts(vendor);
CREATE INDEX idx_receipts_needs_review ON receipts(needs_review);
CREATE INDEX idx_receipts_user_corrections ON receipts USING GIN(user_corrections);
```

**`processed_emails`** - Email deduplication tracking
```sql
CREATE TABLE processed_emails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    message_id TEXT NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    receipt_id UUID REFERENCES receipts(id),
    UNIQUE(user_id, message_id)
);

CREATE INDEX idx_processed_emails_user_id ON processed_emails(user_id);
CREATE INDEX idx_processed_emails_message_id ON processed_emails(message_id);
```

**`ingestion_debug.review_candidates`** - Parser candidate data for review UI
```sql
CREATE TABLE ingestion_debug.review_candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    receipt_id UUID NOT NULL REFERENCES receipts(id),
    field_name TEXT NOT NULL,  -- 'vendor' | 'amount' | 'date' | 'currency'
    candidate_value TEXT NOT NULL,
    score NUMERIC(3, 2) NOT NULL,
    pattern_name TEXT,
    candidate_rank INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_review_candidates_receipt_id ON ingestion_debug.review_candidates(receipt_id);
```

**`users`** (Supabase Auth managed)
- Supabase Auth automatically creates `auth.users` table
- Stores email, hashed password, metadata
- No custom user table currently used

**Row-Level Security (RLS)**:
```sql
-- Users can only see their own receipts
CREATE POLICY "Users can view own receipts"
  ON receipts FOR SELECT
  USING (auth.uid() = user_id);

-- Users can only insert receipts for themselves
CREATE POLICY "Users can insert own receipts"
  ON receipts FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can update their own receipts
CREATE POLICY "Users can update own receipts"
  ON receipts FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Users can delete their own receipts
CREATE POLICY "Users can delete own receipts"
  ON receipts FOR DELETE
  USING (auth.uid() = user_id);
```

⚠️ **CRITICAL**: RLS policies defined but **NOT ENFORCED** because backend uses service_role key (bypasses RLS) and doesn't validate user_id from JWT.

---

## Major Data Flows

### Flow 1: Email Ingestion (Automated)

```
┌─────────────┐
│ User's Gmail│
│  Inbox      │
└──────┬──────┘
       │ User forwards receipt → autoexpense@intake.com
       │
       ▼
┌─────────────────────────────────────────┐
│ Gmail API (Polling every X minutes)     │
└──────┬──────────────────────────────────┘
       │ GET /messages?q=is:unread
       │
       ▼
┌──────────────────────────────────────────┐
│ EmailService.sync_inbox()                │
│  • Fetch unread messages                 │
│  • Download PDF/image attachments        │
│  • Check if message_id already processed │
└──────┬───────────────────────────────────┘
       │
       │ For each attachment:
       ▼
┌──────────────────────────────────────────┐
│ IngestionService._process_source()       │
│  1. Compute file hash (SHA-256)          │
│  2. Check if file_hash exists (skip if dup)│
│  3. Upload file to Supabase Storage      │
│  4. Extract text via OCR                 │
│  5. Parse text → structured data         │
│  6. Check semantic duplicate             │
│  7. Insert into receipts table           │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ Database: receipts + processed_emails    │
│ Storage: receipt file saved              │
└──────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ User sees new receipt in dashboard       │
└──────────────────────────────────────────┘
```

**Timing**: Polling interval (currently manual trigger, needs cron job)
**Latency**: 30-60 seconds per receipt (OCR is synchronous)

---

### Flow 2: Manual Upload

```
┌─────────────┐
│ Web Browser │
└──────┬──────┘
       │ User clicks "Upload Receipt"
       │ Selects PDF/image file
       │
       ▼
┌──────────────────────────────────────────┐
│ POST /upload (file, user_id)             │
└──────┬───────────────────────────────────┘
       │
       │ 1. Validate file type (PDF, JPG, PNG)
       │ 2. Validate file size (< 10MB)
       │
       ▼
┌──────────────────────────────────────────┐
│ IngestionService._process_source()       │
│  (Same as email flow above)              │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ Return receipt JSON to frontend          │
│ {                                        │
│   "id": "uuid",                          │
│   "vendor": "Uber",                      │
│   "amount": 15.67,                       │
│   "confidence": 0.85,                    │
│   "needs_review": false                  │
│ }                                        │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ Frontend refreshes receipt list          │
└──────────────────────────────────────────┘
```

**Latency**: 30-60 seconds (synchronous OCR)
**User Experience**: Loading spinner during processing

---

### Flow 3: Review & Correction

```
┌─────────────┐
│ User clicks │
│ "Review     │
│  Queue"     │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ GET /review/pending?user_id=X            │
└──────┬───────────────────────────────────┘
       │
       │ Query: WHERE needs_review = true
       │
       ▼
┌──────────────────────────────────────────┐
│ Return receipts + top 3 candidates       │
│ {                                        │
│   "receipts": [                          │
│     {                                    │
│       "id": "uuid",                      │
│       "vendor": "Jorden Shaw",  ← Wrong │
│       "vendor_candidates": [            │
│         {"value": "Uber", "score": 0.84},│
│         {"value": "Jorden Shaw", "score": 0.3},│
│         {"value": "Anthony's", "score": 0.2}│
│       ]                                  │
│     }                                    │
│   ]                                      │
│ }                                        │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ Review UI shows:                         │
│  • Receipt PDF preview                   │
│  • Radio buttons for top 3 options       │
│  • "Custom" input field                  │
│  • All 5 fields editable                 │
└──────┬───────────────────────────────────┘
       │
       │ User selects "Uber" or types custom
       │ User clicks "Submit"
       │
       ▼
┌──────────────────────────────────────────┐
│ POST /review/submit                      │
│ {                                        │
│   "receipt_id": "uuid",                  │
│   "corrections": {                       │
│     "vendor": {                          │
│       "original": "Jorden Shaw",         │
│       "corrected": "Uber",               │
│       "source": "candidate_1"            │
│     }                                    │
│   }                                      │
│ }                                        │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ UPDATE receipts SET                      │
│   vendor = 'Uber',                       │
│   user_corrections = {...},              │
│   corrected_at = NOW(),                  │
│   needs_review = FALSE                   │
│ WHERE id = 'uuid'                        │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ Frontend shows "Correction saved!"       │
│ Navigate to next receipt in queue        │
└──────────────────────────────────────────┘
```

**ML Training Data Collection**:
- All corrections stored in `user_corrections` JSONB column
- Export via `GET /review/corrections/export` (JSONL format)
- Future: Train model to improve parser accuracy

---

### Flow 4: Export to CSV

```
┌─────────────┐
│ User clicks │
│ "Export CSV"│
└──────┬──────┘
       │
       │ Optional: Apply filters (date range, vendor)
       │
       ▼
┌──────────────────────────────────────────┐
│ GET /export?user_id=X&start_date=...    │
└──────┬───────────────────────────────────┘
       │
       │ Query receipts with filters
       │
       ▼
┌──────────────────────────────────────────┐
│ ExportService.to_csv()                   │
│  • Fetch receipts from database          │
│  • Format as CSV rows                    │
│  • Set headers: Content-Disposition      │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ Download CSV file                        │
│ Columns: Vendor, Amount, Currency, Date, │
│          Tax, Confidence, Source         │
└──────────────────────────────────────────┘
```

**CSV Format**:
```csv
Vendor,Amount,Currency,Date,Tax,Confidence,Source
Uber,15.67,CAD,2026-02-09,2.04,0.85,email
Starbucks,7.89,CAD,2026-02-10,1.03,0.92,upload
```

---

## Security Model (Current State)

### Authentication (Frontend Only)

```
┌─────────────┐
│ User signs  │
│ up/login    │
└──────┬──────┘
       │ POST /auth/signup (Supabase)
       │
       ▼
┌──────────────────────────────────────────┐
│ Supabase Auth                            │
│  • Hashes password (bcrypt)              │
│  • Stores in auth.users table            │
│  • Returns JWT token + refresh token     │
└──────┬───────────────────────────────────┘
       │
       │ Store session in browser
       │ (Supabase manages cookies)
       │
       ▼
┌──────────────────────────────────────────┐
│ Frontend: Supabase client                │
│  • Checks session on page load           │
│  • Redirects to /login if expired        │
│  • Extracts user_id from session         │
└──────┬───────────────────────────────────┘
       │
       │ ⚠️ PROBLEM: Frontend sends user_id
       │             as query param to backend
       │
       ▼
┌──────────────────────────────────────────┐
│ Backend API                              │
│  ❌ NO JWT VERIFICATION                  │
│  ❌ Trusts user_id from client           │
│  ❌ No authentication middleware         │
└──────────────────────────────────────────┘
```

**CRITICAL VULNERABILITY**:
- Any user can impersonate another by changing `user_id` query param
- Example attack:
  ```bash
  # Legitimate request
  GET /receipts?user_id=alice-uuid

  # Attacker changes user_id
  GET /receipts?user_id=bob-uuid
  # ❌ Returns Bob's receipts to attacker!
  ```

### Authorization (Not Implemented)

- ❌ No resource ownership checks
- ❌ No user-to-receipt validation
- ❌ RLS policies exist but bypassed (service_role key)

### Data Protection

**At Rest**:
- ✅ Supabase encrypts database (AES-256)
- ✅ Supabase encrypts storage (AES-256)
- ❌ No field-level encryption for sensitive data

**In Transit**:
- ✅ Supabase uses HTTPS
- ⚠️ Local dev uses HTTP (localhost)
- ❌ No HSTS headers

**Secrets**:
- ❌ Credentials committed to repo (.env files)
- ❌ No secrets manager (AWS Secrets, Vault)
- ❌ No environment variable validation

---

## External Integrations

### Gmail API (OAuth 2.0)

**Setup**:
1. Create Google Cloud project
2. Enable Gmail API
3. Create OAuth 2.0 credentials (client ID + secret)
4. Authorize user's Gmail account (generates refresh token)
5. Store refresh token in backend .env

**Authentication Flow** (Manual - Needs UI):
```
1. User visits Google OAuth consent screen
2. User grants permission to read emails
3. Google returns authorization code
4. Backend exchanges code for access_token + refresh_token
5. Store refresh_token in database (per user)
6. Use refresh_token to get fresh access_token when needed
```

**Current State**:
- ⚠️ Single-user setup (refresh token in .env)
- ❌ No multi-user OAuth flow
- ❌ No OAuth UI in frontend
- ❌ Polling instead of pub/sub webhooks

**API Usage**:
- `GET /users/me/messages` - List emails
- `GET /users/me/messages/{id}` - Get email details
- `GET /users/me/messages/{id}/attachments/{id}` - Download attachment

**Quota**:
- Free tier: 1 billion requests/day (sufficient)
- Rate limit: 250 requests/second per user

---

### Tesseract OCR (Local Binary)

**Deployment**:
- Requires `tesseract` CLI installed on server
- Install via: `apt-get install tesseract-ocr` (Linux)
- Python wrapper: `pytesseract` library

**Processing**:
```python
# OCR text extraction
text = pytesseract.image_to_string(image, lang='eng', config='--psm 6')
```

**Performance**:
- Single-page PDF: ~5-10 seconds
- Multi-page PDF: ~30-60 seconds
- Blocks HTTP request (synchronous)

**Accuracy** (Estimated):
- Clean receipts: 85-95% accuracy
- Faded/crumpled receipts: 60-80% accuracy
- Handwritten receipts: 30-50% accuracy

**Limitations**:
- CPU-intensive (not GPU-accelerated)
- No pre-trained receipt models
- Generic text extraction (not specialized for receipts)

**Future Improvements**:
- Use Google Cloud Vision API (higher accuracy)
- Use AWS Textract (receipt-specialized)
- Pre-process images (deskew, contrast adjustment)

---

### Supabase (Backend-as-a-Service)

**Services Used**:

**1. PostgreSQL Database**
- Tables: receipts, processed_emails, review_candidates
- RLS policies defined
- Extensions: uuid-ossp, pgcrypto

**2. Storage (S3-compatible)**
- Bucket: `receipts-private` (RLS-protected)
- Content-addressed storage (SHA-256)
- File serving via signed URLs

**3. Authentication**
- Email/password authentication
- JWT token generation
- Session management
- ⚠️ Backend doesn't validate JWTs

**API Keys**:
- `SUPABASE_URL`: Public URL (e.g., https://xxx.supabase.co)
- `SUPABASE_ANON_KEY`: Frontend key (RLS-protected)
- `SUPABASE_SERVICE_KEY`: Backend key (bypasses RLS) ⚠️ EXPOSED IN REPO

**Current State**:
- ✅ Free tier (500MB database, 1GB storage)
- ✅ Auto-backups enabled (Supabase managed)
- ❌ No connection pooling configured
- ❌ No query optimization (missing indexes)

---

## Deployment Architecture (Planned)

### Development Environment (Current)

```
┌─────────────┐
│ Developer   │
│ Laptop      │
└──────┬──────┘
       │
       ├─→ Frontend: localhost:3000 (Next.js dev server)
       ├─→ Backend: localhost:8000 (Uvicorn)
       └─→ Database: Supabase Cloud (dev project)
```

### Production Environment (Recommended)

```
┌──────────────────┐
│ Users (Global)   │
└────────┬─────────┘
         │ HTTPS
         ▼
┌────────────────────────────────────────────┐
│ Cloudflare CDN                             │
│  • SSL/TLS termination                     │
│  • DDoS protection                         │
│  • Static asset caching                    │
└────────┬───────────────────────────────────┘
         │
         ├─→ autoexpense.io (Frontend)
         │   ┌───────────────────┐
         │   │ Vercel/Netlify    │
         │   │  • Next.js SSR     │
         │   │  • Edge functions  │
         │   │  • Auto-scaling    │
         │   └───────────────────┘
         │
         └─→ api.autoexpense.io (Backend)
             ┌───────────────────────────┐
             │ Railway/Render            │
             │  • FastAPI containers     │
             │  • Auto-scaling (2-10)    │
             │  • Health checks          │
             └──────┬────────────────────┘
                    │
                    ├─→ Supabase Cloud
                    │   (Database + Storage)
                    │
                    ├─→ Redis Cloud
                    │   (Future: caching)
                    │
                    └─→ Celery Workers
                        (Future: async OCR)

┌────────────────────────────────────────────┐
│ Monitoring & Observability                 │
│  • Sentry (error tracking)                 │
│  • Datadog/Prometheus (metrics)            │
│  • StatusPage.io (status page)             │
└────────────────────────────────────────────┘
```

**Cost Estimate** (Monthly):
- Frontend (Vercel/Netlify): $0 (free tier)
- Backend (Railway/Render): $50-200
- Supabase Pro: $25
- Cloudflare: $0 (free tier)
- Redis Cloud: $0 (free tier) or $10 (starter)
- Monitoring (Sentry + Datadog): $50-150
- **Total**: $125-385/month

---

## Performance Characteristics

### Latency Benchmarks (Current)

| Operation | Latency | Notes |
|-----------|---------|-------|
| Upload + OCR (single page) | 10-15s | Synchronous, blocking |
| Upload + OCR (multi-page) | 30-60s | Tesseract processes sequentially |
| List receipts (100 items) | 200-500ms | Database query + rendering |
| Export CSV (500 receipts) | 1-2s | Database query + CSV generation |
| Gmail sync (10 emails) | 20-30s | Sequential attachment downloads |

### Scalability Limits

**Current Architecture**:
- **Concurrent users**: 10-50 (synchronous OCR bottleneck)
- **Receipts per user**: Unlimited (database scales)
- **Total receipts**: 100,000+ (Supabase free tier limit: 500MB)
- **File storage**: 1GB (Supabase free tier limit)

**Bottlenecks**:
1. **Synchronous OCR** - Blocks HTTP worker threads
2. **No connection pooling** - Database connections exhausted at 20+ concurrent requests
3. **Gmail polling** - Inefficient, can miss emails
4. **No caching** - Repeated queries to database

**Recommended Improvements**:
1. **Async OCR** - Move to Celery background tasks
2. **Connection pooling** - Use pgBouncer or SQLAlchemy pooling
3. **Gmail pub/sub** - Real-time notifications instead of polling
4. **Redis caching** - Cache frequent queries (user receipts, vendor list)
5. **CDN** - Serve receipt files from Cloudflare

---

## Testing Strategy

### Current Test Coverage

**Backend Tests** (~2,115 lines):
- `test_critical_fixes.py` - Parser regression tests (Steam, Paddle, LinkedIn, Uber)
- `test_end_to_end.py` - Full ingestion pipeline (file upload → OCR → database)
- `test_ingestion_integration.py` - Integration tests with real Supabase

**Coverage Areas**:
- ✅ Parser accuracy (vendor, amount, date, currency, tax)
- ✅ Deduplication (file-hash + semantic)
- ✅ Multi-currency handling
- ✅ OCR text extraction
- ⚠️ Limited: Error handling, edge cases

**Missing Tests**:
- ❌ Authentication/authorization tests
- ❌ API endpoint tests (routers)
- ❌ Frontend tests (Jest, React Testing Library)
- ❌ Load tests (concurrent users)
- ❌ Security tests (SQL injection, XSS)

### Recommended Test Strategy

**Unit Tests** (Fast, isolated):
- Parser logic (regex patterns, scoring)
- Utilities (money parsing, date parsing)
- Models (Pydantic validation)

**Integration Tests** (Medium speed, external services):
- Database queries (Supabase client)
- Storage operations (file upload/download)
- OCR extraction (Tesseract)

**End-to-End Tests** (Slow, full pipeline):
- Upload → OCR → Parse → Database
- Email sync → Attachment download → Ingestion
- Review → Correction → ML data export

**Performance Tests** (Load testing):
- 100 concurrent uploads
- 10,000 receipts per user
- 1 million total receipts

---

## Future Architecture Considerations

### Near-term Improvements (Phase 1-2)

1. **Authentication & Authorization**
   - Add JWT verification middleware
   - Validate user ownership on all resources
   - Use RLS policies properly

2. **Async Processing**
   - Move OCR to Celery background tasks
   - Use Redis for job queue
   - Implement webhook callbacks

3. **Monitoring & Observability**
   - Add Sentry for error tracking
   - Add Datadog/Prometheus for metrics
   - Add structured logging (JSON format)

### Medium-term Enhancements (Phase 3-4)

1. **Caching Layer**
   - Redis for frequent queries
   - Cache user receipt lists (invalidate on update)
   - Cache OCR results (content-addressed)

2. **Database Optimization**
   - Add missing indexes (vendor, date, needs_review)
   - Connection pooling (pgBouncer)
   - Query optimization (EXPLAIN ANALYZE)

3. **CDN & File Serving**
   - Cloudflare CDN for static assets
   - Signed URLs for receipt files (time-limited)
   - Lazy loading for images

### Long-term Vision (Phase 5+)

1. **Machine Learning Pipeline**
   - Train custom receipt extraction model
   - Use user corrections as training data
   - Active learning loop (low-confidence → review → improve)

2. **Multi-region Deployment**
   - US-East, US-West, EU, Asia datacenters
   - Geographic routing (latency optimization)
   - Data residency compliance (GDPR)

3. **Microservices (if needed at scale)**
   - Separate OCR service (can scale independently)
   - Separate parser service
   - Separate API gateway
   - Event-driven architecture (Kafka, RabbitMQ)

---

## Appendix: Technology Choices Rationale

### Why FastAPI?
- ✅ Fast (async support, Pydantic validation)
- ✅ Auto-generates OpenAPI docs
- ✅ Type hints for IDE support
- ✅ Easy deployment (ASGI, Docker-friendly)

### Why Next.js?
- ✅ Server-side rendering (SEO)
- ✅ File-based routing (simple)
- ✅ React ecosystem (large community)
- ✅ Vercel deployment (zero-config)

### Why Supabase?
- ✅ PostgreSQL (powerful, reliable)
- ✅ Built-in auth (saves engineering time)
- ✅ RLS policies (security by default)
- ✅ Free tier (cost-effective for MVP)
- ⚠️ Vendor lock-in (can migrate to self-hosted Postgres)

### Why Tesseract?
- ✅ Free and open-source
- ✅ No API costs (vs Google Cloud Vision)
- ✅ Runs locally (no external dependency)
- ❌ Lower accuracy than commercial OCR
- ❌ Slow (CPU-bound)

**Future**: Consider upgrading to Google Cloud Vision or AWS Textract for production (higher accuracy, faster).

---

**Document Owner**: Engineering Team
**Review Cadence**: Quarterly or after major architecture changes
**Last Updated**: 2026-02-10
