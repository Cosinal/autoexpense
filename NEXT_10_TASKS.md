# Next 10 Highest-Leverage Tasks

**Generated**: 2026-02-10
**Context**: Critical path to market-ready (6-week launch or 12-week enterprise-ready)

---

## Critical Decisions Required (Answer These First)

### 🔴 DECISION 1: Launch Strategy
**Question**: Launch Lean (6 weeks) or Enterprise-Ready (12 weeks)?

**Option A: Launch Lean** (Recommended)
- **Timeline**: 6 weeks
- **Goal**: 10-30 paying customers, validate product-market fit
- **Cost**: $4,000-6,000 one-time + $200-350/month
- **Trade-offs**: No SOC 2, no enterprise features (SSO, audit logs)
- **Next**: If successful → proceed to enterprise features

**Option B: Enterprise-Ready**
- **Timeline**: 12 weeks
- **Goal**: Enterprise sales-ready, mid-market customers
- **Cost**: $10,000-15,000 one-time + $350-500/month
- **Trade-offs**: Longer time to revenue, higher upfront investment
- **Next**: Can sell to companies with 50-500 employees

**Recommendation**: Start with Option A. You don't know if executives will pay $15/month until you ask. Validate demand first, then invest in enterprise features.

---

### 🔴 DECISION 2: Legal Approach
**Question**: Use legal templates or hire lawyer?

**Option A: Templates** (Fast)
- Use Termly.io, Iubenda, or similar ($50-100/month)
- Generate ToS, Privacy Policy from templates
- **Risk**: May not be GDPR/CCPA compliant, vulnerable in litigation
- **Timeline**: 1-2 days
- **Cost**: $50-100/month

**Option B: Hire Lawyer** (Proper)
- Work with SaaS attorney to draft custom documents
- Proper GDPR/CCPA compliance
- **Timeline**: 1-2 weeks (lawyer availability)
- **Cost**: $2,000-5,000 one-time
- **Benefit**: Peace of mind, defensible in court

**Recommendation**: Option A for initial beta (10 users), Option B before public launch or when accepting payments at scale.

---

### 🔴 DECISION 3: Secrets Exposure Response
**Question**: How aggressively to respond to exposed credentials?

**Context**: Supabase service keys and Gmail OAuth secrets are committed to the repository. This is a **CRITICAL security vulnerability**.

**Immediate Actions Required**:
1. **Rotate ALL credentials NOW** (Supabase keys, Gmail OAuth)
2. **Audit git history** for secrets (use truffleHog or git-secrets)
3. **Determine blast radius**: Who has cloned the repo? Is it public?

**Options**:
- **If repo is private + few collaborators**: Rotate keys, document incident, move on
- **If repo has been shared widely**: Consider repo history rewrite (risky), assume keys compromised

**Question**: Is this repo private or public? How many people have access?

---

### 🔴 DECISION 4: Hosting Platform
**Question**: Which hosting platform for production deployment?

**Backend Options**:
- **Railway** - Easiest ($5-50/month), auto-deploy from GitHub, built-in metrics
- **Render** - Similar to Railway ($7-85/month), good performance
- **Fly.io** - More control ($10-100/month), closer to bare metal
- **AWS ECS/Fargate** - Enterprise-grade ($50-200/month), requires more setup

**Frontend Options**:
- **Vercel** - Best Next.js support (free tier → $20/month)
- **Netlify** - Alternative to Vercel (free tier → $19/month)

**Recommendation**: Railway (backend) + Vercel (frontend) for fastest setup. Can migrate to AWS later if needed.

---

### 🔴 DECISION 5: Beta User Acquisition
**Question**: Where will you get your first 10 beta users?

**Options**:
1. **Your network**: Friends, colleagues, LinkedIn connections (easiest)
2. **Online communities**: Indie Hackers, Reddit r/SaaS, Hacker News (Show HN)
3. **Direct outreach**: Cold email to executives at target companies
4. **Paid ads**: Google Ads, LinkedIn Ads ($500-1,000 budget)

**Recommendation**: Start with your network for fastest validation. If 5+ people you know won't pay, product needs work.

---

## Next 10 Tasks (Prioritized)

### Phase 1: Security Foundation (Week 1-2)

#### **TASK 1: Rotate Exposed Credentials** ⚠️ CRITICAL
- **Priority**: P0 (Blocker - DO IMMEDIATELY)
- **Owner**: Engineering lead
- **Effort**: 2-3 hours
- **Acceptance Criteria**:
  - [ ] Generate new Supabase service_role key and anon key
  - [ ] Generate new Gmail OAuth client_secret
  - [ ] Re-authorize Gmail API to get new refresh_token
  - [ ] Update all .env files (DO NOT commit)
  - [ ] Verify old keys no longer work
  - [ ] Document incident in security log

