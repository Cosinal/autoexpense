# AutoExpense Database Setup

This directory contains SQL migrations for setting up the AutoExpense database schema.

## Quick Start

### 1. Run Migrations in Supabase

Go to your Supabase project → **SQL Editor** and run these files in order:

1. **001_initial_schema.sql** - Creates tables and indexes
2. **002_rls_policies.sql** - Sets up Row Level Security
3. **003_storage_setup.sql** - Creates storage bucket and policies

Or copy and paste all three files in order into a single SQL query.

### 2. Verify Setup

After running the migrations, you should have:

#### Tables
- `public.receipts` - Stores receipt data
- `public.processed_emails` - Tracks processed emails (prevents duplicates)
- `public.users` - Optional user metadata

#### Storage
- `receipts` bucket (private)

#### Security
- RLS enabled on all tables
- Storage policies configured
- Users can only access their own data

---

## Database Schema

### receipts table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to auth.users |
| vendor | TEXT | Merchant name |
| amount | NUMERIC | Total amount |
| currency | TEXT | Currency code (default: USD) |
| date | DATE | Receipt date |
| tax | NUMERIC | Tax amount |
| file_url | TEXT | Supabase storage URL |
| file_hash | TEXT | SHA-256 for deduplication |
| file_name | TEXT | Original filename |
| mime_type | TEXT | File MIME type |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

### processed_emails table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to auth.users |
| provider_message_id | TEXT | Gmail message ID (unique) |
| received_at | TIMESTAMP | Email received time |
| processed_at | TIMESTAMP | Processing time |
| receipt_count | INTEGER | Number of receipts extracted |

---

## Storage Structure

Files are organized by user:

```
receipts/
├── {user_id}/
│   ├── {receipt_id}_invoice.pdf
│   ├── {receipt_id}_receipt.jpg
│   └── ...
```

---

## Row Level Security

All tables have RLS enabled with these policies:

- **SELECT**: Users can view only their own records
- **INSERT**: Users can create records for themselves only
- **UPDATE**: Users can update only their own records
- **DELETE**: Users can delete only their own records

The backend service uses the `service_role` key which bypasses RLS for admin operations.

---

## Testing the Setup

Use the Python test script:

```bash
cd backend
source venv/bin/activate
python test_connection.py
```

Or test directly in Supabase SQL Editor:

```sql
-- Insert a test receipt (replace user_id with a real auth.users id)
INSERT INTO receipts (user_id, vendor, amount, date)
VALUES ('your-user-id-here', 'Test Vendor', 100.00, CURRENT_DATE);

-- Query receipts
SELECT * FROM receipts;

-- Check storage bucket
SELECT * FROM storage.buckets WHERE id = 'receipts';
```

---

## Rollback

To remove all tables and start over:

```sql
-- Drop tables
DROP TABLE IF EXISTS public.receipts CASCADE;
DROP TABLE IF EXISTS public.processed_emails CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;

-- Remove storage bucket
DELETE FROM storage.buckets WHERE id = 'receipts';
```

---

## Next Steps

After database setup is complete:
1. ✓ Test connection from backend
2. → Move to Phase 2: Email Ingestion
3. → Move to Phase 3: OCR & Parsing

See `/documents/build-plans/claude-build-v01.md` for the full build plan.
