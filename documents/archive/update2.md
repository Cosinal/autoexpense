# Phase 2: Email Ingestion - Testing Guide

## Prerequisites

Before testing, you need to:
1. ✓ Complete Phase 1 (database setup)
2. → Set up Gmail API credentials
3. → Configure environment variables

---

## Step 1: Gmail API Setup

Follow the detailed guide: `backend/GMAIL_API_SETUP.md`

**Quick steps**:

1. **Create Google Cloud Project**:
   - Go to https://console.cloud.google.com/
   - Create project "AutoExpense"
   - Enable Gmail API

2. **Get OAuth Credentials**:
   - Create OAuth consent screen (External)
   - Add scope: `gmail.readonly`
   - Add your Gmail as test user
   - Create OAuth Desktop Client credentials
   - Download as `backend/credentials.json`

3. **Generate Refresh Token**:
   ```bash
   cd backend
   source venv/bin/activate
   python get_gmail_token.py
   ```

   This opens a browser for OAuth. Sign in and approve.

4. **Update .env**:
   ```bash
   GMAIL_CLIENT_ID=your-client-id
   GMAIL_CLIENT_SECRET=your-client-secret
   GMAIL_REFRESH_TOKEN=your-refresh-token
   INTAKE_EMAIL=your-gmail@gmail.com
   ```

---

## Step 2: Test Gmail Connection

Verify Gmail API is working:

```bash
cd backend
source venv/bin/activate
python test_email_service.py
```

**Expected output**:
```
✓ Gmail service initialized
✓ Found X recent messages
✓ Found Y messages with attachments
✓ Gmail API connection successful!
```

If this fails, check:
- Gmail API is enabled in Google Cloud Console
- OAuth credentials are correct
- Test user is added to OAuth consent screen

---

## Step 3: Prepare Test Data

Send a test email with an attachment:

1. **Option A**: Forward a real receipt email to your new Gmail
2. **Option B**: Email yourself with a PDF/image attachment

Make sure:
- Email has at least one attachment
- Attachment is PDF, JPG, or PNG
- Email is in the inbox (not spam)

---

## Step 4: Test Email Sync (Python Script)

This is the easiest way to test:

```bash
cd backend
source venv/bin/activate
python test_sync.py
```

**What it does**:
1. Checks Gmail configuration
2. Connects to Gmail API
3. Fetches recent emails with attachments
4. Downloads attachments
5. Uploads to Supabase storage
6. Creates receipt records

**Expected output**:
```
Sync Results
============================================================
Messages checked: 5
Messages processed: 2
Receipts created: 3

✓ No errors
✓ Success! Check Supabase
```

---

## Step 5: Verify Results in Supabase

### Check Storage:
1. Go to Supabase → Storage → `receipts` bucket
2. Look for folder: `00000000-0000-0000-0000-000000000000/`
3. You should see uploaded files

### Check Database:
1. Go to Supabase → Table Editor → `receipts` table
2. You should see new records with:
   - `file_url` populated
   - `file_hash` populated
   - `file_name` showing original filename
   - `vendor`, `amount`, `date` will be NULL (Phase 3 adds parsing)

### Check Processed Emails:
1. Go to `processed_emails` table
2. You should see records with Gmail message IDs

---

## Step 6: Test API Endpoint (Optional)

### Start the backend:
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

### Test with script:
```bash
cd backend
./test_api.sh
```

Or manually:

```bash
# Check sync status
curl http://localhost:8000/sync/status

# Trigger sync
curl -X POST http://localhost:8000/sync \
  -H "Content-Type: application/json" \
  -d '{"user_id":"00000000-0000-0000-0000-000000000000","days_back":7}'
```

---

## Troubleshooting

### "Invalid API key" for Gmail
- Check credentials in .env
- Re-run `get_gmail_token.py`
- Make sure refresh token is complete (long string)

### No messages found
- Make sure emails have attachments
- Check that emails aren't older than 7 days
- Try `days_back: 30` for older emails

### Files not uploading to Supabase
- Verify storage bucket exists
- Check storage policies are set up
- Verify `SUPABASE_SERVICE_KEY` in .env

### "Invalid credentials" for Supabase
- Re-check Supabase keys in .env
- Make sure using service_role key, not anon key
- Verify keys are complete (very long JWT tokens)

### Receipts table insert fails
- Check that Phase 1 migrations ran successfully
- Verify user_id references a valid auth.users record
- For testing, you can temporarily disable the foreign key

---

## Success Criteria

Phase 2 is complete when:

✓ Gmail API connects successfully
✓ Emails with attachments are fetched
✓ Files upload to Supabase storage
✓ Receipt records created in database
✓ Duplicate emails are skipped

---

## Next: Phase 3

Once Phase 2 works, move to **Phase 3: OCR & Parsing**:
- Extract text from PDFs and images
- Parse vendor, amount, date, currency
- Update receipt records with parsed data

See `/documents/build-plans/claude-build-v01.md` for details.
