# AutoExpense Backend

FastAPI backend for AutoExpense receipt processing.

## Setup

1. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. Run development server:
```bash
uvicorn app.main:app --reload --port 8000
```

Or use the run script:
```bash
./scripts/run.sh
```

## Project Structure

```
src/backend/
├── app/
│   ├── main.py          # FastAPI app entry point
│   ├── config.py        # Configuration & settings
│   ├── models/          # Pydantic models
│   ├── routers/         # API endpoints
│   ├── services/        # Business logic
│   │   ├── email.py     # Email ingestion
│   │   ├── ocr.py       # OCR processing
│   │   └── parser.py    # Receipt parsing
│   └── utils/           # Helper functions
├── documentation/       # Documentation & guides
│   └── archive/        # Archived analysis
├── scripts/            # Utility & setup scripts
├── tests/              # Test suite
├── requirements.txt    # Python dependencies
└── .env                # Environment variables
```

## API Endpoints

- `GET /` - API info
- `GET /health` - Health check
- `GET /receipts` - List receipts
- `POST /sync` - Trigger email sync
- `GET /export/csv` - Export CSV

## Dependencies

- FastAPI - Web framework
- Supabase - Database & storage
- Tesseract - OCR engine
- Gmail API - Email ingestion
