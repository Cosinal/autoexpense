.
├── .claude
│   └── settings.local.json
├── .gitignore
├── README.md
├── REPOSITORY_STRUCTURE.md
├── SETUP.md
├── TREE.md
├── backend
│   └── failed_receipts
│       ├── GeoGuessr.pdf
│       ├── PSA_Canada.pdf
│       ├── email_19c33910.txt
│       ├── email_19c33917.txt
│       └── email_19c3391e.txt
├── documents
│   ├── archive
│   │   ├── update0.md
│   │   ├── update1.md
│   │   └── update2.md
│   └── build-plans
│       ├── phase-1-implementation-plan.md
│       └── roadmap-openai.md
└── src
    ├── backend
    │   ├── .env
    │   ├── .env.example
    │   ├── .gitignore
    │   ├── TEST_RESULTS.md
    │   ├── app
    │   │   ├── __init__.py
    │   │   ├── config.py
    │   │   ├── main.py
    │   │   ├── models
    │   │   │   ├── __init__.py
    │   │   │   └── receipt.py
    │   │   ├── routers
    │   │   │   ├── __init__.py
    │   │   │   ├── export.py
    │   │   │   ├── receipts.py
    │   │   │   ├── sync.py
    │   │   │   └── upload.py
    │   │   ├── services
    │   │   │   ├── __init__.py
    │   │   │   ├── email.py
    │   │   │   ├── ingestion.py
    │   │   │   ├── ocr.py
    │   │   │   ├── parser.py
    │   │   │   └── storage.py
    │   │   └── utils
    │   │       ├── __init__.py
    │   │       └── supabase.py
    │   ├── credentials.json
    │   ├── documentation
    │   │   ├── ANALYSIS_SUMMARY.md
    │   │   ├── BEFORE_AFTER_COMPARISON.md
    │   │   ├── GMAIL_API_SETUP.md
    │   │   ├── PARSER_FAILURE_ANALYSIS.md
    │   │   ├── PARSER_FIXES_QUICK_REFERENCE.md
    │   │   ├── PARSER_IMPROVEMENT_RECOMMENDATIONS.md
    │   │   ├── README.md
    │   │   ├── VISUAL_PATTERN_EXAMPLES.md
    │   │   ├── archive
    │   │   │   └── ANALYSIS_SUMMARY.txt
    │   │   └── failed_receipts
    │   │       ├── GeoGuessr.pdf
    │   │       ├── GeoGuessr.txt
    │   │       ├── PSA_Canada.pdf
    │   │       ├── PSA_Canada.txt
    │   │       ├── email_19c33910.txt
    │   │       ├── email_19c33917.txt
    │   │       └── email_19c3391e.txt
    │   ├── migrations
    │   │   └── 001_ingestion_schema.sql
    │   ├── new_receipts
    │   ├── requirements.txt
    │   ├── scripts
    │   │   ├── README.md
    │   │   ├── analyze_receipts.py
    │   │   ├── check_bucket_config.py
    │   │   ├── clear_and_resync.py
    │   │   ├── create_test_user.py
    │   │   ├── debug_receipt.py
    │   │   ├── detailed_analysis.py
    │   │   ├── download_failed_receipts.py
    │   │   ├── extract_pdf_text.py
    │   │   ├── force_reprocess.py
    │   │   ├── get_gmail_token.py
    │   │   ├── list_storage_files.py
    │   │   ├── run.sh
    │   │   ├── setup_storage_bucket.py
    │   │   └── verify_db_setup.py
    │   ├── tests
    │   │   ├── README.md
    │   │   ├── test_api.sh
    │   │   ├── test_api_endpoints.py
    │   │   ├── test_connection.py
    │   │   ├── test_critical_fixes.py
    │   │   ├── test_email_service.py
    │   │   ├── test_end_to_end.py
    │   │   ├── test_ingestion_integration.py
    │   │   ├── test_ocr_parsing.py
    │   │   ├── test_parser_improvements.py
    │   │   ├── test_parser_regression.py
    │   │   ├── test_receipt_batch.py
    │   │   └── test_sync.py
    │   └── token.pickle
    ├── database
    │   ├── README.md
    │   ├── SETUP_INSTRUCTIONS.md
    │   ├── STORAGE_SETUP_GUIDE.md
    │   └── migrations
    │       ├── 001_initial_schema.sql
    │       ├── 002_rls_policies.sql
    │       ├── 003_fix_processed_emails_constraint.sql
    │       ├── 003_storage_setup.sql
    │       └── 003_storage_setup_UI.md
    └── frontend
        ├── .env.example
        ├── .env.local
        ├── .eslintrc.json
        ├── .gitignore
        ├── app
        │   ├── export
        │   │   └── page.tsx
        │   ├── globals.css
        │   ├── layout.tsx
        │   ├── login
        │   │   └── page.tsx
        │   ├── page.tsx
        │   ├── receipts
        │   │   └── page.tsx
        │   └── upload
        │       └── page.tsx
        ├── documentation
        │   ├── README.md
        │   └── archive
        ├── lib
        │   ├── api.ts
        │   └── supabase.ts
        ├── next-env.d.ts
        ├── next.config.ts
        ├── package-lock.json
        ├── package.json
        ├── postcss.config.mjs
        ├── scripts
        ├── tailwind.config.ts
        ├── tests
        └── tsconfig.json

34 directories, 115 files