**Why First**: Exposed credentials are a ticking time bomb. Anyone with repo access can wipe your database or read all emails. Fix immediately before deploying.

---

#### **TASK 2: Implement Backend Authentication (JWT Verification)**
- **Priority**: P0 (Blocker)
- **Owner**: Backend engineer
- **Effort**: 5 engineering days
- **Acceptance Criteria**:
  - [ ] Add JWT verification middleware to FastAPI
  - [ ] Extract `user_id` from verified Supabase JWT (not query param)
  - [ ] Protect all routes with `Depends(verify_token)`
  - [ ] Update frontend to send `Authorization: Bearer <token>` header
  - [ ] Test: Requests without valid JWT return 401 Unauthorized
  - [ ] Test: Requests with invalid user_id in JWT return 403 Forbidden
  - [ ] Write integration tests for auth flow

**Implementation Hint**:
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from supabase import create_client

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    try:
        # Verify JWT with Supabase
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        user = supabase.auth.get_user(token)
        return user.id  # Return verified user_id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

# Use in routes
@router.get("/receipts")
async def list_receipts(user_id: str = Depends(verify_token)):
    # user_id is now verified from JWT
    pass
```

**Why Second**: Without authentication, the API is completely open. Any user can access any other user's data. This is a **CRITICAL** security vulnerability blocking all production use.

---

#### **TASK 3: Add API Rate Limiting**
- **Priority**: P0 (Blocker)
- **Owner**: Backend engineer
- **Effort**: 2 engineering days
- **Acceptance Criteria**:
  - [ ] Install slowapi (`pip install slowapi`)
  - [ ] Add rate limiting middleware to FastAPI
  - [ ] Set per-user limit: 100 requests/minute
  - [ ] Set global limit: 10,000 requests/minute
  - [ ] Return 429 Too Many Requests when exceeded
  - [ ] Test: Burst of 150 requests → 50 are rate-limited
  - [ ] Add rate limit headers (X-RateLimit-Remaining, X-RateLimit-Reset)

**Implementation Hint**:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@router.post("/upload")
@limiter.limit("10/minute")  # 10 uploads per minute
async def upload_receipt(...):
    pass
```

**Why Third**: Without rate limiting, a single malicious user can DoS the entire service. Upload endpoint is especially vulnerable (expensive OCR processing).

---

#### **TASK 4: Add Security Headers**
- **Priority**: P0 (Blocker)
- **Owner**: Backend engineer
- **Effort**: 1 engineering day
- **Acceptance Criteria**:
  - [ ] Add security headers middleware to FastAPI
  - [ ] Set `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  - [ ] Set `X-Frame-Options: DENY`
  - [ ] Set `X-Content-Type-Options: nosniff`
  - [ ] Set `X-XSS-Protection: 1; mode=block`
  - [ ] Set `Content-Security-Policy: default-src 'self'`
  - [ ] Verify headers in production: `curl -I https://api.autoexpense.io`

**Implementation Hint**:
```python
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

**Why Fourth**: Security headers protect against common web vulnerabilities (XSS, clickjacking, MIME sniffing). Industry standard for production applications.

---

#### **TASK 5: Deploy to Production (Railway + Vercel)**
- **Priority**: P0 (Blocker)
- **Owner**: DevOps/Backend engineer
- **Effort**: 3 engineering days
- **Acceptance Criteria**:
  - [ ] Create Railway account, connect GitHub repo
  - [ ] Configure backend deployment (Python, Uvicorn)
  - [ ] Set environment variables in Railway (Supabase keys, Gmail secrets)
  - [ ] Deploy backend to https://api.autoexpense.io
  - [ ] Create Vercel account, connect GitHub repo
  - [ ] Deploy frontend to https://autoexpense.io
  - [ ] Update frontend .env: `NEXT_PUBLIC_API_URL=https://api.autoexpense.io`
  - [ ] Test: Upload a receipt end-to-end on production
  - [ ] Set up Sentry for error tracking (backend + frontend)
  - [ ] Configure Datadog or Prometheus for basic metrics

**Why Fifth**: Can't validate product-market fit without a deployed product. Production deployment enables beta user testing.

---

### Phase 2: Business Infrastructure (Week 3-4)

