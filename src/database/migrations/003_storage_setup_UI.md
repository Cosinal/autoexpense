# Storage Bucket Setup (UI Method)

Since you can't create storage policies via SQL directly, follow these steps in the Supabase dashboard:

## Step 1: Create Storage Bucket

1. Go to **Storage** in the left sidebar
2. Click **New bucket**
3. Configure:
   - **Name**: `receipts`
   - **Public bucket**: OFF (unchecked)
   - **File size limit**: 50 MB (or your preference)
   - **Allowed MIME types**: Leave empty (allow all) or specify:
     - `application/pdf`
     - `image/jpeg`
     - `image/png`
     - `image/jpg`
4. Click **Create bucket**

## Step 2: Configure Storage Policies

1. Click on the `receipts` bucket you just created
2. Go to the **Policies** tab
3. Click **New policy**

### Policy 1: Users can upload their own files

- **Policy name**: `Users can upload own receipts`
- **Allowed operation**: `INSERT`
- **Target roles**: `authenticated`
- **Policy definition**:
  ```sql
  (bucket_id = 'receipts'::text) AND
  (auth.uid()::text = (storage.foldername(name))[1])
  ```
- Click **Review** → **Save policy**

### Policy 2: Users can view their own files

- Click **New policy** again
- **Policy name**: `Users can view own receipts`
- **Allowed operation**: `SELECT`
- **Target roles**: `authenticated`
- **Policy definition**:
  ```sql
  (bucket_id = 'receipts'::text) AND
  (auth.uid()::text = (storage.foldername(name))[1])
  ```
- Click **Review** → **Save policy**

### Policy 3: Users can update their own files

- Click **New policy** again
- **Policy name**: `Users can update own receipts`
- **Allowed operation**: `UPDATE`
- **Target roles**: `authenticated`
- **Policy definition**:
  ```sql
  (bucket_id = 'receipts'::text) AND
  (auth.uid()::text = (storage.foldername(name))[1])
  ```
- Click **Review** → **Save policy**

### Policy 4: Users can delete their own files

- Click **New policy** again
- **Policy name**: `Users can delete own receipts`
- **Allowed operation**: `DELETE`
- **Target roles**: `authenticated`
- **Policy definition**:
  ```sql
  (bucket_id = 'receipts'::text) AND
  (auth.uid()::text = (storage.foldername(name))[1])
  ```
- Click **Review** → **Save policy**

## Step 3: Verify Storage Setup

After creating the bucket and policies, run the verification script:

```bash
cd backend
source venv/bin/activate
python verify_db_setup.py
```

You should see:
```
✓ Testing storage bucket...
  → 'receipts' bucket exists
  → Public: False
```

## Storage Structure

Files will be organized like this:
```
receipts/
  └── {user_id}/
      ├── {receipt_id}_invoice.pdf
      ├── {receipt_id}_receipt.jpg
      └── ...
```

The policies ensure each user can only access files in their own folder.

---

## Alternative: Quick Policy Setup

If you prefer a faster approach, Supabase has a **Use a template** option:

1. When creating a new policy, click **Use a template**
2. Select **Allow individual user access to a folder**
3. Modify the policy to match the bucket name `receipts`
4. Repeat for INSERT, SELECT, UPDATE, and DELETE operations
