# AutoExpense Module Map

**Purpose**: Quick reference guide for navigating the codebase and understanding "where to change X"

**Last Updated**: 2026-02-10

---

## Table of Contents

- [Repository Structure](#repository-structure)
- [Backend Modules](#backend-modules)
- [Frontend Modules](#frontend-modules)
- [Where to Change X](#where-to-change-x)
- [Key Files Reference](#key-files-reference)

---

## Repository Structure

```
expense-reporting/
├── src/
│   ├── backend/              # Python FastAPI backend
│   └── frontend/             # Next.js React frontend
├── documents/                # Documentation
│   ├── adr/                  # Architecture Decision Records
│   ├── backend/              # Backend-specific docs
│   └── frontend/             # Frontend-specific docs
├── ROADMAP.md                # Product roadmap
├── CHANGELOG.md              # Version history
└── README.md                 # Setup instructions
```

---

## Backend Modules

**Location**: `src/backend/app/`

### Routers (HTTP API Layer)

**Path**: `src/backend/app/routers/`

Handles HTTP requests and responses. Each router maps to a logical API domain.

| File | Endpoints | Purpose |
|------|-----------|---------|
| `receipts.py` | `GET /receipts`, `DELETE /receipts/{id}` | List, filter, delete receipts |
| `upload.py` | `POST /upload` | Manual file upload endpoint |
| `sync.py` | `POST /sync` | Gmail inbox synchronization |
| `export.py` | `GET /export` | Export receipts to CSV |
| `review.py` | `GET /review/pending`, `POST /review/submit`, `GET /review/corrections/export` | Review queue for corrections, ML training data export |

**Key Patterns**:
- All routes are async (`async def`)
- Pydantic models for request/response validation
- Dependency injection for services
- ⚠️ **CRITICAL**: No authentication middleware (all routes accept user_id from client)

**Example**:
```python
# receipts.py:64
@router.get("", response_model=ReceiptList)
async def list_receipts(
    user_id: str = Query(...),  # ❌ No auth verification
    vendor: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    receipts, total = await ReceiptService.list_receipts(
        user_id, vendor, start_date, end_date, skip, limit
    )
    return {"receipts": receipts, "total": total}
```

---

### Services (Business Logic Layer)

**Path**: `src/backend/app/services/`

Contains core business logic, orchestrates operations, and interacts with external services.

| File | Purpose | Key Methods |
|------|---------|-------------|
| `ingestion.py` | Receipt processing pipeline | `process_upload()`, `process_email_attachment()`, `_check_semantic_duplicate()` |
| `parser.py` | OCR text → structured data | `parse()`, `extract_vendor()`, `extract_amount()`, `extract_date()`, `extract_currency()`, `extract_tax()` |
| `ocr.py` | PDF/image → text extraction | `extract_text_from_file()`, `extract_text_from_pdf()`, `extract_text_from_image()` |
| `storage.py` | File uploads to Supabase | `upload_file()`, `get_file_url()`, `delete_file()` |
| `email.py` | Gmail API integration | `sync_inbox()`, `get_attachments()`, `mark_as_processed()` |

**Key Architecture**:
- Services are **stateless** (no instance variables)
- All methods are **static** or **class methods**
- Services call each other (e.g., IngestionService → OCRService → ParserService)
- Services interact with Supabase client directly

**Example Flow** (Upload):
```python
# ingestion.py:150
@classmethod
async def process_upload(cls, user_id: str, file: UploadFile) -> Dict[str, Any]:
    # 1. Save file temporarily
    temp_path = await cls._save_temp_file(file)

    # 2. Process through pipeline
    result = await cls._process_source(user_id, temp_path, file.filename, "upload")

    return result
```

---

### Utils (Helper Functions)

**Path**: `src/backend/app/utils/`

Reusable helper functions for specific tasks.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `scoring.py` | Confidence scoring for candidates | `score_vendor_candidate()`, `score_amount_candidate()`, `_looks_like_person_name()` |
| `candidates.py` | Candidate data structures | `select_top_vendors()`, `select_top_amounts()`, `select_top_dates()` |
| `money.py` | Currency and amount parsing | `parse_amount()`, `normalize_currency()` |

**Key Patterns**:
- Pure functions (no side effects)
- Type hints for all parameters
- Defensive programming (handle None, empty strings)

**Example**:
```python
# scoring.py:45
def _looks_like_person_name(text: str) -> bool:
    """Detect if text looks like a person's name (e.g., 'Jorden Shaw')."""
    if not text or len(text) > 50:
        return False

    words = text.split()
    if len(words) not in [2, 3]:
        return False

    # Check if all words are title case
    if not all(w[0].isupper() and w[1:].islower() for w in words):
        return False

    # Check for business indicators
    business_indicators = ['Inc', 'LLC', 'Clinic', 'Store', ...]
    if any(indicator in words for indicator in business_indicators):
        return False

    return True
```

---

### Models (Data Schemas)

**Path**: `src/backend/app/models/`

Pydantic models for request/response validation and serialization.

| File | Purpose | Models |
|------|---------|--------|
| `receipt.py` | Receipt data structures | `ReceiptData`, `ReceiptResponse`, `ReceiptList`, `ReceiptFilter` |

**Key Patterns**:
- Inherit from `BaseModel` (Pydantic)
- Use type hints (e.g., `Optional[str]`, `Decimal`, `date`)
- Automatic validation on instantiation
- Serialization to JSON via `.dict()`

**Example**:
```python
# receipt.py:10
class ReceiptData(BaseModel):
    vendor: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = "CAD"
    date: Optional[date] = None
    tax: Optional[Decimal] = None
    confidence: Optional[float] = 0.0
```

---

### Database & Migrations

**Path**: `src/backend/app/database/` and `src/backend/migrations/`

SQL files for database schema and migrations.

| File | Purpose |
|------|---------|
| `database/schema.sql` | Initial database schema (tables, indexes, RLS policies) |
| `migrations/add_review_columns.sql` | Add needs_review, confidence columns |
| `migrations/add_user_corrections.sql` | Add user_corrections, corrected_at columns |

**Migration Process** (Manual):
```bash
# Connect to Supabase via psql or SQL editor
psql $SUPABASE_DATABASE_URL

# Run migration file
\i src/backend/migrations/add_review_columns.sql
```

⚠️ **No automated migration tool** (like Alembic) - migrations are manual SQL scripts.

---

### Configuration

**Path**: `src/backend/app/config.py`

Environment variable management using Pydantic settings.

```python
# config.py:10
class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_KEY: str
    GMAIL_CLIENT_ID: str
    GMAIL_CLIENT_SECRET: str
    GMAIL_REFRESH_TOKEN: str
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
```

**Usage**:
```python
from app.config import settings

supabase_url = settings.SUPABASE_URL
```

---

### Tests

**Path**: `src/backend/tests/`

Test suite covering parser, ingestion, and end-to-end flows.

| File | Purpose | Key Tests |
|------|---------|-----------|
| `test_critical_fixes.py` | Parser regression tests | Steam receipt, Paddle receipt, LinkedIn receipt, Uber receipt |
| `test_end_to_end.py` | Full pipeline tests | Upload → OCR → Parse → Database |
| `test_ingestion_integration.py` | Integration tests with Supabase | File upload, semantic duplicate detection |

**Run Tests**:
```bash
cd src/backend
python3 -m pytest tests/
```

---

## Frontend Modules

**Location**: `src/frontend/`

### App Router Pages

**Path**: `src/frontend/app/`

Next.js 15 App Router structure (file-system based routing).

| File | Route | Purpose |
|------|-------|---------|
| `app/page.tsx` | `/` | Root page (redirects to /login or /receipts) |
| `app/login/page.tsx` | `/login` | Login page |
| `app/signup/page.tsx` | `/signup` | Signup page |
| `app/receipts/page.tsx` | `/receipts` | Main dashboard (receipt list + filters) |
| `app/receipts/review/page.tsx` | `/receipts/review` | Review queue for corrections |
| `app/layout.tsx` | N/A | Root layout (providers, global styles) |

**Key Patterns**:
- Pages are React Server Components by default
- Use `'use client'` directive for client-side interactivity
- Each page is 300-600 lines (⚠️ needs component extraction)

**Example**:
```typescript
// app/receipts/page.tsx:50
export default function ReceiptsPage() {
  const [receipts, setReceipts] = useState<Receipt[]>([])
  const [filters, setFilters] = useState<ReceiptFilters>({})

  useEffect(() => {
    fetchReceipts()
  }, [filters])

  const fetchReceipts = async () => {
    const { data: { user } } = await supabase.auth.getUser()
    const response = await fetch(
      `${API_URL}/receipts?user_id=${user.id}&...`
    )
    const data = await response.json()
    setReceipts(data.receipts)
  }

  return (
    <div>
      <FilterBar onFilterChange={setFilters} />
      <ReceiptTable receipts={receipts} />
      <ExportButton />
    </div>
  )
}
```

---

### Components

**Path**: `src/frontend/components/`

⚠️ **Currently minimal** - Most UI is inline in page components.

**Recommended Structure** (Future):
```
components/
├── ui/                      # Reusable UI primitives
│   ├── Button.tsx
│   ├── Input.tsx
│   ├── Modal.tsx
│   └── Table.tsx
├── receipts/               # Receipt-specific components
│   ├── ReceiptTable.tsx
│   ├── ReceiptRow.tsx
│   ├── FilterBar.tsx
│   └── ExportButton.tsx
└── layout/                 # Layout components
    ├── Header.tsx
    ├── Sidebar.tsx
    └── Footer.tsx
```

---

### Lib (Utilities & Configs)

**Path**: `src/frontend/lib/`

| File | Purpose |
|------|---------|
| `supabase.ts` | Supabase client initialization for frontend |

**Example**:
```typescript
// lib/supabase.ts:5
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

---

### Styles

**Path**: `src/frontend/app/globals.css`

Global Tailwind CSS styles + custom CSS variables.

**Key Classes**:
- Use Tailwind utility classes (e.g., `bg-blue-500`, `text-lg`, `p-4`)
- Custom CSS for complex layouts (e.g., table styling)

---

### Configuration Files

| File | Purpose |
|------|---------|
| `next.config.js` | Next.js configuration |
| `tailwind.config.ts` | Tailwind CSS configuration |
| `tsconfig.json` | TypeScript configuration |
| `.env.local` | Environment variables (Supabase URL, API URL) |

---

## Where to Change X

### "I want to add a new API endpoint"

1. **Define the route** in `src/backend/app/routers/`
   - Create new router file or add to existing router
   - Example: `@router.post("/my-endpoint")`

2. **Add business logic** in `src/backend/app/services/`
   - Create new service or extend existing service
   - Example: `MyService.do_something()`

3. **Define request/response models** in `src/backend/app/models/`
   - Create Pydantic models for validation
   - Example: `class MyRequest(BaseModel): ...`

4. **Register router** in `src/backend/app/main.py`
   - Import and include router
   - Example: `app.include_router(my_router, prefix="/api/my-endpoint")`

5. **Write tests** in `src/backend/tests/`
   - Test endpoint with mock data
   - Example: `test_my_endpoint.py`

---

### "I want to change the receipt parsing logic"

**File**: `src/backend/app/services/parser.py`

- **Vendor extraction**: `extract_vendor()` method (line ~200)
  - Add new patterns in `_init_patterns()` → `known_vendors`
  - Adjust scoring in `utils/scoring.py:score_vendor_candidate()`

- **Amount extraction**: `extract_amount()` method (line ~340)
  - Add new patterns in `_init_patterns()` → `amount_patterns`
  - Patterns use priority (lower = higher priority)

- **Date extraction**: `extract_date()` method (line ~470)
  - Add new patterns in `_init_patterns()` → `date_patterns`
  - Handle ambiguous dates (MM/DD vs DD/MM) in `_detect_date_locale()`

- **Tax extraction**: `extract_tax()` method (line ~580)
  - Add new patterns in `_init_patterns()` → `tax_patterns`
  - Deduplication by span position (not text match)

**Testing**:
```bash
cd src/backend
python3 tests/test_critical_fixes.py  # Run parser regression tests
```

---

### "I want to add a new database table"

1. **Create migration SQL** in `src/backend/migrations/`
   - Example: `add_new_table.sql`

2. **Define table schema**:
   ```sql
   CREATE TABLE my_table (
       id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
       user_id UUID NOT NULL REFERENCES auth.users(id),
       created_at TIMESTAMPTZ DEFAULT NOW()
   );
   ```

3. **Add RLS policies**:
   ```sql
   ALTER TABLE my_table ENABLE ROW LEVEL SECURITY;

   CREATE POLICY "Users can view own data"
     ON my_table FOR SELECT
     USING (auth.uid() = user_id);
   ```

4. **Run migration**:
   ```bash
   psql $SUPABASE_DATABASE_URL -f src/backend/migrations/add_new_table.sql
   ```

5. **Update Pydantic models** in `src/backend/app/models/`

---

### "I want to add a new page to the frontend"

1. **Create page file** in `src/frontend/app/`
   - Example: `app/my-page/page.tsx`
   - Route automatically becomes `/my-page`

2. **Define page component**:
   ```typescript
   'use client'  // If using client-side features

   export default function MyPage() {
     return <div>My Page Content</div>
   }
   ```

3. **Add navigation link** in `app/layout.tsx` or header component
   ```tsx
   <Link href="/my-page">My Page</Link>
   ```

4. **Protect route** (if authentication required):
   ```typescript
   useEffect(() => {
     const checkAuth = async () => {
       const { data: { user } } = await supabase.auth.getUser()
       if (!user) router.push('/login')
     }
     checkAuth()
   }, [])
   ```

---

### "I want to change the UI styling"

- **Global styles**: `src/frontend/app/globals.css`
- **Component styles**: Use Tailwind classes inline
  - Example: `<button className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded">`
- **Custom styles**: Add to `tailwind.config.ts` for reusable custom classes

**Tailwind Cheat Sheet**:
- Colors: `bg-{color}-{shade}`, `text-{color}-{shade}`
- Spacing: `p-{size}` (padding), `m-{size}` (margin)
- Typography: `text-{size}`, `font-{weight}`
- Layout: `flex`, `grid`, `w-{size}`, `h-{size}`

---

### "I want to add authentication to an API endpoint"

⚠️ **Currently not implemented** - This is a CRITICAL security gap.

**Recommended Implementation**:

1. **Add JWT verification middleware** in `src/backend/app/main.py`:
   ```python
   from fastapi import Depends, HTTPException
   from fastapi.security import HTTPBearer

   security = HTTPBearer()

   async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
       token = credentials.credentials
       # Verify JWT with Supabase
       # Return user_id from token
       pass
   ```

2. **Protect route** in router:
   ```python
   @router.get("/receipts")
   async def list_receipts(
       user_id: str = Depends(verify_token),  # ✅ Verified from JWT
       ...
   ):
       pass
   ```

3. **Update frontend** to send JWT in `src/frontend/`:
   ```typescript
   const { data: { session } } = await supabase.auth.getSession()
   const response = await fetch(`${API_URL}/receipts`, {
     headers: {
       'Authorization': `Bearer ${session.access_token}`
     }
   })
   ```

---

### "I want to add a new filter to the receipt list"

1. **Backend**: Update `src/backend/app/routers/receipts.py`
   - Add query parameter to `list_receipts()` endpoint
   - Example: `min_amount: Optional[Decimal] = Query(None)`

2. **Backend**: Update database query in `src/backend/app/services/receipts.py`
   - Add `.gte('amount', min_amount)` to Supabase query

3. **Frontend**: Update `src/frontend/app/receipts/page.tsx`
   - Add input field for new filter
   - Update `fetchReceipts()` to include new query param

4. **Frontend**: Update filter state:
   ```typescript
   const [filters, setFilters] = useState({
     vendor: '',
     startDate: '',
     endDate: '',
     minAmount: ''  // New filter
   })
   ```

---

### "I want to change the CSV export format"

**File**: `src/backend/app/routers/export.py`

- **Add/remove columns**: Update `writer.writerow([...])` in line ~106
- **Change delimiter**: Modify `csv.writer()` parameters
- **Add header row**: Update `writer.writerow(['Vendor', 'Amount', ...])` in line ~100

**Example**:
```python
# export.py:100
writer.writerow(['Vendor', 'Amount', 'Currency', 'Date', 'Tax', 'Category'])  # Add 'Category'

for receipt in receipts:
    writer.writerow([
        receipt.get('vendor', ''),
        receipt.get('amount', ''),
        receipt.get('currency', 'CAD'),
        receipt.get('date', ''),
        receipt.get('tax', ''),
        receipt.get('category', 'Uncategorized')  # New field
    ])
```

---

### "I want to add a new external integration (e.g., QuickBooks)"

1. **Create service** in `src/backend/app/services/`
   - Example: `quickbooks.py`
   - Implement OAuth flow, API client, sync methods

2. **Add OAuth endpoints** in `src/backend/app/routers/`
   - Example: `integrations.py` with `/integrations/quickbooks/authorize`, `/integrations/quickbooks/callback`

3. **Store OAuth tokens** in database
   - Add `integrations` table with `user_id`, `provider`, `access_token`, `refresh_token`

4. **Add UI** in `src/frontend/app/settings/integrations/page.tsx`
   - "Connect QuickBooks" button → OAuth flow
   - Display connection status

5. **Add sync logic**
   - Trigger: Manual button or automatic webhook
   - Sync receipts → QuickBooks expenses

---

### "I want to improve OCR accuracy"

**Option 1: Improve Tesseract preprocessing** (Easy)
- **File**: `src/backend/app/services/ocr.py`
- Add image preprocessing:
  - Increase contrast: `ImageEnhance.Contrast(image).enhance(2.0)`
  - Deskew: Rotate image to fix alignment
  - Denoise: Apply filters to remove noise
- Adjust Tesseract config: `--psm 6` (assume uniform text block)

**Option 2: Switch to commercial OCR** (Medium)
- **Google Cloud Vision API**:
  - Higher accuracy (90-95%)
  - Costs: $1.50 per 1,000 images
  - Implementation: Replace `pytesseract.image_to_string()` with Vision API call

- **AWS Textract**:
  - Receipt-specialized (detects line items, totals)
  - Costs: $1.50 per 1,000 pages
  - Implementation: Use boto3 SDK

**Option 3: Train custom model** (Hard)
- Use user corrections (stored in `user_corrections` column) as training data
- Train fine-tuned OCR model on receipt images
- Requires ML engineering expertise

---

### "I want to add a new feature flag"

⚠️ **No feature flag system currently implemented**

**Recommended Implementation**:

1. **Add feature flag config** in `src/backend/app/config.py`:
   ```python
   class Settings(BaseSettings):
       FEATURE_NEW_PARSER: bool = False
   ```

2. **Use flag in code**:
   ```python
   from app.config import settings

   if settings.FEATURE_NEW_PARSER:
       result = new_parser.parse(text)
   else:
       result = old_parser.parse(text)
   ```

3. **Toggle via environment variable**:
   ```bash
   FEATURE_NEW_PARSER=true uvicorn main:app
   ```

**Better solution**: Use LaunchDarkly, Unleash, or similar feature flag service.

---

## Key Files Reference

### Most Frequently Modified Files

| File | Purpose | Modification Frequency |
|------|---------|------------------------|
| `src/backend/app/services/parser.py` | Receipt parsing logic | High (every parser improvement) |
| `src/frontend/app/receipts/page.tsx` | Main dashboard UI | High (UI tweaks, features) |
| `src/backend/app/routers/receipts.py` | Receipt API endpoints | Medium (new filters, endpoints) |
| `src/backend/app/services/ingestion.py` | Receipt processing pipeline | Medium (new sources, deduplication) |
| `src/frontend/app/receipts/review/page.tsx` | Review queue UI | Medium (UX improvements) |

### Files You Should NOT Modify Directly

| File | Reason | Alternative |
|------|--------|-------------|
| `src/backend/app/database/schema.sql` | Initial schema only | Create new migration in `migrations/` |
| `.env` files | Secrets (never commit) | Use environment variables in hosting platform |
| `node_modules/` | Auto-generated | Update `package.json` + run `npm install` |
| `__pycache__/` | Auto-generated | Ignored by git |

### Critical Configuration Files

| File | Purpose | When to Modify |
|------|---------|----------------|
| `src/backend/app/config.py` | Environment variables | Adding new secrets/settings |
| `src/backend/.env` | Local development secrets | Never (use .env.example template) |
| `src/frontend/.env.local` | Frontend environment vars | Changing Supabase URL, API URL |
| `src/backend/requirements.txt` | Python dependencies | Adding new packages |
| `src/frontend/package.json` | Node.js dependencies | Adding new packages |

---

## Architecture Diagrams (Text-Based)

### Request Flow (Upload Endpoint)

```
User Browser
    │
    │ POST /upload (multipart/form-data)
    ▼
┌─────────────────────────────┐
│ Backend: upload.py router   │
│  • Validate file type       │
│  • Validate file size       │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ IngestionService            │
│  • Save temp file           │
│  • Compute SHA-256 hash     │
└──────────┬──────────────────┘
           │
           ├─→ Check file_hash in database (dedup)
           │
           ├─→ StorageService.upload()
           │   └─→ Supabase Storage
           │
           ├─→ OCRService.extract_text()
           │   └─→ Tesseract CLI
           │
           ├─→ ParserService.parse()
           │   ├─→ extract_vendor()
           │   ├─→ extract_amount()
           │   ├─→ extract_date()
           │   ├─→ extract_currency()
           │   └─→ extract_tax()
           │
           ├─→ _check_semantic_duplicate()
           │   └─→ Query receipts (vendor+amount+date)
           │
           └─→ Insert into receipts table
               └─→ Supabase PostgreSQL
    │
    ▼
Return receipt JSON to frontend
```

### Service Dependencies

```
Routers (HTTP Layer)
    │
    ├─→ ReceiptService ──→ Supabase (receipts table)
    │
    ├─→ IngestionService
    │   ├─→ StorageService ──→ Supabase Storage
    │   ├─→ OCRService ──→ Tesseract
    │   ├─→ ParserService
    │   │   └─→ Utils (scoring, candidates, money)
    │   └─→ Supabase (receipts, processed_emails)
    │
    ├─→ EmailService ──→ Gmail API
    │   └─→ IngestionService
    │
    └─→ ExportService ──→ Supabase (receipts table)
```

---

## Quick Reference: Common Tasks

### Add a new receipt field

1. **Database**: Add column in migration (e.g., `ALTER TABLE receipts ADD COLUMN category TEXT`)
2. **Backend**: Update `ReceiptData` model in `models/receipt.py`
3. **Backend**: Add extraction logic in `services/parser.py`
4. **Frontend**: Display in `app/receipts/page.tsx` table

### Fix a parser bug

1. **Reproduce**: Add failing test case in `tests/test_critical_fixes.py`
2. **Debug**: Add logging in `services/parser.py` (use `logger.debug()`)
3. **Fix**: Adjust regex patterns or scoring logic
4. **Verify**: Run `python3 tests/test_critical_fixes.py`

### Deploy a new version

1. **Backend**: Push to GitHub → Railway/Render auto-deploys
2. **Frontend**: Push to GitHub → Vercel auto-deploys
3. **Database**: Run migration manually via Supabase SQL editor
4. **Monitor**: Check Sentry for errors, Datadog for metrics

### Debug production issues

1. **Check logs**: Sentry dashboard (error traces)
2. **Check metrics**: Datadog dashboard (latency, error rate)
3. **Check status**: StatusPage.io (service status)
4. **Reproduce locally**: Use production data snapshot

---

## Glossary

- **Router**: FastAPI endpoint handler (HTTP layer)
- **Service**: Business logic layer (orchestrates operations)
- **Model**: Pydantic data structure (validation + serialization)
- **OCR**: Optical Character Recognition (PDF/image → text)
- **Parser**: Text extraction logic (OCR text → structured data)
- **Candidate**: Potential value for a field (e.g., 3 vendor candidates)
- **Confidence**: Score (0-1) indicating extraction certainty
- **RLS**: Row-Level Security (Postgres feature for data isolation)
- **Supabase**: Backend-as-a-Service (Postgres + Storage + Auth)
- **SSR**: Server-Side Rendering (Next.js feature)

---

**Document Owner**: Engineering Team
**Review Cadence**: Update when major code reorganization occurs
**Last Updated**: 2026-02-10
