# AutoExpense – MVP Build Plan

## Goal

Ship a working MVP that supports:

Forward receipt → OCR + parse → store → export CSV

No bank data. No matching. No inbox access.

---

## Tech Stack

- Backend: Python (FastAPI)
- Frontend: Next.js
- Database: Supabase (Postgres)
- Storage: Supabase Storage
- OCR: Tesseract (local)
- Email Intake: Gmail (polling)

---

## MVP Definition

MVP is complete when:

- User can forward receipts to intake email
- System ingests and processes receipts
- Receipts appear in dashboard
- User can export monthly CSV

---

## Phase 0 — Setup (Day 1)

### Tasks
- [ ] Create GitHub repo
- [ ] Set up Python venv
- [ ] Initialize FastAPI project
- [ ] Create Next.js app
- [ ] Configure .env files
- [ ] Connect Supabase project

### Deliverable
Local dev environment running.

---

## Phase 1 — Database & Storage (Day 1)

### Tables

#### receipts
- id (uuid)
- user_id
- vendor
- amount
- currency
- date
- file_url
- file_hash
- created_at

#### receipt_files (optional)
- id
- receipt_id
- file_url
- mime_type

### Storage
- Bucket: `receipts`
- Private access
- RLS enabled

### Tasks
- [ ] Create tables
- [ ] Configure RLS
- [ ] Create storage bucket

### Deliverable
DB + storage ready.

---

## Phase 2 — Email Ingestion (Day 2)

### Tasks
- [ ] Create intake Gmail account
- [ ] Enable Gmail API
- [ ] Implement polling worker (5 min interval)
- [ ] Track processed message IDs
- [ ] Download attachments + HTML receipts
- [ ] Upload files to storage

### Deliverable
Emails → files in storage.

---

## Phase 3 — OCR & Parsing (Day 3)

### Tasks
- [ ] Install Tesseract
- [ ] Implement PDF text extraction
- [ ] Implement image OCR
- [ ] Normalize text
- [ ] Build basic parsers:
  - vendor
  - amount
  - date
  - currency
- [ ] Save parsed data to DB

### Deliverable
Files → structured receipt records.

---

## Phase 4 — Backend API (Day 3–4)

### Endpoints

#### GET /receipts
Returns user receipts

#### POST /sync
Triggers email polling

#### GET /export/csv
Exports monthly CSV

### Tasks
- [ ] Implement auth middleware
- [ ] Build receipts endpoint
- [ ] Build sync endpoint
- [ ] Build export endpoint

### Deliverable
Working backend API.

---

## Phase 5 — Frontend Dashboard (Day 4–5)

### Pages

#### /login
Supabase auth

#### /receipts
- Table view
- Month filter
- Sync button

#### /export
- Export CSV button

### Tasks
- [ ] Configure Supabase auth
- [ ] Build receipts table
- [ ] Implement filters
- [ ] Connect export endpoint

### Deliverable
Usable dashboard.

---

## Phase 6 — Export System (Day 5)

### CSV Format

Columns:
- date
- vendor
- amount
- currency
- file_url

### Tasks
- [ ] Implement CSV generator
- [ ] Handle date filtering
- [ ] Test large exports

### Deliverable
Reliable CSV downloads.

---

## Phase 7 — Hardening (Day 6)

### Tasks
- [ ] File type validation
- [ ] Deduplication (hash)
- [ ] Error logging
- [ ] Retry failed jobs
- [ ] Basic rate limiting

### Deliverable
Stable system.

---

## Phase 8 — Deployment (Day 7)

### Targets
- Backend: Fly.io / Render
- Frontend: Vercel
- Storage: Supabase

### Tasks
- [ ] Deploy backend
- [ ] Deploy frontend
- [ ] Configure env vars
- [ ] Test prod pipeline

### Deliverable
Live MVP.

---

## Phase 9 — Pilot (Week 2+)

### Tasks
- [ ] Onboard first user
- [ ] Monitor ingestion
- [ ] Fix parsing issues
- [ ] Improve UX
- [ ] Gather feedback

### Deliverable
Validated workflow.

---

## Success Criteria

MVP is successful if:

- User forwards receipts weekly
- Reports generated in <5 min
- Manual work reduced by ≥50%
- User willing to pay

---

## Out of Scope (V1)

- Bank feeds
- Matching
- Categorization
- Team features
- Mobile app
- Inbox access

---

## Upgrade Path (Post-MVP)

- Email OAuth
- Plaid/Flinks
- Auto-matching
- Policy engine
- Chat UI

---

## North Star

Build the simplest system that makes expense reporting painless.

Everything else is secondary.
