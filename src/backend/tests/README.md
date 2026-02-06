# Backend Tests

This directory contains all test files for the backend application.

## Test Files

- `test_api_endpoints.py` - API endpoint integration tests
- `test_connection.py` - Database connection tests
- `test_email_service.py` - Email service tests
- `test_ocr_parsing.py` - OCR and parsing tests
- `test_sync.py` - Email sync tests
- `test_critical_fixes.py` - Parser critical fixes validation
- `test_parser_improvements.py` - Parser improvement tests
- `test_receipt_batch.py` - Batch receipt processing tests
- `test_api.sh` - API testing shell script

## Running Tests

From the backend root directory:
```bash
cd src/backend
python -m pytest tests/
```

Or run individual tests:
```bash
python tests/test_name.py
```
