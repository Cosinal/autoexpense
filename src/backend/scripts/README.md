# Backend Scripts

This directory contains utility and setup scripts for the backend.

## Setup Scripts
- `get_gmail_token.py` - Generate Gmail API authentication token
- `setup_storage_bucket.py` - Configure Supabase storage bucket
- `create_test_user.py` - Create test user in database
- `verify_db_setup.py` - Verify database configuration

## Analysis Scripts
- `analyze_receipts.py` - Analyze receipt parsing performance
- `detailed_analysis.py` - Detailed receipt parsing analysis
- `download_failed_receipts.py` - Download failed receipts for debugging

## Utility Scripts
- `check_bucket_config.py` - Check storage bucket configuration
- `extract_pdf_text.py` - Extract text from PDF receipts
- `list_storage_files.py` - List files in storage bucket
- `debug_receipt.py` - Debug individual receipt parsing
- `run.sh` - Quick start script for development server

## Usage

Run scripts from the backend root directory:
```bash
cd src/backend
python scripts/script_name.py
```
