# Quick Demo Setup (5 Minutes)

## 1. Start Both Servers

### Terminal 1 - Backend
```bash
cd /Users/jordanshaw/Desktop/expense-reporting/src/backend

# Start the FastAPI server
uvicorn app.main:app --reload --port 8000
```

### Terminal 2 - Frontend
```bash
cd /Users/jordanshaw/Desktop/expense-reporting/src/frontend

# Start the Next.js app
npm run dev
```

Keep both terminals open - you'll see live request logs.

## 2. Verify Everything is Running

Open a NEW terminal:

```bash
# Check backend
curl http://localhost:8000/health
# Should return: {"status": "healthy"}

# Check frontend (open in browser)
# http://localhost:3000
```

## 3. Install Dependencies (if needed)

If PDFs fail to upload, install poppler:

```bash
brew install poppler
# Then restart the backend server
```

## 4. Open the Demo

**Primary Demo URL:**
- Frontend Dashboard: http://localhost:3000

**Supporting URLs:**
- Backend API Docs: http://localhost:8000/docs
- Backend Health: http://localhost:8000/health

## 5. Demo Flow (10 minutes)

1. **Show Landing Page** (http://localhost:3000)
   - Value proposition
   - Key features

2. **Login**
   - Authenticate with Supabase

3. **Receipt Dashboard**
   - Show existing receipts
   - Demonstrate filters (vendor, date, currency)

4. **Manual Sync**
   - Click "Sync Email" button
   - Shows email ingestion in action

5. **Upload Receipt** (via API docs if no frontend upload)
   - Open: http://localhost:8000/docs
   - Upload PSA_Canada.pdf or GeoGuessr.pdf
   - Show parsed response

6. **View Receipt Details**
   - Click on a receipt
   - Show confidence scores
   - Show debug metadata

7. **Export to CSV**
   - Demonstrate export functionality

## Quick Troubleshooting

**Backend won't start?**
```bash
# Kill any existing process
lsof -ti:8000 | xargs kill -9

# Check .env file exists
ls -la .env

# Try again
uvicorn app.main:app --reload --port 8000
```

**Frontend won't start?**
```bash
cd /Users/jordanshaw/Desktop/expense-reporting/src/frontend

# Reinstall dependencies
npm install

# Try again
npm run dev
```

**PDF upload returns error?**
```bash
# Install poppler (required for PDF processing)
brew install poppler

# Restart backend server
```

**Frontend shows no receipts?**
- Make sure you're logged in
- Check backend is running (http://localhost:8000/health)
- Open browser console for errors
- Verify Supabase credentials in both .env files

## Demo Sample Files

Located in: `backend/documentation/failed_receipts/`

**Available PDFs:**
- `PSA_Canada.pdf` - Complex receipt with CAD currency
- `GeoGuessr.pdf` - Payment processor detection case

**Available TXT (for parser testing):**
- `email_19c33910.txt` - Sephora with multi-tax (GST + HST)
- `email_19c33917.txt` - Urban Outfitters order summary
- `PSA_Canada.txt` - PSA Canada text version

---

## Full Demo Guide

For detailed talking points and demo script, see: **FRONTEND_DEMO_GUIDE.md**

---

You're ready to demo! 🚀

**Key URLs:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
