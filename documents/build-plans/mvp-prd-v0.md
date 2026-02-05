# AutoExpense – MVP PRD (Forward-to-Vault)

## 1. Overview

AutoExpense is a privacy-first expense receipt vault for executives.  
Users forward digital receipts to a dedicated email address. The system ingests, parses, stores, and exports them in accountant-ready format.

V1 focuses only on receipt collection and organization.

---

## 2. Target User

- Executive / professional
- Uses multiple cards
- Receives most receipts digitally
- Privacy-sensitive
- Manual expense workflow

Pilot: Single user.

---

## 3. Problem

Users waste time:
- Searching for receipts
- Downloading files manually
- Organizing monthly reports
- Rebuilding lost records

Existing tools require inbox access or manual uploads.

---

## 4. MVP Scope

### Included
- Receipt intake via email forwarding
- Attachment and HTML extraction
- OCR + rule-based parsing
- Secure storage
- Web dashboard
- CSV export
- ZIP bundle export (optional)

### Excluded
- Bank integrations
- Transaction matching
- Categorization
- Policy rules
- Mobile app
- Team features
- Inbox access

---

## 5. User Flow

1. User forwards receipt to intake email
2. System ingests email
3. Attachments extracted
4. OCR + parsing executed
5. Receipt stored securely
6. User downloads monthly export

---

## 6. Core Features

### Email Intake
- Accept forwarded emails
- Support PDF/JPG/PNG/HTML
- Process each message once

### Processing
- OCR for image-based files
- Extract:
  - Vendor
  - Amount
  - Date
  - Currency
  - Tax (if present)

### Storage
- Encrypted user folders
- Original files preserved
- Deduplication via file hash

### Dashboard
- Receipt list
- Date/vendor search
- Manual sync
- Download files

### Export
- CSV summary
- ZIP of originals (optional)

---

## 7. Technical Architecture

- Email: Gmail API / Inbound parse
- Backend: Node.js / Python + n8n
- Storage: Supabase / S3
- OCR: Tesseract / Cloud OCR (opt-in)
- Parsing: Regex + rules

---

## 8. Data Model (Simplified)

### User
- id
- email
- created_at

### Email
- id
- provider_message_id
- user_id
- received_at

### Receipt
- id
- user_id
- email_id
- vendor
- amount
- currency
- date
- tax
- file_url
- file_hash
- created_at

---

## 9. Privacy & Security

- No inbox access
- User-initiated forwarding only
- No data resale
- No model training
- Encrypted storage

---

## 10. Success Metrics

- ≥80% receipt capture rate
- ≥50% reduction in reporting time
- Monthly active usage
- Willingness to pay

---

## 11. Risks

| Risk | Mitigation |
|------|------------|
| User forgets to forward | Reminders |
| OCR errors | Manual review |
| Low adoption | Concierge onboarding |
| Scope creep | Strict MVP limits |

---

## 12. Roadmap

### V1 (MVP)
- Forward → Store → Export

### V2
- Email OAuth
- Bank feeds
- Auto-matching

---

## 13. MVP Goal

Validate that users will consistently forward receipts if storage and export are effortless.
