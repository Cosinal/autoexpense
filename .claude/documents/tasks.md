# AutoExpense: Active Tasks

**Last Updated**: 2026-02-10
**Current Sprint**: Backend Quality & Core Workflow Stabilization

---

## Current Focus

**Primary Goal**: Improve parser reliability and harden core workflows before scaling.

---

## In Progress

### Parser Reliability Improvements
- **Status**: Not started
- **Owner**: TBD
- **Goal**: Increase parser accuracy from ~70-85% to 90%+
- **Scope**:
  - Add regression test suite with real-world receipts
  - Improve vendor extraction patterns
  - Better date disambiguation (MM/DD vs DD/MM)
  - More robust amount parsing (handle edge cases)
  - Improve tax extraction deduplication
- **Success Metric**: 90%+ accuracy on test suite (50+ receipts)

### Core Workflow Hardening
- **Status**: Not started
- **Owner**: TBD
- **Goal**: Upload → Parse → Review → Export must work reliably
- **Scope**:
  - Add comprehensive error handling
  - Improve error messages (user-friendly)
  - Add retry logic for transient failures
  - Test edge cases (corrupted PDFs, huge files, etc.)
- **Success Metric**: <5% failure rate on real receipts

---

## Up Next

### Basic Security (P0 - Blocking Deployment)
- Add JWT authentication to backend (verify_token middleware)
- Add rate limiting (slowapi, 100 req/min per user)
- Add security headers (HSTS, CSP, X-Frame-Options)
- **Estimated**: 5 days
- **Blocker**: Cannot deploy without this

### Staging Deployment
- Deploy backend to Railway/Render
- Deploy frontend to Vercel
- Set up Sentry for error tracking
- Configure environment variables
- **Estimated**: 2 days
- **Depends on**: Basic security complete

### Onboarding Improvements
- Add email verification (Supabase Auth)
- Build simple onboarding wizard (3 steps)
- Add empty state with clear CTAs
- Send welcome email with instructions
- **Estimated**: 3 days
- **Depends on**: Staging deployment

---

## Blocked

None currently.

---

## Completed (Last 2 Weeks)

### Strategic Planning
- ✅ Comprehensive system analysis (5 parallel agents)
- ✅ Created ROADMAP.md with phased plan
- ✅ Created SYSTEM_OVERVIEW.md (architecture docs)
- ✅ Created MODULE_MAP.md (codebase navigation)
- ✅ Created BACKLOG.md (future features)
- ✅ Created 3 ADRs (review UI, semantic duplicates, person name filtering)
- ✅ Strategic direction clarification (Lean Launch focus)

### Documentation Structure
- ✅ Created .claude/claude.md (agent instructions)
- ✅ Created .claude/documents/tasks.md (this file)
- ✅ Created .claude/documents/user_flow.md (user journeys)

### Security
- ✅ Rotated exposed credentials (Supabase keys, Gmail OAuth)

---

## Deferred (Out of Scope for Lean Launch)

- Enterprise features (SSO, audit logs, SOC 2)
- Lovable frontend migration (Phase 2+)
- Accounting integrations (QuickBooks, Xero)
- Advanced analytics dashboard
- Mobile native app
- Heavy compliance infrastructure

---

## Notes

**Key Insight from Strategic Review**: Backend quality is the #1 priority. Don't add features until parsing is reliable and core workflows are solid.

**Definition of "Done" for Lean Launch**:
- Parser accuracy 90%+ on test receipts
- Core workflows work reliably (<5% failure rate)
- Basic security implemented (auth, rate limiting)
- Deployed to staging with monitoring
- 10 beta users testing successfully

**Next Major Milestone**: Launch to 10 beta users from personal/professional network.
