# Next 10 Tasks - Revised for Lean Launch

**Updated**: 2026-02-10
**Strategic Focus**: Backend quality and parsing reliability over enterprise features

---

## Strategic Alignment

Based on your direction:
- ✅ **Lean Launch** (6 weeks, not enterprise-ready)
- ✅ **Backend maturity first** (parsing reliability before scaling)
- ✅ **Template legal docs** (no lawyer for now)
- ✅ **Credentials rotated** (security risk resolved)
- ✅ **Lovable migration deferred** (Phase 2+)

**Primary Goal**: Build something users can rely on, not something that scales.

---

## Phase 1: Backend Quality (Weeks 1-3)

### TASK 1: Build Parser Regression Test Suite
- **Priority**: P0 (Foundation for all improvements)
- **Effort**: 3 days
- **Acceptance Criteria**:
  - [ ] Create test suite with 50+ real-world receipt samples
  - [ ] Cover major vendors: Uber, Starbucks, Steam, LinkedIn, Amazon, Walmart
  - [ ] Test edge cases: multi-page PDFs, faded receipts, handwritten notes
  - [ ] Measure baseline accuracy (vendor, amount, date, currency, tax)
  - [ ] Tests run in CI (GitHub Actions or similar)
  - [ ] Document expected accuracy: 90%+ target

**Why First**: Can't improve what you can't measure. Regression suite prevents quality regressions.

---

### TASK 2: Improve Vendor Extraction Accuracy
- **Priority**: P0
- **Effort**: 4 days
- **Acceptance Criteria**:
  - [ ] Analyze failures from regression suite
  - [ ] Add missing vendor patterns (restaurant chains, retail stores, services)
  - [ ] Improve person name detection (reduce false positives)
  - [ ] Better handling of payment processors (Stripe, PayPal, Square)
  - [ ] Test: Vendor accuracy improves from ~75% to 90%+

**Implementation Focus**:
- Add patterns for common vendor formats
- Improve scoring logic (adjust penalties/bonuses)
- Use test suite to validate improvements

---

### TASK 3: Improve Amount Extraction Accuracy
- **Priority**: P0
- **Effort**: 3 days
- **Acceptance Criteria**:
  - [ ] Handle edge cases: negative amounts (refunds), amounts with commas, currency symbols
  - [ ] Better subtotal vs total disambiguation
  - [ ] Improve multi-currency handling
  - [ ] Test: Amount accuracy improves from ~80% to 95%+

**Known Issues**:
- Sometimes extracts subtotal instead of total
- Fails on unusual formatting (e.g., "CA $ 123.45")
- Doesn't handle ranges ("$50-100")

---

### TASK 4: Improve Date Extraction & Disambiguation
- **Priority**: P0
- **Effort**: 2 days
- **Acceptance Criteria**:
  - [ ] Implement locale detection (MM/DD vs DD/MM based on context)
  - [ ] Better handling of ambiguous dates (e.g., 01/02/2026)
  - [ ] Support more date formats (ordinal dates, written months)
  - [ ] Test: Date accuracy improves from ~85% to 95%+

**Implementation**:
- Use `_detect_date_locale()` from parser (already exists but not used)
- Look for country indicators (GST, VAT, currency) to infer format
- Default to MM/DD for North America

---

### TASK 5: Improve Tax Extraction Deduplication
- **Priority**: P1
- **Effort**: 2 days
- **Acceptance Criteria**:
  - [ ] Fix duplicate tax detection (use span position, not text match)
  - [ ] Handle multi-line tax (GST + PST, GST + HST)
  - [ ] Sum taxes correctly (e.g., Sephora: $2.62 GST + $2.62 PST = $5.24)
  - [ ] Test: Tax extraction accuracy 90%+

**Known Issue**: Current deduplication by text match fails when two different taxes have same amount.

---

### TASK 6: Add Comprehensive Error Handling
- **Priority**: P0 (User experience)
- **Effort**: 3 days
- **Acceptance Criteria**:
  - [ ] All parser methods have try-except with specific exceptions
  - [ ] User-friendly error messages (not stack traces)
  - [ ] Log errors with context (receipt_id, user_id, error type)
  - [ ] Retry logic for transient failures (OCR timeouts, API errors)
  - [ ] Test: Error rate <5% on valid receipts

**Implementation**:
- Replace broad `except Exception` with specific exceptions
- Add structured logging (JSON format for easy parsing)
- Return helpful error messages to frontend

---

## Phase 2: Security & Deployment (Weeks 4-5)

### TASK 7: Implement Backend Authentication (Simplified)
- **Priority**: P0 (Security blocker)
- **Effort**: 3 days
- **Acceptance Criteria**:
  - [ ] Add JWT verification middleware (verify_token)
  - [ ] Extract user_id from JWT, not query params
  - [ ] Protect all API routes with Depends(verify_token)
  - [ ] Update frontend to send Authorization header
  - [ ] Test: Requests without JWT return 401

