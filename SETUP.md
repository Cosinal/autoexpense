# AutoExpense Setup Guide

## Phase 0: Local Development Environment

### Prerequisites

- Python 3.9+
- Node.js 18+
- Tesseract OCR
- Git
- Supabase account

---

## 1. Install Tesseract OCR

### macOS
```bash
brew install tesseract
```

### Ubuntu/Debian
```bash
sudo apt-get install tesseract-ocr
```

### Verify installation
```bash
tesseract --version
```

---

## 2. Backend Setup

### Install Python dependencies
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configure environment
```bash
# Edit backend/.env with your credentials
# You'll need Supabase credentials from Step 4
```

### Test the backend
```bash
# Start the server
./run.sh
# or
uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000 - you should see API info.

---

## 3. Frontend Setup

### Install Node dependencies
```bash
cd frontend
npm install
```

### Configure environment
```bash
# Edit frontend/.env.local with your credentials
# You'll need Supabase credentials from Step 4
```

### Test the frontend
```bash
npm run dev
```

Visit http://localhost:3000 - you should see the AutoExpense home page.

---

## 4. Supabase Setup

### Create a project
1. Go to https://supabase.com
2. Click "New Project"
3. Choose a name (e.g., "autoexpense")
4. Choose a database password
5. Select a region
6. Wait for project to initialize

### Get your credentials
1. Go to Project Settings → API
2. Copy:
   - Project URL → `SUPABASE_URL`
   - `anon` `public` key → `SUPABASE_KEY`
   - `service_role` key → `SUPABASE_SERVICE_KEY`

### Update .env files
```bash
# backend/.env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJxxx...
SUPABASE_SERVICE_KEY=eyJxxx...

# frontend/.env.local
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJxxx...
```

### Test the connection
```bash
cd backend
source venv/bin/activate
python test_connection.py
```

---

## 5. Gmail API Setup (for later)

You'll need this for Phase 2 (Email Ingestion). For now, you can skip this.

1. Go to Google Cloud Console
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Download credentials and get refresh token
6. Update `GMAIL_*` variables in backend/.env

---

## Verification Checklist

- [ ] Tesseract installed and working
- [ ] Python backend running at http://localhost:8000
- [ ] Frontend running at http://localhost:3000
- [ ] Supabase project created
- [ ] Environment variables configured
- [ ] Supabase connection test passes

---

## Next Steps

Once your local dev environment is running, proceed to:

**Phase 1**: Database & Storage setup
- Create database tables
- Configure RLS policies
- Set up storage bucket

See `/documents/build-plans/claude-build-v01.md` for the full plan.

---

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (needs 3.9+)
- Activate virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`

### Frontend won't start
- Check Node version: `node --version` (needs 18+)
- Clear cache: `rm -rf .next node_modules && npm install`

### Supabase connection fails
- Verify credentials in .env files
- Check that Supabase project is active
- Ensure you're using the service_role key for backend

### Tesseract not found
- Verify installation: `which tesseract`
- Update `TESSERACT_CMD` in backend/.env with the correct path
