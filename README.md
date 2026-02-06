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
├── src/
│   ├── backend/           # Python FastAPI backend
│   │   ├── app/          # Core application code
│   │   ├── documentation/ # Backend docs & archives
│   │   ├── scripts/      # Utility & setup scripts
│   │   └── tests/        # Test suite
│   ├── frontend/          # Next.js frontend
│   │   ├── app/          # Next.js app directory
│   │   ├── documentation/ # Frontend docs
│   │   ├── scripts/      # Build & utility scripts
│   │   └── tests/        # Frontend tests
│   └── database/          # Database migrations & setup
│       └── migrations/    # SQL migration files
└── documents/             # Project documentation
    ├── build-plans/       # Development plans
    └── archive/           # Archived docs
```

## Getting Started

See individual README files in `/src/backend` and `/src/frontend` directories for setup instructions.

## MVP Features

- Receipt intake via email forwarding
- OCR + rule-based parsing
- Secure storage
- Web dashboard
- CSV export

## Documentation

See `/documents/build-plans/` for detailed build plans and PRD.
