# AutoExpense: Claude Agent Instructions

**Version**: 1.0
**Last Updated**: 2026-02-10
**Status**: Active Development - Lean Launch Phase

---

## Project Summary

**AutoExpense** is a privacy-first expense receipt management tool for busy executives who want zero-effort expense tracking without connecting bank accounts.

**Core Value Proposition**: Email forwarding → automatic OCR → structured data → export to accountant. Simple, private, reliable.

**Target Users**: Individual executives, consultants, freelancers (10-50 receipts/month).

**Current Phase**: Backend maturity and core workflow stabilization.

---

## Development Principles

1. **Product Reliability Over Feature Volume** - Parsing must work consistently before adding features
2. **User Value Over Enterprise Readiness** - Focus on individual users, not enterprises (for now)
3. **Validation Over Speculation** - Real user feedback drives priorities
4. **Iteration Over Heavy Systems** - Simple solutions first, optimize later
5. **Quality Over Speed** - Better to ship slowly than ship broken

---

## Current Strategic Focus (Next 6 Weeks)

### Primary Objectives
1. **Improve parsing consistency** - Vendor, amount, date extraction must be reliable
2. **Harden core workflows** - Upload → parse → review → export must work smoothly
3. **Reduce user friction** - Onboarding, error messages, correction UI
4. **Improve error transparency** - Users understand what failed and why
5. **Gather structured feedback** - Real user validation of product-market fit

### Out of Scope (For Now)
- Enterprise features (SSO, audit logs, SOC 2)
- Platform migrations (Lovable frontend migration is Phase 2+)
- Heavy compliance infrastructure
- Large-scale integrations

---

## Agent Execution Rules

### When to Use Agent Teams
- **Complex codebase exploration** - Use Explore agent (quick/medium/thorough)
- **Multi-file refactoring** - Use Plan agent for implementation strategy
- **Parallel analysis** - Launch multiple agents for independent research
- **Code search** - Use Explore agent instead of manual Grep/Glob chains

### Task Decomposition
- Break large tasks into <1 day subtasks
- Validate outputs after each subtask
- Document blockers immediately
- Ask clarifying questions early

### Agent Coordination
- One agent per major concern (frontend, backend, data, etc.)
- Share findings via documents (ADRs, tasks.md)
- No duplicate work across agents

---

## Engineering Standards

### Code Quality
- **Readable over clever** - Code is read 10x more than written
- **Tested critical paths** - Parser, ingestion, auth must have tests
- **Type hints** - Python type hints for all functions
- **Error handling** - Never silently swallow exceptions

### Security
- **No secrets in code** - Use environment variables only
- **Validate user input** - Never trust client-side data
- **Authenticate API calls** - JWT verification on all endpoints
- **Rate limiting** - Prevent abuse and DoS

### Performance
- **Don't optimize prematurely** - Profile first, then optimize
- **Async where it matters** - OCR should be async (background jobs)
- **Cache sparingly** - Only cache expensive, frequently accessed data

---

## Documentation Discipline

### Architecture Decision Records (ADR)
All major technical or product decisions must be documented in `documents/adr/`.

**When to create an ADR:**
- Choosing between technical approaches (e.g., sync vs async OCR)
- Significant architectural changes (e.g., database schema changes)
- Security or compliance decisions (e.g., authentication strategy)
- Product direction shifts (e.g., enterprise vs individual focus)

**ADR Format:**
- **Context** - What problem are we solving?
- **Decision** - What did we decide?
- **Alternatives Considered** - What other options did we evaluate?
- **Consequences** - What becomes easier or harder?

### Changelog
Update `CHANGELOG.md` after every iteration with user-facing changes.

**Format:**
- Version number (semantic versioning)
- Date
- Added/Changed/Fixed/Removed sections
- Files changed (for developer reference)

### Keep Docs Current
- Update `.claude/documents/tasks.md` weekly
- Update `.claude/documents/user_flow.md` when workflows change
- Archive outdated docs (don't delete - move to `documents/archive/`)

---

## Change Management

### Before Making Breaking Changes
1. Document the change in an ADR
2. Update affected documentation
3. Write migration guide if needed
4. Communicate impact to users (if deployed)

### Git Practices
- Descriptive commit messages (what and why)
- Small, focused commits
- Never commit secrets or .env files
- Co-authored commits: `Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>`

---

## Current Architecture (High-Level)

**Backend**: FastAPI (Python) - Routers → Services → Models pattern
**Frontend**: Next.js 15 (React 19) - App Router pages
**Database**: Supabase PostgreSQL with Row-Level Security
**Storage**: Supabase Storage (private bucket)
**OCR**: Tesseract (local binary)
**Email**: Gmail API (OAuth 2.0 polling)

**Key Services**:
- `parser.py` - OCR text → structured data (vendor, amount, date, currency, tax)
- `ingestion.py` - Receipt processing pipeline (upload → OCR → parse → DB)
- `ocr.py` - PDF/image → text extraction
- `storage.py` - File upload to Supabase
- `email.py` - Gmail inbox sync

---

## Known Issues & Technical Debt

### Backend
- Parser accuracy ~70-85% (needs improvement)
- Synchronous OCR (blocks HTTP workers)
- No automated testing for edge cases
- Missing rate limiting (security gap)

### Frontend
- Large page components (300-600 lines)
- Zero component reusability
- No tests (Jest, React Testing Library)
- Poor mobile experience

### Infrastructure
- No production deployment (local dev only)
- No monitoring (Sentry, Datadog)
- No CI/CD pipeline

---

## What "Market-Ready" Means (Lean Launch)

**Minimum viable:**
- Users can upload or forward receipts
- Most receipts parse correctly (80%+ accuracy)
- Errors are understandable
- Corrections are easy
- Data export works reliably

**Not required:**
- Enterprise compliance (SOC 2, SSO, audit logs)
- Complex integrations (QuickBooks, Xero)
- Perfect mobile experience
- Heavy automation

---

## Path Forward

### Phase 1 (Weeks 1-3): Backend Quality
- Improve parser reliability
- Add error handling and logging
- Implement basic security (auth, rate limiting)
- Deploy to staging environment

### Phase 2 (Weeks 4-6): User Experience
- Simplify onboarding
- Improve review/correction UI
- Add basic help docs
- Launch to 10 beta users

### Phase 3 (Post-Launch): Iterate
- Gather feedback
- Fix critical bugs
- Improve based on real usage patterns
- Decide: continue individual focus or pivot to enterprise

---

## Guiding Principle

> Build something people rely on before building something that scales.

---

**Document Owner**: Engineering & Product
**Review Cadence**: Monthly or after major strategic shifts
