# Decisions

## 2026-08-01 — keep unit 18 independent

**Decision:** retain no-option passthrough as one bounded upstream change.

**Reason:** selection of the byte-copy path is independent from archive rewrite correctness. Active sparse repair, path normalization, transform semantics, and PAX ID-shift semantics each have separate tests and compatibility concerns.

**Reopen trigger:** current upstream introduces an inseparable refactor of option parsing or removes the copy path.

## 2026-08-01 — preserve numeric zero as no-operation

**Decision:** treat `--strip-components=0` and `--idshift=0` as inactive.

**Reason:** later source logic already uses truthiness, so zero produces no semantic change. Byte-preserving behavior is consistent with that implementation.

**Reopen trigger:** upstream defines explicit zero as a validation or rewrite request with observable behavior.

## 2026-08-01 — transforms remain active when supplied

**Decision:** any supplied `--transform` or `--xform` enters the rewrite path.

**Reason:** deciding whether a transform changes every member would require parsing the archive and defeats the copy-path decision. Caller intent is sufficient.

**Reopen trigger:** upstream adopts a formal option-normalization layer with a different contract.

## 2026-08-01 — regenerate the patch carrier

**Decision:** replace the old fuzzy hunk with an exact hunk generated from blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`.

**Reason:** priority-zero readiness requires application without fuzz or offsets. The old patch applied with fuzz 2; the refreshed patch applies with `--fuzz=0`.

**Supersedes:** the previous hunk header/context in PR #46's retained patch file. The source change itself remains unchanged.

## 2026-08-01 — strengthen active-option coverage

**Decision:** require explicit controls for path, PAX, type, strip, transform, and ID-shift categories.

**Reason:** #397 names all six categories. The prior regression directly proved only transform and ID shift beyond the no-operation matrix.

## 2026-08-01 — state remains ACTIVE

**Decision:** keep the unit `ACTIVE`.

**Reason:** a clean exact-branch test run and current upstream overlap refresh remain. A controlled fork also remains absent.

**Ready trigger:** committed regression passes from a clean checkout, overlap search finds no active equivalent, complete diff review stays bounded, and the upstream-shaped patch applies to the exact current base.

## External-contact decision

External contact remains unauthorized. No issue, pull request, comment, email, review, or patch submission was sent upstream.
