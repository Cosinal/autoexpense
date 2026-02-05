# AutoExpense

Privacy-first expense receipt vault for executives.

## Overview

AutoExpense allows users to forward digital receipts to a dedicated email address. The system ingests, parses, stores, and exports them in accountant-ready format.

## Tech Stack

- **Backend**: Python (FastAPI)
- **Frontend**: Next.js
- **Database**: Supabase (Postgres)
- **Storage**: Supabase Storage
- **OCR**: Tesseract (local)
- **Email**: Gmail API (polling)

## Project Structure

```
expense-reporting/
├── backend/          # Python FastAPI backend
├── frontend/         # Next.js frontend
├── documents/        # Project documentation
└── src/             # Shared utilities
```

## Getting Started

See individual README files in `/backend` and `/frontend` directories for setup instructions.

## MVP Features

- Receipt intake via email forwarding
- OCR + rule-based parsing
- Secure storage
- Web dashboard
- CSV export

## Documentation

See `/documents/build-plans/` for detailed build plans and PRD.