#### **TASK 6: Integrate Stripe Billing**
- **Priority**: P0 (Revenue blocker)
- **Owner**: Full-stack engineer
- **Effort**: 8 engineering days
- **Acceptance Criteria**:
  - [ ] Create Stripe account, get API keys
  - [ ] Install Stripe SDK (`pip install stripe`, `npm install @stripe/stripe-js`)
  - [ ] Create subscription products in Stripe: Free (10 receipts), Pro ($15), Business ($39)
  - [ ] Build pricing page: `/pricing` with comparison table
  - [ ] Implement Stripe Checkout flow (frontend → backend → Stripe)
  - [ ] Add webhook handler: `POST /stripe/webhook` (process payment events)
  - [ ] Store subscription status in database: `subscriptions` table
  - [ ] Implement usage tracking: count receipts per user per month
  - [ ] Block Free users at 10 receipts with "Upgrade" modal
  - [ ] Test: Complete full checkout flow in test mode
  - [ ] Test: Subscription lifecycle (create, update, cancel, renew)

**Why Sixth**: Can't generate revenue without billing. Stripe integration is required to accept payments and enforce plan limits.

---

#### **TASK 7: Build Onboarding Wizard**
- **Priority**: P0 (Activation blocker)
- **Owner**: Full-stack engineer
- **Effort**: 5 engineering days
- **Acceptance Criteria**:
  - [ ] Enable email verification in Supabase Auth settings
  - [ ] Build 3-step onboarding wizard: `/onboarding`
    - Step 1: Verify email (send verification link)
    - Step 2: Connect Gmail (OAuth flow with "Connect Gmail" button)
    - Step 3: Test receipt (upload sample receipt or send email)
  - [ ] Show progress indicator (1/3, 2/3, 3/3)
  - [ ] Add empty state on `/receipts`: "Upload your first receipt" CTA
  - [ ] Send welcome email after signup with intake address
  - [ ] Track activation funnel: signup → email verified → first receipt
  - [ ] Test: New user completes onboarding in < 5 minutes

**Why Seventh**: Users are lost without onboarding. Clear step-by-step guidance improves activation rate from ~20% to ~60%.

---

#### **TASK 8: Draft Legal Documents (ToS + Privacy Policy)**
- **Priority**: P0 (Legal blocker)
- **Owner**: Engineering + legal counsel
- **Effort**: 3 engineering days + 1-2 weeks lawyer time
- **Acceptance Criteria**:
  - [ ] **DECISION REQUIRED**: Templates (Termly.io) or hire lawyer?
  - [ ] Draft Privacy Policy (GDPR/CCPA compliant)
  - [ ] Draft Terms of Service (liability caps, governing law)
  - [ ] Add links to footer: `/privacy`, `/terms`
  - [ ] Require ToS acceptance during signup (checkbox + timestamp)
  - [ ] Store acceptance in database: `users.tos_accepted_at`
  - [ ] Test: Cannot sign up without checking ToS box

**Why Eighth**: Accepting payments or collecting EU user data without proper legal docs is illegal (GDPR violation). Must have before public launch.

---

#### **TASK 9: Implement GDPR Account Deletion**
- **Priority**: P0 (Legal blocker)
- **Owner**: Backend engineer
- **Effort**: 3 engineering days
- **Acceptance Criteria**:
  - [ ] Add "Delete Account" button in settings page
  - [ ] Build confirmation modal: "Are you sure? This cannot be undone."
  - [ ] Implement `DELETE /account` endpoint
  - [ ] Delete cascade:
    - [ ] Delete all user receipts from database
    - [ ] Delete all receipt files from Supabase Storage
    - [ ] Delete all processed_emails records
    - [ ] Delete review_candidates records
    - [ ] Delete user account from auth.users
  - [ ] Send confirmation email: "Your account has been deleted"
  - [ ] Test: Account deletion removes ALL user data
  - [ ] Test: Deleted user cannot log in

**Why Ninth**: GDPR legally requires "right to erasure". Cannot operate in EU without this feature. Low effort, high legal risk if missing.

---

#### **TASK 10: Build Help Center (Minimum Docs)**
- **Priority**: P1 (User success)
- **Owner**: Technical writer + engineer
- **Effort**: 3 engineering days
- **Acceptance Criteria**:
  - [ ] Create help center page: `/help`
  - [ ] Write 5 essential articles:
    1. How to forward receipts (with screenshots)
    2. What receipt formats are supported (PDF, JPG, PNG)
    3. How to export for your accountant (CSV format explanation)
    4. Why isn't my receipt parsing correctly? (troubleshooting)
    5. How do I delete my account?
  - [ ] Add FAQ section on landing page (common questions)
  - [ ] Add "Help" link in header/footer
  - [ ] Test: User can find answer to common question in < 2 minutes

