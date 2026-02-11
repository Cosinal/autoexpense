# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records documenting significant decisions made during the development of AutoExpense.

## Format

Each ADR follows this structure:
- **Status**: Proposed | Accepted | Deprecated | Superseded
- **Context**: What is the issue we're addressing?
- **Decision**: What are we doing about it?
- **Alternatives Considered**: What other options did we evaluate?
- **Consequences**: What becomes easier or harder because of this decision?
- **References**: Related ADRs, issues, or documentation

## Index

- [ADR-0001](ADR-0001-review-ui-with-ml-training.md) - Review UI with ML Training Data Collection
- [ADR-0002](ADR-0002-semantic-duplicate-detection.md) - Semantic Duplicate Detection Strategy
- [ADR-0003](ADR-0003-person-name-vendor-filtering.md) - Person Name Detection in Vendor Extraction

_More ADRs will be added as architectural decisions are made._

## Naming Convention

ADRs are numbered sequentially: `ADR-NNNN-short-title.md`

## How to Create an ADR

1. Copy the template from an existing ADR
2. Use the next sequential number
3. Fill in all sections thoughtfully
4. Update this README index
5. Commit with the code changes that implement the decision
