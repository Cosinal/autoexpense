# AutoExpense: Market-Ready Roadmap

**Version**: 1.0
**Last Updated**: 2026-02-10
**Status**: Active Development → Market-Ready

---

## Executive Summary

**AutoExpense** is a privacy-first expense receipt management tool targeting busy executives who want "set it and forget it" automation for expense tracking. The product currently has a **solid technical foundation** (v0.2.0 MVP) but is **NOT production-ready** due to critical security vulnerabilities and missing business infrastructure.

**Current State**: 30-40% market-ready
**Target State**: Enterprise-grade SaaS product
**Estimated Timeline to Launch**: 8-12 weeks of focused development

### Critical Blockers

🚨 **SECURITY SHOWSTOPPERS** - DO NOT DEPLOY WITHOUT FIXING:
1. **No backend authentication** - API accepts user_id as parameter with no verification
2. **Exposed credentials** - Supabase service keys and Gmail secrets committed to repository
3. **No authorization checks** - Any user can access any other user's receipts
4. **No rate limiting** - API open to abuse and DoS attacks
5. **Missing GDPR compliance** - No account deletion workflow (legal requirement)

**Business Infrastructure Gaps**:
- No billing system (Stripe integration missing)
- No onboarding flow (users don't know how to forward receipts)
- No legal documents (Terms of Service, Privacy Policy)
- No support infrastructure (help desk, status page)
- No marketing website (can't convert visitors to signups)

### Value Proposition

**Target Persona**: Executives and professionals who:
- Forward 10-50+ receipts per month
- Work with accountants/bookkeepers
- Value privacy and data security
- Want minimal setup and maintenance

**Differentiation vs Expensify/Concur/Ramp**:
- **Privacy-first** - No bank/card access required
- **Simple** - Email forwarding only, no complex workflows
- **Individual-focused** - Not designed for teams/approvals
- **Fast setup** - 5 minutes vs 30-60 minutes

**Positioning**: "The Superhuman of expense receipts - minimal, elegant, privacy-first"

### Recommended Approach

**Option A: Launch Lean (6 weeks)** - RECOMMENDED
- Fix critical security issues (authentication, authorization)
- Add Stripe billing + pricing page
- Build basic onboarding (Gmail OAuth, welcome emails)
- Deploy to production with monitoring
- Launch to 10 beta users for validation
- **Goal**: $500-2,000 MRR with first 10-30 paying customers

**Option B: Enterprise-Ready (12 weeks)**
- All items from Option A
- Add legal documents (lawyer-reviewed)
- Implement audit logs, 2FA, SSO
- Build accounting integrations (QuickBooks, Xero)
- Complete SOC 2 Type I audit preparation
- **Goal**: Enterprise sales-ready with $5-10k deal size capability

**Decision Point**: Start with Option A to validate product-market fit, then move to Option B if traction is strong.

---

## Current State Snapshot

### What's Working (v0.2.0)

#### Core Features ✅
- **Email ingestion** - Gmail API forwarding with OAuth 2.0
- **OCR extraction** - Tesseract processing for PDF and images
- **Automatic parsing** - Vendor, amount, date, currency, tax extraction
- **Review UI** - Manual correction with ML training data collection
- **Export** - CSV download with filtering
- **Deduplication** - File-hash + semantic duplicate detection
- **Multi-currency** - CAD, USD, EUR, GBP support

#### Technical Foundation ✅
- FastAPI backend with clean service layer architecture
- Next.js 15 frontend with React 19 and Tailwind CSS
- Supabase backend (PostgreSQL + Storage + Auth)
- Content-addressed storage with SHA-256 hashing
- Row-level security (RLS) policies defined
- Candidate-based extraction with confidence scoring
- ~2,115 lines of test coverage (parser, ingestion, integration)

#### Recent Improvements (v0.2.0 - Feb 2026)
- Review queue for correcting uncertain extractions
- Top 3 candidate options with confidence scores
- User corrections stored for ML training
- Semantic duplicate detection (vendor+amount+date matching)
- Person name detection (prevents extracting customer names as vendors)
- Improved vendor extraction patterns

### Critical Gaps

#### Security & Compliance 🚨 CRITICAL
- ❌ **No backend authentication** - API endpoints trust user_id from client
- ❌ **Exposed secrets** - Service keys in repository (.env files committed)
- ❌ **No authorization** - No user ownership validation on resources
- ❌ **No rate limiting** - Open to API abuse
- ❌ **No security headers** - Missing HSTS, CSP, X-Frame-Options
- ❌ **No CSRF protection** - Vulnerable to cross-site attacks
- ❌ **GDPR gaps** - No account deletion, no data export API
- ❌ **No audit logging** - Cannot track security events
- ❌ **No legal docs** - No ToS, Privacy Policy, or DPA

#### Business Infrastructure ❌
- ❌ **No billing system** - Cannot accept payments (Stripe not integrated)
- ❌ **No pricing page** - Users don't know what it costs
- ❌ **No subscription management** - No free vs paid tier logic
- ❌ **No usage tracking** - Cannot enforce receipt limits
- ❌ **No production hosting** - No deployment configuration
- ❌ **No monitoring** - No Sentry, Datadog, or error tracking
- ❌ **No backup strategy** - Database/storage backup not verified

#### User Experience ⚠️
- ❌ **No onboarding** - Users see blank dashboard, no setup wizard
- ❌ **No Gmail OAuth UI** - Users must manually configure (major friction)
- ❌ **No empty states** - No guidance when no receipts exist
- ❌ **No welcome emails** - No activation/setup instructions
- ❌ **Mobile unusable** - Tables overflow, buttons too small
- ❌ **No settings page** - Cannot change email, password, or preferences
- ❌ **No help center** - No FAQ, troubleshooting guides, or docs

#### Support & GTM ⚠️
- ❌ **No support infrastructure** - No help desk, chat, or ticketing
- ❌ **No status page** - Users can't see if service is down
- ❌ **No marketing website** - Current homepage is functional, not persuasive
- ❌ **No demo video** - Can't see product without signing up
- ❌ **No sales assets** - No deck, ROI calculator, or case studies

### Technical Debt

#### Parser & Extraction
- Placeholder logic in candidate capture for some fields
- No automated ML training pipeline (export is manual)
- OCR normalization applied globally (performance impact)
- Review UI doesn't show raw OCR text for debugging

#### Data Model
- No soft deletes or audit trails
- No data retention/archival policies
- Missing indexes on commonly filtered fields
- No database connection pooling configured

#### Scalability Bottlenecks
- Synchronous OCR processing (30+ seconds blocking)
- No async job queue (Celery configured but unused)
- Gmail polling instead of pub/sub webhooks
- No CDN for file serving
- No caching layer (Redis unused)

#### Frontend Code Quality
- Zero component reusability (every page is 300-600 lines)
- No state management library (prop drilling everywhere)
- No error boundaries
- Zero tests (no Jest, no React Testing Library)
- No loading states or skeletons

### Cost Structure (Current)

**Monthly Operational Costs**: ~$10-30/month (dev environment)
- Supabase Free Tier: $0
- Gmail API: $0 (within free quota)
- Hosting: Local development only

**To Launch (Estimated)**:
- Legal (ToS, Privacy Policy): $2,000-5,000 (one-time)
- Hosting (Railway/Render): $50-200/month
- Monitoring (Sentry + Datadog): $50-150/month
- Support (Intercom/Plain): $79-150/month
- Status Page: $29/month
- Penetration test: $2,000-5,000 (one-time)

**Total One-Time**: $4,000-10,000
**Total Monthly**: $200-500/month
**Break-even**: 14-34 paying customers at $15/month

---

## Market-Ready Criteria Checklist

### 1. Reliability & Infrastructure (40% Complete)

| Requirement | Status | Priority | Notes |
|-------------|--------|----------|-------|
| Production hosting with auto-scaling | ❌ | P0 | Railway/Render deployment needed |
| Monitoring & error tracking | ❌ | P0 | Sentry + Datadog/Prometheus |
| Rate limiting (per-user + global) | ❌ | P0 | 100 req/min per user, 10k global |
| Automated backups (daily) | ❌ | P0 | Database + storage to S3 |
| Health check endpoints | ⚠️ | P0 | Basic /health exists, needs dependency checks |
| CDN for file serving | ❌ | P1 | Cloudflare for receipt files |
| Async job processing | ⚠️ | P1 | Celery configured but not used |
| Staging environment | ❌ | P1 | Separate env for testing |
| Load balancing | ❌ | P2 | Not needed for <1000 users |
| Uptime SLA | ❌ | P2 | 99.5% target |

### 2. Security & Compliance (30% Complete)

| Requirement | Status | Priority | Notes |
|-------------|--------|----------|-------|
| Backend authentication (JWT) | ❌ | P0 | CRITICAL - API is open |
| Authorization checks | ❌ | P0 | CRITICAL - No ownership validation |
| Rotate exposed credentials | ❌ | P0 | CRITICAL - Secrets in repo |
| Security headers | ❌ | P0 | HSTS, CSP, X-Frame-Options |
| CSRF protection | ❌ | P0 | Required for state-changing ops |
| GDPR account deletion | ❌ | P0 | Legal requirement |
| Privacy Policy | ❌ | P0 | Legal requirement |
| Terms of Service | ❌ | P0 | Legal requirement |
| GDPR data export API | ❌ | P1 | JSON format for portability |
| Audit logging | ❌ | P1 | User actions, access logs |
| 2FA/MFA | ❌ | P1 | Enterprise requirement |
| Penetration testing | ❌ | P1 | $2-5k one-time |
| SOC 2 compliance | ❌ | P2 | Enterprise sales |
| SSO (SAML/OIDC) | ❌ | P2 | Enterprise requirement |

### 3. Onboarding & Activation (50% Complete)

| Requirement | Status | Priority | Notes |
|-------------|--------|----------|-------|
| Email verification | ❌ | P0 | Prevent fake signups |
| Onboarding wizard (3 steps) | ❌ | P0 | Verify email → OAuth → test receipt |
| Gmail OAuth UI flow | ❌ | P0 | Major friction point |
| Empty state guidance | ❌ | P0 | Clear CTAs for first-time users |
| Welcome email | ❌ | P0 | Setup instructions + intake address |
| Activation tracking | ❌ | P1 | Measure time-to-first-receipt |
| Mobile-friendly upload | ❌ | P1 | Drag-and-drop or photo capture |
| "Test Receipt" button | ❌ | P1 | Verify OCR works |
| Setup progress indicators | ❌ | P2 | Show completion % |

### 4. Billing & Monetization (0% Complete)

| Requirement | Status | Priority | Notes |
|-------------|--------|----------|-------|
| Stripe integration | ❌ | P0 | Checkout + subscription management |
| Pricing page | ❌ | P0 | Free, Professional, Business, Enterprise |
| Usage tracking | ❌ | P0 | Count receipts per user |
| Subscription plans | ❌ | P0 | Free (10/mo), Pro ($15), Business ($39) |
| Upgrade prompts | ❌ | P0 | When limits reached |
| Billing portal | ❌ | P0 | Stripe Customer Portal |
| Failed payment handling | ❌ | P1 | Dunning emails |
| Invoice generation | ❌ | P1 | For paying customers |
| Annual billing discount | ❌ | P2 | 17% off (industry standard) |

### 5. Documentation (20% Complete)

| Requirement | Status | Priority | Notes |
|-------------|--------|----------|-------|
| Help center | ❌ | P0 | How to forward receipts, troubleshooting |
| "For Accountants" guide | ❌ | P0 | CSV format explanation |
| FAQ page | ❌ | P0 | Common questions |
| Security/privacy whitepaper | ❌ | P1 | Data handling, encryption |
| API docs (Swagger) | ⚠️ | P1 | FastAPI auto-generates, need to enable |
| Video tutorial (5 min) | ❌ | P1 | Loom recording |
| In-app tooltips | ❌ | P2 | First-time user guidance |

### 6. Support & Feedback (10% Complete)

| Requirement | Status | Priority | Notes |
|-------------|--------|----------|-------|
| Help desk (Intercom/Plain) | ❌ | P0 | In-app chat |
| Status page | ❌ | P0 | StatusPage.io for uptime |
| Support SLA | ❌ | P1 | 24-hour response for paid |
| Feedback widget | ❌ | P1 | Canny/Nolt for feature requests |
| Bug reporting form | ❌ | P1 | Auto-create GitHub issues |
| Email support@ forwarding | ❌ | P1 | To help desk |
| Community forum | ❌ | P2 | Peer support |

### 7. Go-to-Market (15% Complete)

| Requirement | Status | Priority | Notes |
|-------------|--------|----------|-------|
| Marketing landing page | ⚠️ | P0 | Exists but not persuasive |
| Demo video (90 sec) | ❌ | P0 | Show product value |
| Pricing comparison | ❌ | P0 | vs Expensify, Concur |
| Demo environment | ❌ | P1 | Pre-populated sample receipts |
| Sales deck (10 slides) | ❌ | P1 | Problem/solution/pricing |
| ROI calculator | ❌ | P1 | "Save X hours/month" |
| SEO content (3 blog posts) | ❌ | P1 | Expense reporting pain points |
| Customer testimonials | ❌ | P2 | Post-launch |
| Case studies | ❌ | P2 | Post-launch with 5+ customers |

---

## Packaging & Positioning

### Pricing Strategy

#### **Tier 1: Personal (Free)**
- **Price**: $0/month
- **Limits**: 10 receipts/month, 90-day retention
- **Features**: Email forwarding, photo uploads, basic OCR, CSV export
- **Target**: Individuals with occasional expenses

#### **Tier 2: Professional ($15/month or $150/year)**
- **Price**: $15/month (or $150/year, save 17%)
- **Limits**: Unlimited receipts, unlimited retention
- **Features**: Everything in Free + priority OCR, email support, export filters
- **Target**: Freelancers, consultants, individual executives
- **Primary monetization tier** - 80% of revenue expected here

#### **Tier 3: Business ($39/month per user)**
- **Price**: $39/month (or $390/year)
- **Limits**: Unlimited, multi-user support
- **Features**: Everything in Pro + accounting integrations (QuickBooks, Xero), SLA, custom categories
- **Target**: Small businesses (5-20 employees)

#### **Tier 4: Enterprise (Custom)**
- **Price**: Starts at $500/month (20+ users)
- **Features**: Everything in Business + SSO, dedicated support, custom integrations, on-premise, audit logs
- **Target**: Mid-market and enterprise companies

### Feature Gating

| Feature | Free | Professional | Business | Enterprise |
|---------|------|--------------|----------|------------|
| Receipts/month | 10 | Unlimited | Unlimited | Unlimited |
| Retention period | 90 days | Unlimited | Unlimited | Unlimited |
| Email support | No | Yes | Priority | Dedicated AM |
| Export formats | CSV | CSV | CSV, JSON | All |
| OCR speed | Standard | Priority | Priority | Fastest |
| Integrations | None | None | QuickBooks, Xero | Custom |
| Team features | No | No | Yes | Yes |
| SSO | No | No | No | Yes |
| Audit logs | No | No | No | Yes |

### Freemium vs Trial Strategy

**Recommendation: Freemium + Optional Trial**
- **Freemium**: 10 receipts/month forever (converts 2-5% to paid)
- **Trial**: 14-day free trial of Professional tier (converts 10-20% to paid)

**Why both?**
- Freemium attracts "tire-kickers" who become long-term free users → word of mouth
- Trial attracts serious buyers evaluating for work use → faster conversion

### Competitive Positioning

| Competitor | Price | Target | Strength | AutoExpense Advantage |
|------------|-------|--------|----------|----------------------|
| Expensify | $5-18/user | SMBs | Full expense workflows | **Privacy** (no bank access) |
| Concur | Custom | Enterprise | ERP integrations | **Simplicity** (no approvals) |
| Ramp | Free | Startups | Corporate cards | **Individual-focused** |
| Brex | Free | Startups | Rewards | **No card required** |
| Shoeboxed | $18-50 | Individuals | Receipt scanning | **Faster** (email vs mail-in) |

**Positioning Statement**: "AutoExpense is the privacy-first alternative to Expensify for executives who want zero-effort expense tracking without connecting their bank accounts."

---

## Phased Roadmap: Now → Next → Later

### PHASE 1: Security Foundation (Weeks 1-3) - CRITICAL

**Goal**: Fix critical security vulnerabilities blocking production deployment

**Epic 1.1: Backend Authentication & Authorization**
- **Priority**: P0 (Blocker)
- **Effort**: 8 engineering days
- **Owner**: Backend engineer

| Task | Acceptance Criteria | Dependencies |
|------|---------------------|--------------|
| Add JWT verification middleware | All API routes require valid Supabase JWT token | None |
| Extract user_id from JWT | user_id comes from verified token, not query params | JWT middleware |
| Add authorization checks | Verify user owns resource before access (receipts, uploads) | JWT middleware |
| Update frontend to send tokens | Add Authorization: Bearer <token> to all API calls | None |
| Write auth integration tests | Test 401/403 responses for missing/invalid tokens | Auth implementation |

**Risk**: Breaking changes to API contract; requires frontend + backend coordination

**Epic 1.2: Secrets Management & Rotation**
- **Priority**: P0 (Blocker)
- **Effort**: 2 engineering days

| Task | Acceptance Criteria | Dependencies |
|------|---------------------|--------------|
| Rotate all Supabase keys | Generate new service_role and anon keys | None |
| Rotate Gmail OAuth credentials | New client_secret and refresh_token | None |
| Remove .env files from repo | .env files only in .gitignore, never committed | None |
| Scan git history for secrets | Use truffleHog/git-secrets, rewrite history if needed | None |
| Set up environment variables in hosting | Railway/Render env vars configured | Deployment setup |

**Risk**: Service downtime during rotation; coordinate with deployment

**Epic 1.3: API Protection**
- **Priority**: P0 (Blocker)
- **Effort**: 3 engineering days

| Task | Acceptance Criteria | Dependencies |
|------|---------------------|--------------|
| Add rate limiting (slowapi) | 100 req/min per user, 10k global; 429 responses | None |
| Add security headers middleware | HSTS, CSP, X-Frame-Options, X-Content-Type-Options | None |
| Add CSRF protection | CSRF token validation on state-changing endpoints | None |
| Configure CORS properly | Explicit allowed origins, no wildcard in prod | Deployment |

**Epic 1.4: Production Deployment**
- **Priority**: P0 (Blocker)
- **Effort**: 5 engineering days
- **Owner**: DevOps/Backend engineer

| Task | Acceptance Criteria | Dependencies |
|------|---------------------|--------------|
| Deploy backend to Railway/Render | Backend accessible at api.autoexpense.io | None |
| Deploy frontend to Vercel/Netlify | Frontend accessible at autoexpense.io | None |
| Set up Sentry error tracking | Errors reported to Sentry dashboard | Deployment |
| Configure Datadog/Prometheus | Basic metrics (latency, error rate, uptime) | Deployment |
| Set up automated daily backups | Supabase DB + storage backed up to S3 | Deployment |
| Add health check endpoint | /health returns 200 with dependency status | None |

**Success Metrics**:
- ✅ No API endpoint accessible without valid JWT
- ✅ Zero secrets in repository (verified by git-secrets)
- ✅ Rate limiting returns 429 when exceeded
- ✅ Security headers present in all responses
- ✅ Backend and frontend deployed to production URLs
- ✅ Errors appearing in Sentry dashboard
- ✅ Uptime monitoring active

**Dependencies**: None (blocking all other work)

---

### PHASE 2: Business Infrastructure (Weeks 4-6) - HIGH PRIORITY

**Goal**: Enable revenue generation and user acquisition

**Epic 2.1: Billing Integration**
- **Priority**: P0 (Revenue blocker)
- **Effort**: 10 engineering days
- **Owner**: Full-stack engineer

| Task | Acceptance Criteria | Dependencies |
|------|---------------------|--------------|
| Integrate Stripe SDK | Stripe API working in backend | None |
| Create subscription products | Free, Pro ($15), Business ($39), Enterprise | Stripe account |
| Build pricing page | Comparison table, FAQs, CTAs | Design mockup |
| Add usage tracking | Count receipts per user per month | Database schema update |
| Implement plan limits | Soft cap at 10 receipts/month for Free | Usage tracking |
| Add "Upgrade" prompts | Show modal when limit reached | Usage tracking |
| Build Stripe webhook handler | Process payment.succeeded, subscription.updated | Stripe integration |
| Set up Stripe Customer Portal | Users can manage billing, invoices, cancel | Stripe integration |
| Add trial logic (optional) | 14-day Professional trial | Subscription management |

**Success Metrics**:
- ✅ User can upgrade from Free → Pro via Stripe Checkout
- ✅ Free users blocked at 10 receipts with upgrade prompt
- ✅ Subscription status synced from Stripe webhooks
- ✅ Users can manage billing in Customer Portal
- ✅ First test payment processed successfully

**Risk**: Stripe integration bugs can break checkout flow; needs thorough testing

**Epic 2.2: Onboarding & Activation**
- **Priority**: P0 (Activation blocker)
- **Effort**: 8 engineering days
- **Owner**: Full-stack engineer

| Task | Acceptance Criteria | Dependencies |
|------|---------------------|--------------|
| Add email verification | Users must verify email before using app | Supabase Auth config |
| Build onboarding wizard | 3-step flow: verify email → OAuth → test receipt | Design mockup |
| Implement Gmail OAuth UI | One-click "Connect Gmail" button with OAuth flow | Google Cloud project setup |
| Add empty state | Show "Upload your first receipt" with clear CTA | None |
| Send welcome email | Instructions for forwarding receipts, intake address | Email service (SendGrid?) |
| Add activation tracking | Track signup → email verified → first receipt | Analytics setup |
| Build mobile-friendly upload | Drag-and-drop or camera capture | None |

**Success Metrics**:
- ✅ 60%+ of signups verify email within 24 hours
- ✅ 40%+ of verified users upload first receipt within 48 hours
- ✅ Gmail OAuth works without manual token generation
- ✅ Mobile users can upload via photo

**Epic 2.3: Legal & Compliance**
- **Priority**: P0 (Legal blocker)
- **Effort**: 6 engineering days + 1-2 weeks for lawyer
- **Owner**: Engineering + legal counsel

| Task | Acceptance Criteria | Dependencies |
|------|---------------------|--------------|
| Draft Privacy Policy | GDPR/CCPA compliant, approved by lawyer | Hire lawyer |
| Draft Terms of Service | Liability caps, governing law, approved by lawyer | Hire lawyer |
| Add ToS/Privacy links | Footer + signup flow | Legal docs finalized |
| Implement ToS acceptance | Checkbox during signup, timestamp stored | Database schema |
| Build account deletion | Delete user + all receipts + files + email records | Database schema |
| Add GDPR data export API | JSON export of all user data | Database queries |

**Success Metrics**:
- ✅ Legal docs reviewed by lawyer
- ✅ Users must accept ToS during signup
- ✅ Account deletion removes all user data
- ✅ GDPR export returns complete user data in JSON

**Dependencies**: Hire lawyer (budget $2-5k)

---

### PHASE 3: Polish & GTM (Weeks 7-9) - LAUNCH PREP

**Goal**: Create compelling user experience and marketing assets

**Epic 3.1: Help Center & Documentation**
- **Priority**: P1 (User success)
- **Effort**: 5 engineering days
- **Owner**: Technical writer + engineer

| Task | Acceptance Criteria | Dependencies |
|------|---------------------|--------------|
| Build help center (10 articles) | How-to guides, troubleshooting, FAQ | None |
| Write "For Accountants" guide | CSV format explanation, export instructions | None |
| Record demo video (5 min) | Loom/ScreenFlow walkthrough of key features | None |
| Enable FastAPI Swagger docs | /docs endpoint publicly accessible | None |
| Add in-app tooltips | First-time user guidance for key features | None |
| Write security whitepaper | Data handling, encryption, privacy practices | None |

**Success Metrics**:
- ✅ 10+ help articles published
- ✅ Demo video embedded on homepage
- ✅ Support tickets decrease after help center launch

**Epic 3.2: Support Infrastructure**
- **Priority**: P1 (User retention)
- **Effort**: 3 engineering days
- **Owner**: Full-stack engineer

| Task | Acceptance Criteria | Dependencies |
|------|---------------------|--------------|
| Add Intercom or Plain.com | In-app chat widget, ticket system | Budget $79-150/month |
| Set up StatusPage.io | Public status page showing uptime, incidents | Budget $29/month |
| Add feedback widget (Canny) | Feature request submission and voting | Budget $50/month |
| Configure support@ email | Forwards to help desk | Help desk integration |
| Define SLA for paid users | 24-hour response time documented | None |

**Success Metrics**:
- ✅ Support tickets resolved within 24 hours (paid users)
- ✅ Status page shows 99%+ uptime
- ✅ Feature requests tracked in Canny

**Epic 3.3: Marketing Website & GTM Assets**
- **Priority**: P1 (Acquisition)
- **Effort**: 8 engineering days + design/copywriting
- **Owner**: Marketing + engineer

| Task | Acceptance Criteria | Dependencies |
|------|---------------------|--------------|
| Redesign landing page | Hero, features, pricing, testimonials, CTAs | Design mockup |
| Add comparison page | AutoExpense vs Expensify vs Concur | Competitive research |
| Write 3 SEO blog posts | "Why execs hate expense reporting", alternatives, tax tips | None |
| Build demo environment | Pre-populated demo account with sample receipts | None |
| Create sales deck (10 slides) | Problem/solution/differentiation/pricing | Design mockup |
| Build ROI calculator | "Save X hours/month = $Y/year" | None |

**Success Metrics**:
- ✅ Landing page conversion rate 2-5% (visitor → signup)
- ✅ Blog posts ranking for target keywords (within 3 months)
- ✅ Demo environment available for prospects

---

### PHASE 4: Enterprise Features (Weeks 10-14) - COMPETITIVE ADVANTAGE

**Goal**: Enable enterprise sales and competitive differentiation

**Epic 4.1: Advanced Security**
- **Priority**: P1 (Enterprise requirement)
- **Effort**: 10 engineering days

| Task | Acceptance Criteria | Dependencies |
|------|---------------------|--------------|
| Add 2FA/MFA | TOTP support via authenticator apps | None |
| Implement audit logging | Track all user actions, access logs, data changes | Database schema |
| Add field-level encryption | Encrypt sensitive fields (amounts, vendors) | Key management setup |
| Commission penetration test | Third-party security assessment, report | Budget $2-5k |
| Build API key management | Generate/revoke API keys for integrations | Database schema |

**Success Metrics**:
- ✅ Users can enable 2FA
- ✅ Audit logs capture all security events
- ✅ Penetration test passes with no critical findings

**Epic 4.2: SSO & Enterprise Identity**
- **Priority**: P1 (Enterprise sales blocker)
- **Effort**: 10 engineering days

| Task | Acceptance Criteria | Dependencies |
|------|---------------------|--------------|
| Add SAML 2.0 support | Works with Okta, Azure AD | None |
| Add OIDC support | Works with Google Workspace | None |
| Build SSO configuration UI | Admins can configure SSO settings | Admin panel |
| Add IP allowlisting | Enterprise feature for network restrictions | Database schema |

**Success Metrics**:
- ✅ Users can log in via Okta/Azure AD
- ✅ SSO tested with at least 2 providers

**Epic 4.3: Accounting Integrations**
- **Priority**: P1 (Business tier feature)
- **Effort**: 15 engineering days

| Task | Acceptance Criteria | Dependencies |
|------|---------------------|--------------|
| Integrate QuickBooks API | Sync receipts as expenses | QuickBooks developer account |
| Integrate Xero API | Sync receipts as bills/expenses | Xero developer account |
| Build integration settings page | Users can connect/disconnect integrations | OAuth flows |
| Add mapping UI | Map receipt categories to accounting categories | None |

**Success Metrics**:
- ✅ Receipts sync to QuickBooks/Xero automatically
- ✅ 10+ beta users successfully use integrations

---

### PHASE 5: Optimization & Scale (Weeks 15-20) - POST-LAUNCH

**Goal**: Improve performance, reliability, and scalability

**Epic 5.1: Performance Optimization**
- **Priority**: P2 (User experience)
- **Effort**: 12 engineering days

| Task | Acceptance Criteria | Dependencies |
|------|---------------------|--------------|
| Async OCR processing | Move OCR to background queue (Celery/Redis) | Infrastructure setup |
| Add CDN for files | Cloudflare CDN for receipt file serving | CDN account |
| Implement caching | Redis cache for frequent queries | Redis setup |
| Add database connection pooling | Configure pgBouncer or SQLAlchemy pooling | Database config |
| Optimize large file uploads | Chunked uploads, progress indicators | Frontend + backend |

**Success Metrics**:
- ✅ OCR processing < 10 seconds perceived latency
- ✅ File serving latency < 200ms (p95)
- ✅ API response times < 500ms (p95)

**Epic 5.2: Advanced Features**
- **Priority**: P2 (Differentiation)
- **Effort**: 20 engineering days

| Task | Acceptance Criteria | Dependencies |
|------|---------------------|--------------|
| Add receipt categorization | Auto-tag receipts (meals, travel, office, etc.) | ML model training |
| Build bulk operations | Select multiple receipts → export/delete/tag | Frontend UI |
| Add search functionality | Full-text search on vendor, amount, date | Database indexes |
| Build analytics dashboard | Spending by category, vendor, time period | Data aggregation |
| Add email templates | Custom email formatting for forwarded receipts | Email parser |

**Success Metrics**:
- ✅ Receipt categorization accuracy > 80%
- ✅ Users use bulk operations 20%+ of the time
- ✅ Search returns results in < 500ms

---

## Risk Register

### Critical Risks (May Block Launch)

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|------------|-------|
| **Authentication bugs cause data leaks** | Medium | Critical | Comprehensive security testing, penetration test | Security engineer |
| **Legal docs inadequate for GDPR** | Medium | Critical | Hire experienced SaaS lawyer, not templates | Legal |
| **Stripe integration breaks payment flow** | Low | Critical | Staging environment testing, Stripe test mode | Backend engineer |
| **Gmail API quota exceeded** | Low | High | Monitor usage, request quota increase, add pub/sub | Backend engineer |
| **OCR accuracy too low (< 70%)** | Medium | High | Set expectations, build review UI (done), ML improvements | ML engineer |
| **Users can't set up Gmail forwarding** | High | High | Build OAuth UI (Phase 2), provide clear instructions | Full-stack |

### High Risks (May Impact GTM Timeline)

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|------------|-------|
| **Price point too high ($15/month)** | Medium | High | Strong freemium tier, trial, validate with beta users | Product |
| **Hosting costs higher than expected** | Low | Medium | Start with managed services, optimize later | DevOps |
| **Competitors copy privacy positioning** | Low | Medium | Move fast, build brand, focus on UX simplicity | Product |
| **Low conversion rate (< 2%)** | Medium | High | A/B test landing page, improve onboarding, testimonials | Marketing |
| **Enterprise sales cycle too long** | High | Medium | Focus on Individual/SMB for quick wins first | Sales |

### Medium Risks (Manageable)

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|------------|-------|
| **Support volume overwhelming** | Medium | Medium | Self-service help center, chatbot, tiered SLA | Support |
| **Technical debt slows feature development** | High | Medium | Allocate 20% time for refactoring, address Phase 5 | Engineering |
| **Key dependencies have breaking changes** | Low | Medium | Pin versions, test updates in staging | DevOps |

---

## Dependencies Between Epics

```
Phase 1 (Security Foundation) - BLOCKING ALL
├── Epic 1.1 (Auth) ──────────────┬──→ Phase 2 (Business)
├── Epic 1.2 (Secrets) ───────────┤
├── Epic 1.3 (API Protection) ────┤
└── Epic 1.4 (Deployment) ────────┘

Phase 2 (Business Infrastructure)
├── Epic 2.1 (Billing) ───────────────→ Revenue possible
├── Epic 2.2 (Onboarding) ────────────→ Activation possible
└── Epic 2.3 (Legal) ─────────────────→ Compliance ✅

Phase 3 (Polish & GTM) - Can parallelize
├── Epic 3.1 (Docs) ──────────────────→ User success
├── Epic 3.2 (Support) ───────────────→ Retention
└── Epic 3.3 (Marketing) ─────────────→ Acquisition

Phase 4 (Enterprise) - Can run concurrently
├── Epic 4.1 (Security) ──────────────→ Enterprise trust
├── Epic 4.2 (SSO) ───────────────────→ Enterprise sales
└── Epic 4.3 (Integrations) ──────────→ Business tier value

Phase 5 (Optimization) - Post-launch only
├── Epic 5.1 (Performance) ───────────→ Scale to 1000+ users
└── Epic 5.2 (Advanced Features) ─────→ Competitive advantage
```

---

## Key Metrics to Track (Post-Launch)

### Acquisition
- **Website visitors → Signups** (target: 2-5% conversion)
- **Organic vs paid traffic mix**
- **Cost per acquisition (CPA)** (target: < $50)

### Activation
- **Signups → Email verified** (target: 60-70%)
- **Email verified → First receipt** (target: 40-60%)
- **Time to first receipt** (target: < 24 hours)

### Engagement
- **Receipts per user per month** (target: 15-20 for paid users)
- **DAU/MAU ratio** (target: 0.1-0.2 for monthly use case)
- **Weekly active users (WAU)**

### Retention
- **Month 1 → Month 2 retention** (target: 60-70%)
- **Month 1 → Month 6 retention** (target: 30-40%)
- **Churn rate** (target: < 5% monthly for paid)

### Revenue
- **Free → Paid conversion rate** (target: 2-5%)
- **Trial → Paid conversion rate** (target: 10-20%)
- **Monthly recurring revenue (MRR)**
- **Average revenue per user (ARPU)** (target: $12-15)
- **Customer lifetime value (LTV)** (target: $180+)

### Support
- **Tickets per 100 users** (target: < 5)
- **Time to first response** (target: < 2 hours)
- **Customer satisfaction score (CSAT)** (target: 90%+)

---

## Go-to-Market Readiness

### Packaging
- ✅ **Pricing defined**: Free, Pro ($15), Business ($39), Enterprise (custom)
- ❌ **Free tier value**: 10 receipts/month (needs implementation)
- ❌ **Paid tier differentiation**: Priority OCR, integrations (needs implementation)
- ❌ **Enterprise features**: SSO, audit logs, custom integrations (Phase 4)

### Positioning
- ✅ **Value prop clear**: Privacy-first alternative to Expensify
- ✅ **Target persona defined**: Busy executives, consultants, freelancers
- ✅ **Differentiation**: No bank access, simple email forwarding, individual-focused
- ❌ **Proof points**: No testimonials, case studies (post-launch)

### Demo Assets
- ❌ **Demo video**: 90-second walkthrough (Phase 3)
- ❌ **Demo environment**: Pre-populated sample data (Phase 3)
- ❌ **Sales deck**: 10 slides for outbound sales (Phase 3)
- ❌ **ROI calculator**: "Save X hours/month" (Phase 3)

### Marketing Channels
- ❌ **Product Hunt launch**: Requires polished product (Phase 3)
- ❌ **SEO content**: 3 blog posts (Phase 3)
- ❌ **Email waitlist**: Capture early interest (Quick win)
- ❌ **Outbound sales**: LinkedIn, cold email (Phase 4 - Enterprise)

### Beta Launch Checklist

Before launching to first 10 beta users:
- ✅ Phase 1 complete (security foundation)
- ✅ Phase 2 Epic 2.1 complete (billing)
- ✅ Phase 2 Epic 2.2 complete (onboarding)
- ✅ Phase 2 Epic 2.3 complete (legal)
- ⚠️ Phase 3 Epic 3.1 partial (minimum docs: FAQ, "How to" guide)
- ⚠️ Phase 3 Epic 3.2 partial (email support only, no help desk yet)
- ❌ Phase 3 Epic 3.3 (nice-to-have for beta)

---

## Next Steps

### Immediate Actions (This Week)
1. **STOP sharing repository** - Contains exposed credentials
2. **Rotate all credentials** - Assume compromised
3. **Commit to Launch Lean (6 weeks) or Enterprise-Ready (12 weeks)** - Decision required
4. **Hire SaaS lawyer** - For ToS, Privacy Policy ($2-5k budget)
5. **Set up staging environment** - For testing before production

### Week 1-2: Security Foundation
1. Implement backend authentication (Epic 1.1)
2. Rotate secrets and remove from repo (Epic 1.2)
3. Add API protection (Epic 1.3)
4. Deploy to production hosting (Epic 1.4)

### Week 3-4: Business Infrastructure
1. Integrate Stripe billing (Epic 2.1)
2. Build onboarding wizard (Epic 2.2)
3. Finalize legal documents (Epic 2.3)

### Week 5-6: Polish & Launch Prep
1. Build help center (Epic 3.1)
2. Add support infrastructure (Epic 3.2)
3. Launch to 10 beta users
4. Measure activation rate and gather feedback

### Decision Point: Continue to Enterprise-Ready?
- **If 5+ beta users convert to paid** → Proceed to Phase 4 (Enterprise features)
- **If < 2 beta users pay** → Pivot or reassess product-market fit
- **If feedback is strong but no conversions** → Fix pricing/positioning

---

## Appendix

### Architecture Decision Records (ADRs)
See `/documents/adr/` for detailed technical decisions:
- [ADR-0001: Review UI with ML Training Data Collection](documents/adr/ADR-0001-review-ui-with-ml-training.md)
- [ADR-0002: Semantic Duplicate Detection Strategy](documents/adr/ADR-0002-semantic-duplicate-detection.md)
- [ADR-0003: Person Name Detection in Vendor Extraction](documents/adr/ADR-0003-person-name-vendor-filtering.md)

### Changelog
See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

### System Architecture
See [SYSTEM_OVERVIEW.md](documents/SYSTEM_OVERVIEW.md) for architecture diagrams and data flows.

### Module Map
See [MODULE_MAP.md](documents/MODULE_MAP.md) for codebase navigation guide.

### Backlog
See [BACKLOG.md](documents/BACKLOG.md) for non-critical feature ideas.

---

**Last Updated**: 2026-02-10
**Document Owner**: Engineering & Product Leadership
**Review Cadence**: Weekly during active development; monthly post-launch
