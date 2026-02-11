# ADR-0002: Semantic Duplicate Detection Strategy

**Status**: Accepted (Implemented: 2026-02-10)

## Context

Vendors often send the same transaction as multiple attachments (e.g., "Invoice.pdf" and "Receipt.pdf"). These files have different names and potentially different PDF metadata, resulting in different SHA-256 hashes.

The existing file-hash-based deduplication caught identical files but missed semantically identical receipts, creating duplicate entries for users.

## Decision

Implement semantic duplicate detection that checks for existing receipts with matching:
- **Vendor name** (exact match)
- **Amount** (exact match)
- **Date** (exact match)

Requires at least 2 of 3 fields to match. Applied after file-hash check but before receipt creation.

**Implementation:**
- New method: `_check_semantic_duplicate()` in `IngestionService`
- Runs during `_process_source()` after parsing
- Returns `None` (skip) if semantic duplicate found
- Logs the duplicate detection for monitoring

## Alternatives Considered

1. **Fuzzy matching on vendor names**: More complex, risk of false positives
2. **Time-window matching only**: Would miss same-day duplicates from different times
3. **Content-based PDF comparison**: Expensive, requires PDF parsing infrastructure
4. **User prompt on potential duplicates**: Bad UX, shifts burden to user
5. **Amount + date only**: Too loose - different vendors could have same amount/date

## Consequences

### Positive
- Prevents duplicate receipts from multi-attachment emails
- Improves data quality without user intervention
- Simple, fast query (indexed fields)
- Logs duplicates for monitoring and debugging

### Negative
- False positives possible: legitimate transactions with same vendor+amount+date on same day
- Requires all 3 fields to be extracted correctly (if extraction fails, deduplication fails)
- No user notification when duplicates are skipped (silent behavior)
- Edge case: split payments or partial refunds might be flagged

### Risks & Mitigations

**Risk**: Legitimate duplicate transactions (e.g., two $5 coffees from Starbucks same day)
**Mitigation**: Require 2 of 3 match (not 3 of 3) and rely on user review if suspicious

**Risk**: Poor extraction quality causes missed duplicates
**Mitigation**: Improve parser quality over time with ML training data

## Future Enhancements

- Add user notification: "We found a potential duplicate and skipped it"
- Allow user to override: "This is not a duplicate, create anyway"
- Track duplicate rate as a metric
- Consider time-of-day in matching (if available in receipts)

## References

- Implementation: Commit 4667dbf
- Code: `src/backend/app/services/ingestion.py:_check_semantic_duplicate()`
- Related: ADR-0001 (review UI improves extraction quality)
