# ADR-0003: Person Name Detection in Vendor Extraction

**Status**: Accepted (Implemented: 2026-02-10)

## Context

When users forward receipt emails to the intake address, the email `sender_name` metadata contains the user's name (e.g., "Jorden Shaw"), not the merchant. The parser was giving email headers the highest confidence score (0.9), causing it to extract customer names as vendors.

This created poor UX where every receipt showed the user's own name as the vendor instead of "Uber", "Anthropic", etc.

## Decision

Implement person name detection with a scoring penalty:

1. **Detection Function**: `_looks_like_person_name()` identifies names matching pattern:
   - 2-3 words, all title case
   - Each word < 15 characters
   - Only alphabetic characters (plus hyphen/apostrophe)
   - Excludes business indicators (Inc, LLC, Clinic, Store, etc.)

2. **Penalty Application**: -0.6 score penalty when:
   - Candidate comes from email header (`from_email_header` or `context_sender_name`)
   - AND matches person name pattern

3. **Effect**:
   - "Jorden Shaw" from email: 0.9 - 0.6 = 0.3
   - "Uber" from body text: 0.84 (unchanged)
   - Uber now wins

## Alternatives Considered

1. **Blacklist user's name specifically**: Requires knowing user name, doesn't scale, misses variations
2. **Ignore email headers entirely**: Loses legitimate merchant emails (e.g., from Uber's sender name)
3. **Require email domain validation**: Complex, doesn't work for forwarded emails
4. **Machine learning classifier**: Overkill for this problem, adds complexity
5. **Prompt user to confirm vendor**: Bad UX, slows down ingestion

## Consequences

### Positive
- Correctly identifies vendors from receipt body over email metadata
- Works for any user name (not hardcoded)
- Simple heuristic, no external dependencies
- Preserves legitimate business names from email headers

### Negative
- False positives: 2-word business names might be flagged (e.g., "Browz Eyeware" initially caught)
- Requires maintenance of business indicator list
- Doesn't handle non-English names well
- Edge case: businesses named after people (e.g., "John's Pizza")

### Risks & Mitigations

**Risk**: Business names flagged as person names
**Mitigation**: Comprehensive business indicator list (Clinic, Eyeware, Store, Restaurant, etc.)

**Risk**: Cultural name patterns not covered
**Mitigation**: Pattern focuses on structure, not specific names. Expand business indicators as needed.

**Risk**: Person-named businesses misclassified
**Mitigation**: Accept this edge case - body text usually has business name elsewhere

## Technical Details

**Business Indicator List** (expanded as needed):
```python
['Inc', 'LLC', 'Ltd', 'Limited', 'Corp', 'Corporation',
 'Clinic', 'Medical', 'Eyeware', 'Eyecare', 'Optical',
 'Pharmacy', 'Restaurant', 'Bar', 'Grill', 'Hotel',
 'Spa', 'Salon', 'Store', 'Shop', 'Cafe', 'Co', 'Company']
```

**Score Calculation** (vendor scoring):
- Base score (0.9 for email header)
- Person name penalty (-0.6 if detected)
- Other structural bonuses/penalties
- Final score clamped to [0.0, 1.0]

## Future Enhancements

- Use ML-based name entity recognition (NER) for more accurate detection
- Learn from user corrections (review UI data)
- Context-aware scoring (e.g., "From: Jorden Shaw" vs "From: support@anthropic.com")
- Domain-based trust (verified sender domains get higher base score)

## References

- Implementation: Commit 4667dbf
- Code: `src/backend/app/utils/scoring.py:_looks_like_person_name()`
- Related: ADR-0001 (review UI allows manual correction when this fails)
- Issue: Anthropic receipt correctly extracted after this fix
