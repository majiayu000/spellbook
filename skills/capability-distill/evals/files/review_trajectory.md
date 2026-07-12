# Redacted code-review trajectory

The repository and contributor identities are intentionally omitted.

1. A PR added a merge gate with a free-form `review_source` string and treated any non-empty value as valid.
2. The reviewer compared three options: document expected values, accept unknown values with a warning, or validate a closed set and fail closed.
3. Evidence showed that a misspelled source already passed the fixture. Because the field controlled merge authorization, the reviewer rejected the documentation-only and warning options.
4. The implementation changed the field to a closed set, treated missing and unknown values as blocked, and added a schema-valid negative fixture for the misspelled value.
5. The reviewer then noticed that self-review could still pass without a recorded reviewer-lane failure. The same fail-closed rule was extended to require that prerequisite evidence.
6. Focused tests and the full gate suite passed; the negative fixtures failed for the intended policy reason rather than for malformed schema.
7. Existing `security-review` guidance already owned generic fail-closed advice, while the repository's merge-gate skill owned the concrete review-source and prerequisite rules.

Outcome: the existing merge-gate skill was updated; no new generic security skill was created.
