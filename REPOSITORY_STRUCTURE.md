# Repository Structure

This document describes the organized structure of the AutoExpense repository.

## Directory Overview

```
expense-reporting/
├── src/                          # Source code (main application code)
│   ├── backend/                  # Backend application
│   │   ├── app/                 # Core application code
│   │   │   ├── models/          # Data models
│   │   │   ├── routers/         # API endpoints
│   │   │   ├── services/        # Business logic
│   │   │   └── utils/           # Helper functions
│   │   ├── documentation/       # Backend documentation
│   │   │   ├── archive/        # Archived docs
│   │   │   └── failed_receipts/ # Test receipts
│   │   ├── scripts/            # Utility scripts
│   │   ├── tests/              # Test suite
│   │   ├── requirements.txt    # Python dependencies
│   │   ├── credentials.json    # Gmail API credentials
│   │   └── token.pickle        # Gmail auth token
│   │
│   ├── frontend/                # Frontend application
│   │   ├── app/                # Next.js app directory
│   │   ├── lib/                # Shared utilities
│   │   ├── documentation/      # Frontend documentation
│   │   │   └── archive/       # Archived docs
│   │   ├── scripts/           # Build/utility scripts
│   │   ├── tests/             # Frontend tests
│   │   ├── package.json       # Node dependencies
│   │   └── next.config.ts     # Next.js config
│   │
│   └── database/               # Database management
│       ├── migrations/         # SQL migration files
│       └── *.md               # Database setup guides
│
├── documents/                   # Project documentation
│   ├── build-plans/            # Development plans
│   └── archive/               # Archived project docs
│
├── .gitignore                  # Git ignore rules
├── README.md                   # Project overview
├── SETUP.md                    # Setup instructions
└── REPOSITORY_STRUCTURE.md     # This file
```

## Key Principles

### 1. Separation of Concerns
- **src/** contains all source code
- **documents/** contains project-level documentation
- Each major component (backend/frontend/database) is self-contained

### 2. Documentation Organization
- Each component has its own `documentation/` folder
- Active documentation in main folder
- Historical/archived docs in `documentation/archive/`

### 3. Scripts Organization
- Utility scripts in `scripts/` folder
- Test scripts in `tests/` folder
- Clear separation between production code and tooling

### 4. Test Organization
- All tests in dedicated `tests/` folder
- Test files prefixed with `test_`
- Easy to run entire test suite

## Working with the New Structure

### Backend Development

```bash
# Navigate to backend
cd src/backend

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8000

# Run tests
python tests/test_receipt_batch.py

# Run utility scripts
python scripts/verify_db_setup.py
```

### Frontend Development

```bash
# Navigate to frontend
cd src/frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

### Database Management

```bash
# Navigate to database
cd src/database

# Apply migrations (via Supabase dashboard)
# See SETUP_INSTRUCTIONS.md for details
```

## Benefits of This Structure

1. **Clear Organization**: Easy to find files based on their purpose
2. **Scalability**: Easy to add new components or documentation
3. **Professional**: Industry-standard structure
4. **Maintainability**: Separated concerns make debugging easier
5. **Team-Friendly**: New developers can quickly understand the project

## Migration Notes

All files have been moved from the old flat structure to this organized hierarchy. Import paths remain unchanged as the Python module structure (app.services.parser) stays the same.
