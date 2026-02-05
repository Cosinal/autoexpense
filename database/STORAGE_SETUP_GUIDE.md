# Storage Bucket Setup - Quick Guide

## Why UI instead of SQL?

Storage policies require special permissions that aren't available in the SQL Editor. You need to use the Supabase dashboard UI instead.

---

## Quick Steps

### 1. Create the Bucket (2 minutes)

**Navigation**: Storage → New bucket

**Settings**:
```
Name: receipts
Public: OFF ❌
File size limit: 50 MB
```

Click **Create bucket** ✓

---

### 2. Add Policies (5 minutes)

Click on your new `receipts` bucket → **Policies** tab → **New policy**

Create **4 policies** with these settings:

#### Policy #1: Upload
```
Name: Users can upload own receipts
Operation: INSERT
Target roles: authenticated
Definition:
(bucket_id = 'receipts'::text) AND (auth.uid()::text = (storage.foldername(name))[1])
```

#### Policy #2: View
```
Name: Users can view own receipts
Operation: SELECT
Target roles: authenticated
Definition:
(bucket_id = 'receipts'::text) AND (auth.uid()::text = (storage.foldername(name))[1])
```

#### Policy #3: Update
```
Name: Users can update own receipts
Operation: UPDATE
Target roles: authenticated
Definition:
(bucket_id = 'receipts'::text) AND (auth.uid()::text = (storage.foldername(name))[1])
```

#### Policy #4: Delete
```
Name: Users can delete own receipts
Operation: DELETE
Target roles: authenticated
Definition:
(bucket_id = 'receipts'::text) AND (auth.uid()::text = (storage.foldername(name))[1])
```

---

## What These Policies Do

The policy definition `(storage.foldername(name))[1]` extracts the first folder name from the file path.

**Example**:
- File path: `12345-user-id/receipt.pdf`
- Folder name: `12345-user-id`
- Policy checks: Does this match the authenticated user's ID?

This means:
- ✓ User A can access files in `{user_a_id}/`
- ✗ User A **cannot** access files in `{user_b_id}/`

---

## Verify It Worked

Run this from your terminal:

```bash
cd backend
source venv/bin/activate
python verify_db_setup.py
```

Expected output:
```
✓ Testing storage bucket...
  → 'receipts' bucket exists
  → Public: False
```

---

## Troubleshooting

**Can't find "New policy" button?**
- Make sure you clicked on the bucket first
- Go to the Policies tab (not Configuration)

**Policy won't save?**
- Check that you selected the correct operation (INSERT/SELECT/UPDATE/DELETE)
- Make sure "authenticated" is selected under Target roles

**Verification script fails?**
- Double-check the bucket name is exactly `receipts` (lowercase)
- Verify all 4 policies are created

---

## You're Done! ✓

Once verification passes, **Phase 1 is complete**.

Next: **Phase 2 - Email Ingestion**
