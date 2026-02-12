# Pre-Launch Checklist: Path to Beta Launch

**Status**: Phase 1 Complete ✅ | Pre-Launch In Progress 🔄
**Target Launch Date**: TBD (2-4 weeks)
**Last Updated**: 2026-02-12

---

## Overview

Phase 1 launch hardening is complete. This checklist covers remaining work needed to launch AutoExpense to beta users.

**Launch Definition**: 10 beta users can upload/forward receipts → parser extracts data → users review/correct → export to accountant.

---

## Phase 1 ✅ COMPLETE

- ✅ Parser reliability (62 tests passing, 100% pass rate)
- ✅ Confidence scoring and review gating
- ✅ Forwarding-aware vendor extraction
- ✅ Amount filtering and validation
- ✅ Export reliability with validation warnings
- ✅ Launch safety validation

**Phase 1 is production-ready.**

---

## Pre-Launch Work Remaining

### 1. Backend Deployment (Priority: Critical)

**Status**: 🔴 Not Started

#### Tasks:
- [ ] Deploy backend to production environment (Heroku, Railway, or Render)
- [ ] Configure production environment variables (Supabase keys, Tesseract paths)
- [ ] Set up production database (Supabase PostgreSQL)
- [ ] Verify Tesseract OCR binary installed on production server
- [ ] Test file upload to Supabase Storage from production
- [ ] Configure CORS for frontend domain
- [ ] Set up monitoring (Sentry for error tracking)
- [ ] Configure log aggregation (Papertrail, Datadog, or CloudWatch)
- [ ] Set up health check endpoint monitoring (uptime checks)

#### Acceptance Criteria:
- Backend accessible at production URL (e.g., `https://api.autoexpense.com`)
- `/health` endpoint returns 200 OK
- File upload and OCR work in production
- Error logs captured and viewable
- Uptime monitoring configured

#### Estimated Time: 1-2 days

---

### 2. Frontend Integration (Priority: Critical)

**Status**: 🟡 Partial (needs validation)

#### Tasks:
- [ ] Verify frontend calls `/export/csv` endpoint correctly
- [ ] Test frontend displays `needs_review` flag for flagged receipts
- [ ] Implement review queue UI filter (show only `needs_review=True` receipts)
- [ ] Test frontend displays validation warnings from CSV export
- [ ] Verify frontend shows top-3 candidates for low-confidence fields
- [ ] Test CSV download in browser with new columns (Review Status, Validation Warnings)
- [ ] Add loading states for export (may take seconds for large datasets)
- [ ] Test error handling when export fails (no receipts, server error)

#### Acceptance Criteria:
- Review queue shows receipts with `needs_review=True`
- CSV export downloads with all new columns
- Validation warnings visible in UI or export
- Top-3 candidates visible for manual correction
- Error messages are user-friendly

#### Estimated Time: 2-3 days

---

### 3. Manual Smoke Testing (Priority: High)

**Status**: 🔴 Not Started

#### Test Cases:

**3.1. Upload Flow**
- [ ] Upload real PDF receipts (Starbucks, Uber, Apple, Walmart, Steam)
- [ ] Verify OCR extracts text correctly
- [ ] Verify parser extracts vendor, amount, date, currency, tax
- [ ] Check confidence values in database (`ingestion_debug` column)
- [ ] Verify `needs_review` flag set correctly

**3.2. Review Flow**
- [ ] Filter receipts by `needs_review=True`
- [ ] Verify low-confidence receipts appear in review queue
- [ ] Test manual correction of vendor, amount, date
- [ ] Verify correction saves to database
- [ ] Verify `needs_review` flag changes to `False` after correction

**3.3. Export Flow**
- [ ] Export receipts to CSV
- [ ] Verify CSV has all columns: Date, Vendor, Amount, Currency, Tax, Review Status, Validation Warnings, File Name, File URL, Receipt ID
- [ ] Verify amounts formatted to 2 decimal places
- [ ] Verify missing fields show "N/A" not empty strings
- [ ] Verify Review Status shows "Reviewed" or "Needs Review"
- [ ] Verify Validation Warnings show issues (or "None")
- [ ] Open CSV in Excel/Google Sheets (verify formatting)
- [ ] Test date range filtering (start_date, end_date)
- [ ] Test currency filtering

**3.4. Edge Cases**
- [ ] Upload empty PDF (no text)
- [ ] Upload image receipt (JPG, PNG)
- [ ] Upload forwarded email receipt
- [ ] Upload receipt with OCR artifacts ("I N V O I C E")
- [ ] Upload receipt with tax breakdown (GeoGuessr case)
- [ ] Upload receipt with ambiguous vendor (person name)
- [ ] Upload receipt with inconsistent amounts (subtotal + tax ≠ total)

**3.5. Email Sync Flow** (if implemented)
- [ ] Connect Gmail account via OAuth
- [ ] Forward receipt to AutoExpense email
- [ ] Verify receipt appears in inbox
- [ ] Verify parser extracts data correctly
- [ ] Test forwarded email detection (Uber forwarded by user)

