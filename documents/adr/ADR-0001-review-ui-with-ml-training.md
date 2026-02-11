# ADR-0001: Review UI with ML Training Data Collection

**Status**: Accepted (Implemented: 2026-02-10)

## Context

Receipt extraction via OCR and parsing produces uncertain results. Users need a way to correct mistakes, and the system needs to learn from corrections to improve over time.

Initial approach of flagging low-confidence receipts (< 0.7) for review wasn't enough - users couldn't actually correct the mistakes, and we had no mechanism to collect training data.

## Decision

Implement a comprehensive Review UI that:
1. Presents top 3 candidate options (with scores) for uncertain fields
2. Allows custom input as a 4th option
3. Stores all corrections in a `user_corrections` JSONB column for ML training
4. Makes ALL fields editable (not just low-confidence ones)
5. Provides radio button selection + custom input UX

**Key Components:**
- Backend: `/review/pending`, `/review/submit`, `/review/corrections/export` API endpoints
- Parser: Enhanced to capture top 3 candidates via `select_top_*()` functions
- Database: Added `user_corrections` and `corrected_at` columns
- Frontend: Review queue page at `/receipts/review` with candidate selection UI

## Alternatives Considered

1. **Simple text input correction**: Easier to build but loses candidate context and doesn't guide users
2. **Automatic re-training**: More complex, requires ML pipeline infrastructure we don't have yet
3. **Third-party labeling service**: Expensive and doesn't keep data in-house
4. **Only allow corrections on flagged fields**: Too restrictive - users can't fix high-confidence mistakes

## Consequences

### Positive
- Users can correct any extraction mistake
- System collects structured training data (original, corrected, candidates, confidence)
- UX guides users toward likely corrections (faster than typing)
- Foundation for future ML model improvements
- Transparent - users see why parser made its choice

### Negative
- Added complexity to parser (candidate capture + scoring)
- More database columns and API endpoints to maintain
- Frontend state management more complex (radio selections + custom inputs)
- ML training pipeline still needs to be built separately

### Technical Debt Created
- Parser candidate capture has placeholder logic for some fields
- No automated export/training pipeline yet
- Review UI doesn't show OCR text for context
- No analytics on correction patterns

## References

- Implementation: Commits 4667dbf, 4bbe249
- Documentation: `documents/backend/REVIEW_UI_IMPLEMENTATION.md`
- Database migration: `src/backend/migrations/add_user_corrections.sql`
- Related: ADR-0002 (semantic duplicates), ADR-0003 (person name filtering)
