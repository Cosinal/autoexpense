# AutoExpense – Phase 1 Roadmap

## Goal

Build a privacy-first receipt intake system that supports:

- Email attachments  
- Email-body receipts (Uber, flights, etc.)  
- Photo uploads  
- Bulk receipt dumps  
- Clean CSV export  

---

## Core Principle

All inputs follow the same pipeline:

INPUT → OCR / Parse → Store → Export

No branching after intake.

---

## Supported Inputs (V1)

### 1. Email Attachments
- PDF / JPG / PNG
- Multiple attachments per email
- One attachment = one receipt

### 2. Email as Receipt
- HTML-only or text-only emails
- (Uber, Amazon, Airbnb, airlines)
- Extract and normalize body

### 3. Photo Upload
- Web upload
- Multi-select supported
- Mobile email-to-intake supported

### 4. Bulk Upload
- Multiple files in one email
- Treated as separate receipts

---

## Intake Logic

On email receive:

IF attachments exist:
  process attachments  
ELSE:
  process email body as receipt  

Uploads bypass email and enter the same pipeline.

---

## Processing Pipeline

1. Normalize input  
2. Convert to image/PDF if needed  
3. OCR (Tesseract)  
4. Parse fields  
5. Store originals + metadata  
6. Index for export  

Parsed fields:

- vendor  
- amount  
- date  
- currency  
- tax (optional)  

---

## Data Abstraction

All inputs are stored as standardized documents.

### InputDocument

InputDocument:
- source_type: email_attachment | email_body | upload  
- raw_content: string | binary  
- file_type: pdf | jpg | png | html | text  
- user_id: uuid  

---

## Phase 1 User Flow

1. User forwards receipt or uploads photo  
2. System processes automatically  
3. Receipts appear in dashboard  
4. User exports monthly CSV  

No setup beyond saving intake email.

---

## MVP Features

### Included
- Attachment handling  
- HTML receipt parsing  
- Photo uploads  
- Bulk processing  
- Secure storage  
- Receipt dashboard  
- CSV export  

### Excluded
- Bank feeds  
- Matching  
- Categorization  
- Policies  
- Teams  
- Mobile app  

---

## Phase 1 Milestones

### Milestone 1: Intake
- Email and uploads working

### Milestone 2: Processing
- OCR and parsing reliable

### Milestone 3: UX
- Dashboard usable
- Export functional

### Milestone 4: Pilot
- First user onboarded
- Monthly workflow validated

---

## Success Criteria

Phase 1 is successful if:

- ≥80% receipts captured  
- CSV usable by accountant  
- User prefers this over manual download  

---

## Future Upgrades (Post-Phase 1)

- AI transaction summaries  
- Bank feeds  
- Auto-matching  
- Policy engine  
- Accountant integrations  

---

## North Star

Make expense reporting invisible.

Thursday February 5th