#### Acceptance Criteria:
- All test cases pass
- No crashes or 500 errors
- Errors are user-friendly ("Failed to parse receipt" not "Internal server error")
- Edge cases handled gracefully (flagged for review, not crashed)

#### Estimated Time: 1-2 days

---

### 4. Documentation & Help Materials (Priority: Medium)

**Status**: 🔴 Not Started

#### Tasks:
- [ ] Create user onboarding guide (how to upload receipts, review, export)
- [ ] Document common parsing issues and fixes
- [ ] Create FAQ for beta users:
  - What if vendor is wrong? (Review queue, manual correction)
  - What if amount is wrong? (Review queue, manual correction)
  - What does "Needs Review" mean? (Low confidence, flagged for manual check)
  - What do validation warnings mean? (Amount inconsistency, low confidence, forwarding)
- [ ] Create CSV export guide for accountants (column meanings)
- [ ] Add in-app help text/tooltips (Review Status, Validation Warnings)

#### Acceptance Criteria:
- Onboarding guide available (Notion, Markdown, or in-app)
- FAQ covers common questions
- Accountants understand CSV export format

#### Estimated Time: 1 day

---

### 5. Beta User Recruitment (Priority: Medium)

**Status**: 🔴 Not Started

#### Tasks:
- [ ] Identify 10 beta users (friends, colleagues, early adopters)
- [ ] Send beta invitations with onboarding guide
- [ ] Set up feedback collection (Google Form, Typeform, or email)
- [ ] Schedule weekly check-ins with beta users
- [ ] Create private Slack/Discord channel for beta feedback

#### Beta User Criteria:
- Has 10-50 receipts/month
- Willing to provide feedback
- Uses receipts for business expenses/taxes
- Not expecting enterprise features (yet)

#### Acceptance Criteria:
- 10 beta users onboarded
- Feedback mechanism in place
- Weekly check-ins scheduled

#### Estimated Time: 1-2 days (outreach + setup)

---

### 6. Error Handling & Observability (Priority: High)

**Status**: 🟡 Partial (basic logging exists)

#### Tasks:
- [ ] Set up Sentry error tracking (backend + frontend)
- [ ] Configure log levels (DEBUG for staging, INFO for production)
- [ ] Add structured logging for parser events:
  - Receipt uploaded (user_id, file_name, file_size)
  - OCR started/completed (duration, text_length)
  - Parse started/completed (duration, vendor, amount, confidence)
  - Review submitted (user_id, receipt_id, corrections)
  - Export generated (user_id, receipt_count, date_range)
- [ ] Set up alerting for critical errors:
  - OCR failures (Tesseract crashes)
  - Database connection errors
  - Parser crashes (unexpected exceptions)
- [ ] Create error dashboards (Sentry, Datadog, or Grafana)

#### Acceptance Criteria:
- All errors captured in Sentry
- Critical errors trigger alerts (email, Slack)
- Log search works (find receipts by user_id, file_name)
- Dashboards show key metrics (parse success rate, OCR success rate)

#### Estimated Time: 1 day

---

### 7. Rate Limiting & Security (Priority: High)

**Status**: 🔴 Not Started

#### Tasks:
- [ ] Implement rate limiting on API endpoints:
  - `/receipts/upload` - 10 uploads/minute per user
  - `/export/csv` - 5 exports/minute per user
  - `/review/submit` - 20 reviews/minute per user
- [ ] Add JWT token expiration (1 hour, refresh tokens)
- [ ] Verify Row-Level Security (RLS) policies on Supabase:
  - Users can only access their own receipts
  - No cross-user data leakage
- [ ] Add input validation on all endpoints (file size limits, field length limits)
- [ ] Test for SQL injection, XSS, CSRF vulnerabilities
- [ ] Add HTTPS enforcement (redirect HTTP to HTTPS)
- [ ] Configure secure headers (HSTS, CSP, X-Frame-Options)

#### Acceptance Criteria:
- Rate limiting blocks excessive requests (returns 429 Too Many Requests)
- Supabase RLS prevents cross-user access
- Security scan shows no critical vulnerabilities
- All production traffic uses HTTPS

#### Estimated Time: 1-2 days

---

### 8. Performance Testing (Priority: Medium)

**Status**: 🔴 Not Started

#### Tasks:
- [ ] Test upload performance (1MB, 5MB, 10MB PDFs)
- [ ] Test OCR performance (10-page PDFs)
- [ ] Test export performance (100, 500, 1000 receipts)
- [ ] Measure database query performance (list receipts with pagination)
- [ ] Test concurrent users (10 users uploading simultaneously)
- [ ] Identify bottlenecks (OCR, parser, database, storage)
- [ ] Optimize slow operations (OCR should be async, not blocking HTTP)

#### Acceptance Criteria:
- Upload < 5 seconds for typical receipts (1-2 pages)
- OCR < 10 seconds for typical receipts
- Export < 5 seconds for 100 receipts
- System handles 10 concurrent users without crashes

#### Estimated Time: 1 day

---

### 9. Database Backups & Disaster Recovery (Priority: Medium)