**Note**: Keep it simple - just JWT verification, no complex RBAC or permissions system yet.

---

### TASK 8: Add Rate Limiting & Security Headers
- **Priority**: P0 (Security blocker)
- **Effort**: 1 day
- **Acceptance Criteria**:
  - [ ] Add slowapi rate limiting (100 req/min per user)
  - [ ] Add security headers (HSTS, CSP, X-Frame-Options)
  - [ ] Test: Burst requests trigger 429 rate limit

**Note**: Basic protection, not enterprise-grade. Good enough for beta.

---

### TASK 9: Deploy to Staging (Railway + Vercel)
- **Priority**: P0 (Deployment blocker)
- **Effort**: 2 days
- **Acceptance Criteria**:
  - [ ] Backend deployed to Railway (or Render)
  - [ ] Frontend deployed to Vercel
  - [ ] Environment variables configured (no secrets in code)
  - [ ] Sentry integrated for error tracking
  - [ ] Test: Upload receipt end-to-end on staging

**Note**: Start simple - no auto-scaling, no complex infrastructure. Just get it deployed.

---

## Phase 3: User Experience (Week 6)

### TASK 10: Improve Review/Correction UI
- **Priority**: P1 (User friction)
- **Effort**: 3 days
- **Acceptance Criteria**:
  - [ ] Show raw OCR text in review UI (for debugging)
  - [ ] Better error messages ("Vendor not found" vs "Low confidence")
  - [ ] Faster navigation (keyboard shortcuts: N for next, S for submit)
  - [ ] Show confidence scores for each field
  - [ ] Mobile-friendly layout (responsive tables)

**Note**: Focus on usability, not visual polish. Beta users need functionality, not beauty.

---

## After These 10 Tasks

You will have:
- ✅ **Reliable parsing** (90%+ accuracy on test suite)
- ✅ **Solid error handling** (<5% failure rate)
- ✅ **Basic security** (JWT auth, rate limiting)
- ✅ **Deployed staging** (Railway + Vercel)
- ✅ **Improved UX** (better review UI)

**Next**: Launch to 10 beta users from personal/professional network.

---

## Tasks Deferred (From Original Plan)

**Moved to Phase 2+ (Post-Beta)**:
- Stripe billing integration (not needed for free beta)
- Legal documents (templates sufficient for now)
- Onboarding wizard (manual onboarding for beta)
- Help center (direct support for beta users)
- GDPR deletion (not needed for 10 beta users)

**Moved to Phase 3+ (Conditional)**:
- Enterprise features (SSO, audit logs)
- Accounting integrations (QuickBooks, Xero)
- Advanced analytics
- Lovable frontend migration

---

## Estimated Timeline

### Week 1: Parser Foundation
- Day 1-3: Task 1 (Regression test suite)

### Week 2: Parser Improvements
- Day 1-2: Task 2 (Vendor extraction)
- Day 3-5: Task 3 (Amount extraction)

### Week 3: Parser Refinement
- Day 1-2: Task 4 (Date disambiguation)
- Day 3-4: Task 5 (Tax deduplication)
- Day 5: Task 6 (Error handling - start)

### Week 4: Error Handling & Security
- Day 1: Task 6 (Error handling - complete)
- Day 2-4: Task 7 (Backend auth)
- Day 5: Task 8 (Rate limiting + headers)

### Week 5: Deployment
- Day 1-2: Task 9 (Deploy to staging)
- Day 3-5: Task 10 (Review UI improvements)

### Week 6: Beta Prep & Launch
- Final testing
- Bug fixes
- Launch to 10 beta users

**Total**: 6 weeks with 1 full-time engineer.

---

## Success Metrics (End of 6 Weeks)

### Parser Quality
- Vendor: 90%+ accuracy
- Amount: 95%+ accuracy
- Date: 95%+ accuracy
- Currency: 95%+ accuracy
- Tax: 90%+ accuracy

### System Reliability
- Error rate: <5% on valid receipts
- Uptime: 99%+ (staging)
- No critical security vulnerabilities

### User Validation
- 10 beta users onboarded
- 5+ users actively using (uploading receipts weekly)
- Qualitative feedback collected

---

## Key Principles

1. **Quality over speed** - Ship when it works, not when it's pretty
2. **Simple solutions first** - No over-engineering
3. **Measure before optimizing** - Regression suite drives improvements
4. **Real users validate** - Beta feedback > assumptions

---

**Next Step**: Start Task 1 (Build parser regression test suite).

**Document Owner**: Engineering
**Created**: 2026-02-10
