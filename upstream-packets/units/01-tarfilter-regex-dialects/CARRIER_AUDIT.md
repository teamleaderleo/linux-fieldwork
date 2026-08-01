# Carrier audit

Audit date: 2026-08-01  
Unit: issue #397, unit 01  
External contact: none; authorization remains false

## Audit rule

The audit followed the canonical unit record and the implementation/test prerequisites until linked records crossed into explicitly separate defect units. It retained exact heads for source-bearing PRs and read issue records that define the scope boundaries.

## Canonical unit carriers

| Carrier | Role | Result |
| --- | --- | --- |
| issue #397 unit 01 | priority, ready gate, and authority | unit remains `ACTIVE` |
| issue #212 | canonical release-candidate record and draft | current-upstream rebase/test remains the technical gate |
| PR #151 | core dialect translator | canonical core implementation carrier |
| PR #202 | Python-only `(?...)` repair | closed component carrier, behavior consolidated later |
| PR #216 | malformed interval and unmatched-close repairs | canonical repaired internal head |
| PR #113 | GNU tar 1.35 characterization | executable negative-control carrier |
| PR #211 | upstream issue/MR draft and release desk | draft/evidence carrier |

## Prerequisite transform chain

### Root semantic record — issue #36

Issue #36 records the broader mismatch between GNU tar/sed transform semantics and the direct Python implementation. It identifies replacement count and `&` behavior as early defects and leaves the regex dialect slice to later records.

The issue body contains a historical source statement naming `josch/mmdebstrap` `main`, `tarfilter` commit `87b9b385b3` from 2024-09-13, and Debian snapshot `1.5.7-3`. This is retained as historical carrier evidence only. The later canonical release record #212 names the canonical Salsa project, and issue #397 requires a fresh current canonical base. Neither historical identity satisfies the current-upstream gate.

### Replacement semantics — issue #51 and PR #56

- issue #51 demonstrates Python's global-by-default replacement versus GNU first-only default and rejection of GNU `g` flag combinations;
- PR #56 head `640f414cb18cf47b3e803856392c720414bea333`, merge `ff3c9458cee438d16f8d99ca9e2e9b843d3766fe`, implements first/global selection, `i`/`g`, whole-match `&`, and escaped replacement handling;
- PR #56 explicitly retains Python pattern syntax as an evidence limit, which the unit 01 dialect translator later resolves for the characterized subset.

Classification: predecessor source behavior folded into the target-scope prerequisite patch state; broader replacement case-conversion remains outside unit 01.

### Path/link/PAX precursor — issue #25 and PR #48

- issue #25 demonstrates unchanged hard-link targets and stale PAX `path`/`linkpath` after path rewrites;
- PR #48 head `25f6bcda2a807a8901b3ff3e34f5581d6f057877`, merge `4d2550eb6a4e0765aed9f16897b4c4a9a39f119e`, retains a path/link/PAX correction candidate;
- PR #48 encoded the wrong default symlink scope, leading to issue #63 and the corrected PR #68.

Classification: superseded precursor. PR #68 is the retained prerequisite carrier.

### Corrected target scopes — issue #63 and PR #68

- issue #63 records that GNU tar defaults to member, hard-link, and symlink targets (`rsh`) and that uppercase `S` disables symlink-target transformation;
- PR #68 head `1f8f16bf0841a720bdc1da727000c26a3ab13a09`, merge `e7388243f3436ceda16f9d5be70d5423cc379b9d`, corrects the default scope and composes PR #56 and PR #48 behavior.

Classification: retained prerequisite source carrier, patch blob `1703984aa0c030e5131618a3541ee85bfd68ec65`.

### Numeric occurrence state — issue #98 and PR #102

- issue #98 defines GNU numeric selectors, number-plus-global behavior, zero semantics, ordering, and last-number-run selection;
- PR #102 head `46f49d04639d6baf43243e5096175866c7e6a58e`, merge `78ba614fa7faf4f4cdff99bab832649c774fe1e7`, implements per-field selected-match state.

Classification: retained prerequisite source carrier, patch blob `81828a468854e7ec9ef4cda9626b9c57314afba3`.

### Dialect defect — issue #108 and PR #113

- issue #108 isolates default GNU basic versus explicit `x` extended syntax after PR #68 and PR #102;
- PR #113 head `54d5f67d84f1dfb10d1e2c9079026aea5e1f41dd`, merge `9a058c2f6df430fa788c958f61f3a3e6c995e713`, provides characterization only and leaves imported source unchanged.

Classification: canonical negative-control carrier for unit 01.

## Explicitly separate linked records

### Issue #28

Issue #28 aggregates dotfile normalization and nested include-prefix defects, with coverage in PR #33. Issue #397 assigns these behaviors to later tarfilter units (dotfile identity and parent metadata). They do not enter the unit 01 source or test stack.

### Issue #29

Issue #29 owns unreachable no-option byte-preserving passthrough and GNU sparse preservation. Issue #397 assigns this to unit 18. It does not enter unit 01.

### Other broader #36 slices

Persistent `flags=` statements, semicolon-separated expression lists, replacement case conversion, locale/collation behavior, and complete GNU/POSIX compatibility remain outside unit 01 by issue #108, PR #113, PR #151, and issue #212.

## Audit conclusion

The deeper linked-carrier review changes no implementation or disposition decision:

1. the canonical regex unit remains issue #212 plus PRs #151/#202/#216;
2. PR #113 remains the characterization carrier;
3. PR #68 and PR #102 remain ordered prerequisites pending current-source inspection;
4. PR #48 and PR #56 are historical inputs already composed into PR #68;
5. issues #28 and #29 stay separate;
6. the historical source identity in issue #36 cannot replace a fresh exact Salsa `master` identity;
7. current canonical retrieval, rebase, tests, overlap search, and complete-diff review remain the first technical work.