**Status**: 🟡 Partial (Supabase auto-backups enabled)

#### Tasks:
- [ ] Verify Supabase automated backups enabled (daily backups)
- [ ] Test database restore from backup
- [ ] Document disaster recovery procedure:
  1. Restore database from backup
  2. Verify Supabase Storage intact
  3. Redeploy backend if needed
  4. Test critical flows (upload, parse, export)
- [ ] Set up backup monitoring (alerts if backups fail)

#### Acceptance Criteria:
- Daily automated backups confirmed
- Restore tested successfully
- Recovery procedure documented
- Backup monitoring configured

#### Estimated Time: 0.5 days

---

### 10. Analytics & Metrics (Priority: Low)

**Status**: 🔴 Not Started

#### Tasks:
- [ ] Define key metrics to track:
  - Parse success rate (vendor extracted, amount extracted)
  - Review rate (% receipts needing manual review)
  - Correction rate (% receipts corrected by users)
  - Export frequency (exports per user per month)
  - User retention (active users week-over-week)
- [ ] Set up analytics (PostHog, Mixpanel, or custom)
- [ ] Create metrics dashboard
- [ ] Set up weekly metrics reports (email or Slack)

#### Acceptance Criteria:
- Key metrics tracked automatically
- Dashboard shows current parse success rate, review rate
- Weekly reports sent to team

#### Estimated Time: 1 day

---

## Launch Timeline (Estimated)

| Week | Focus | Tasks |
|------|-------|-------|
| **Week 1** | Deployment & Integration | Backend deployment, frontend integration, error handling, rate limiting |
| **Week 2** | Testing & Documentation | Manual smoke testing, documentation, beta user recruitment |
| **Week 3** | Beta Launch | Onboard 10 beta users, collect feedback, monitor errors |
| **Week 4** | Iteration | Fix critical bugs, improve based on feedback, prepare for wider launch |

**Total Time to Beta Launch**: 2-4 weeks

---

## Launch Readiness Criteria (Go/No-Go)

Before launching to beta users, verify:

- ✅ **Backend deployed** and accessible
- ✅ **Frontend integrated** with new endpoints
- ✅ **Manual smoke tests** pass (upload, review, export)
- ✅ **Error tracking** configured (Sentry)
- ✅ **Rate limiting** implemented
- ✅ **Security** validated (RLS, HTTPS, input validation)
- ✅ **Documentation** available (onboarding guide, FAQ)
- ✅ **Beta users** recruited (10 users)
- ✅ **Metrics** tracking configured
- ✅ **Backup** and recovery tested

**If all criteria met → Launch to beta** 🚀

---

## Post-Launch Monitoring (First 2 Weeks)

### Daily Checks:
- Review Sentry errors (any new crashes?)
- Check parse success rate (>80%?)
- Check review rate (<30%?)
- Monitor user feedback (bugs reported?)

### Weekly Checks:
- User retention (are beta users active?)
- Parse accuracy improvements (compare week-over-week)
- Common error patterns (specific vendors failing?)
- Feature requests (what do users want most?)

### Success Metrics (2 weeks post-launch):
- ✅ 8/10 beta users actively using the product
- ✅ Parse success rate >80% (vendor + amount extracted)
- ✅ Review rate <30% (most receipts auto-extract correctly)
- ✅ No critical bugs (crashes, data loss)
- ✅ Positive user feedback ("saves me time", "works well")

**If success metrics met → Plan wider launch**

---

## Phase 2+ Roadmap (Post-Beta)

**Phase 2: Vendor Database** (4-6 weeks)
- Normalize vendor names ("STARBUCKS" → "Starbucks")
- Handle vendor aliases ("Starbucks Coffee" → "Starbucks")
- Build canonical vendor database

**Phase 3: LLM Fallback** (6-8 weeks)
- Use GPT-4 for complex/low-confidence receipts
- Reduce review rate from 30% to 10%
- Improve edge case handling

**Phase 4: ML Model Training** (8-12 weeks)
- Train model on user corrections
- Improve parser from feedback loop
- Personalized vendor recognition

**Phase 5: Mobile App** (12-16 weeks)
- iOS/Android app
- Camera receipt capture
- Push notifications for new receipts

**Phase 6: Enterprise Features** (16-24 weeks)
- SSO (Okta, Google Workspace)
- Audit logs
- Team collaboration
- Accounting integrations (QuickBooks, Xero)

---

## Summary

**Phase 1 Complete ✅** - Parser is production-ready with comprehensive safety validation.

**Next Steps**:
1. Deploy backend to production (1-2 days)
2. Validate frontend integration (2-3 days)
3. Run manual smoke tests (1-2 days)
4. Create documentation (1 day)
5. Recruit beta users (1-2 days)
6. Launch to beta! 🚀

**Estimated Time to Beta Launch**: 2-4 weeks

**After beta launch**, iterate based on user feedback and plan Phase 2+ features.

---

**Document Owner**: Engineering & Product
**Review Cadence**: Weekly during pre-launch
**Last Updated**: 2026-02-12