**Why Tenth**: Users will get stuck without documentation. Self-service help reduces support burden and improves retention.

---

## After These 10 Tasks

You will have:
- ✅ **Secure backend** (authentication, rate limiting, security headers)
- ✅ **Deployed product** (production URLs, monitoring)
- ✅ **Billing system** (Stripe, pricing page, plan enforcement)
- ✅ **User onboarding** (wizard, empty states, welcome email)
- ✅ **Legal compliance** (ToS, Privacy Policy, account deletion)
- ✅ **Basic support** (help center, FAQ)

**Next**: Launch to 10 beta users, measure activation and conversion, gather feedback.

**Success Metrics**:
- 60%+ of beta users activate (upload first receipt)
- 20%+ of beta users convert to paid (after 14-day trial or free tier exhaustion)
- Support tickets < 5 per user (good self-service docs)

---

## Tasks NOT on This List (But Seem Important)

### Why These Are Deferred:

**"Build mobile app"** → Desktop web is sufficient for exec persona; mobile-responsive web is P1, native app is P3

**"Add QuickBooks integration"** → Phase 4 (Enterprise), not needed for individual users

**"Implement SSO"** → Phase 4 (Enterprise), not needed for launch

**"Build analytics dashboard"** → Phase 5 (Post-launch), nice-to-have

**"Add receipt categorization"** → Phase 5 (Post-launch), can be done manually for now

**"Refactor parser code"** → Phase 5 (Post-launch), current parser works well enough (see BACKLOG.md)

---

## Estimated Timeline

### Week 1 (Security Foundation):
- Day 1: Task 1 (Rotate credentials) - 3 hours
- Day 1-5: Task 2 (Backend auth) - 5 days
- Day 3-4: Task 3 (Rate limiting) - 2 days

### Week 2 (Security + Deployment):
- Day 1: Task 4 (Security headers) - 1 day
- Day 2-4: Task 5 (Production deployment) - 3 days
- Day 5: Testing, fixes

### Week 3 (Billing + Onboarding):
- Day 1-5: Task 6 (Stripe billing) - 5 days (start)

### Week 4 (Billing + Onboarding):
- Day 1-3: Task 6 (Stripe billing cont.) - 3 days
- Day 4-5: Task 7 (Onboarding wizard) - 2 days (start)

### Week 5 (Onboarding + Legal):
- Day 1-3: Task 7 (Onboarding wizard cont.) - 3 days
- Day 3-5: Task 8 (Legal docs) - Start drafting
- Day 4-5: Task 9 (GDPR deletion) - 2 days (start)

### Week 6 (Legal + Docs):
- Day 1: Task 9 (GDPR deletion cont.) - 1 day
- Day 2-4: Task 10 (Help center) - 3 days
- Day 5: Final testing, bug fixes

**Total**: 6 weeks (assuming 1 full-time engineer, no blockers)

With 2 engineers working in parallel, can compress to **4 weeks**.

---

## Risk Mitigation

### Task 1-2 are blockers for everything else
- If Task 2 (auth) takes longer than expected, entire timeline slips
- **Mitigation**: Allocate best backend engineer, prioritize above all else

### Lawyer availability for Task 8
- Lawyers may take 2-4 weeks to respond/draft
- **Mitigation**: Start legal outreach NOW (parallel track), use templates as fallback

### Stripe integration complexity (Task 6)
- Webhooks can be tricky (signature verification, idempotency)
- **Mitigation**: Use Stripe's official libraries, follow docs carefully, test in test mode extensively

---

## Success Criteria (After 10 Tasks)

**Security**: ✅
- Backend requires valid JWT for all requests
- No credentials in repository
- Rate limiting active
- Security headers present

**Revenue**: ✅
- Users can upgrade to paid plans
- Stripe webhooks processing payments
- Usage limits enforced

**Activation**: ✅
- Users can complete onboarding in < 5 minutes
- Empty states guide new users
- Help center reduces support burden

**Compliance**: ✅
- Legal documents (ToS, Privacy Policy)
- GDPR account deletion works
- ToS acceptance tracked

**Production-Ready**: ✅
- Backend deployed to Railway
- Frontend deployed to Vercel
- Monitoring active (Sentry, Datadog)

---

**Next Step**: Answer the 5 critical decisions, then start Task 1 (rotate credentials) immediately.

**Document Owner**: Engineering & Product Leadership
**Created**: 2026-02-10
