# Phase 1: Database & Storage Setup Instructions

Follow these steps to set up your AutoExpense database and storage.

## Step 1: Access Supabase SQL Editor

1. Go to your Supabase project: https://supabase.com/dashboard
2. Select your project (xhmjuarbzdpeilhgbijz)
3. Click on **SQL Editor** in the left sidebar
4. Click **New query**

## Step 2: Run Migrations

Copy and paste each SQL file in order, then click **Run** after each one:

### Migration 1: Initial Schema

Open `database/migrations/001_initial_schema.sql` and copy all contents.

Paste into Supabase SQL Editor and click **Run**.

This creates:
- ✓ `receipts` table
- ✓ `processed_emails` table
- ✓ `users` table (optional)
- ✓ Indexes for performance
- ✓ Triggers for updated_at timestamps

### Migration 2: Row Level Security

Open `database/migrations/002_rls_policies.sql` and copy all contents.

Paste into Supabase SQL Editor and click **Run**.

This sets up:
- ✓ RLS policies for all tables
- ✓ User permissions
- ✓ Service role access

### Migration 3: Storage Bucket (UI Method)

**Note**: Storage policies must be created through the Supabase dashboard UI, not SQL.

Follow the instructions in `database/migrations/003_storage_setup_UI.md`:

1. Go to **Storage** → Create `receipts` bucket (private)
2. Add 4 policies for INSERT, SELECT, UPDATE, DELETE operations
3. Each policy restricts users to their own folder

This creates:
- ✓ `receipts` storage bucket
- ✓ Storage access policies
- ✓ User folder structure

## Step 3: Verify Setup

Run the verification script from your terminal:

```bash
cd backend
source venv/bin/activate
python verify_db_setup.py
```

You should see:
```
============================================================
AutoExpense Database Setup Verification
============================================================

✓ Testing receipts table...
  → receipts table accessible (found 0 records)

✓ Testing processed_emails table...
  → processed_emails table accessible (found 0 records)

✓ Testing storage bucket...
  → 'receipts' bucket exists
  → Public: False

✓ Checking database schema...
  → RLS is active (expected - queries require authentication)

============================================================
✓ Database setup verification complete!
============================================================
```

## Step 4: Verify in Supabase Dashboard

### Check Tables
1. Go to **Table Editor** in Supabase dashboard
2. You should see:
   - `receipts`
   - `processed_emails`
   - `users`

### Check Storage
1. Go to **Storage** in Supabase dashboard
2. You should see the `receipts` bucket
3. It should be marked as **Private**

## Troubleshooting

### Error: "relation does not exist"
- Make sure you ran migration 001 first
- Check that you're in the correct Supabase project

### Error: "permission denied"
- This is expected when RLS is active
- The backend will use the service_role key to bypass RLS

### Tables created but verification fails
- Check your `.env` file has correct credentials
- Ensure you're using the service_role key, not anon key

### Storage bucket not found
- Make sure you ran migration 003
- Check the Storage dashboard manually

## Next Steps

Once verification passes:

✓ **Phase 1 Complete!**

Ready for **Phase 2: Email Ingestion**
- Set up Gmail API
- Implement email polling
- Extract attachments
- Upload files to storage

See `/documents/build-plans/claude-build-v01.md` for details.
