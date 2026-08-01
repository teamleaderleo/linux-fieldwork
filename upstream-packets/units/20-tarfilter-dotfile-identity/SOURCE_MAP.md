# Source map

## Canonical coordination and method

- Linux Fieldwork issue #397 — unit boundary, priority, gates, and authority.
- `START_HERE.md` — canonical-carrier refresh, first-failure ownership, adjacent-context discriminators, and explicit stop conditions.
- `FIELD_GUIDE.md` — bounded claim, losing control, exact-head execution, cleanup/rerun, review saturation, and reopen rules.
- `notes/processes/cross-context-review-prevents-myopia.md` — known/unknown matrix and residual-risk register.
- `notes/processes/recent-cross-context-lessons.md` — current review lessons.
- `upstream-packets/README.md` — durable packet protocol.
- `upstream-packets/INDEX.md` — canonical directory `units/20-tarfilter-dotfile-identity/`.

## Canonical defect carrier

- Issue #38 — `tarfilter path normalization aliases dotfiles with non-dot paths`.
  - Identifies `name = "/" + member.name.lstrip("./")` as the source defect.
  - Provides `.config`, `config`, multi-dot, and include/exclude requirements.

## Historical combined carriers read in full

- Issue #28 — closed duplicate aggregation of #38 and #39.
- PR #33 — closed, unmerged combined carrier at head `32a92eec0aed327dfad4e1ca0df51f6168b80a48`.
  - Bundled no-option passthrough (#29), dotfile matching (#38), parent retention (#39), sparse handling, and wildcard-parent follow-up.
- Issue #29 — no-option passthrough, now unit 18.
- Issue #39 — parent metadata retention, now unit 21.
- `investigations/tarfilter-path-filter-matching/README.md`
- `investigations/tarfilter-path-filter-matching/tarfilter-path-filter-matching.patch`
- `tests/test_tarfilter_path_filter_matching.py`
- `tests/test_lf14_sparse_repair.py`
- `tests/test_lf14_wildcard_include_parents.py`
- `programmes/filesystems-images/lanes/LF-14-archive-extraction-metadata-contracts/scouts/LF-SCOUT-FS-01/artifacts/mmdebstrap-tarfilter-preserve-gnu-sparse.patch`
- `programmes/filesystems-images/lanes/LF-14-archive-extraction-metadata-contracts/scouts/LF-SCOUT-FS-01/artifacts/mmdebstrap-tarfilter-wildcard-parent.patch`

## Current upstream source and test ownership

- Repository: `josch/mmdebstrap`
- Base: main `77ec9be5417ee44c96343d2347145585da1b1f94`
- Source file: `tarfilter`
- Source blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Source owner: nested `path_filter_should_skip()` in `main()`.
- Source last-change commit: `87b9b385b38795c58bc13ffb33b8724bed27f7a0`
- Last-change intent signal: `tarfilter: do not rely on paths being absolute (starting with a single slash)`.
- Test registry: `coverage.txt`, blob `87f4cccf5fc646c82600672113830419e20b95dd`.
- Test runner: `coverage.py`, blob `9a522484aef05deae514a98e4b6adf5feb6c886d`.
- Null backend: `run_null.sh`, blob `e0a8c106f9d3d636baea286d2ab33834748dffc9`.
- Existing tarfilter style reference: `tests/tarfilter-idshift`.

## Unit 20 source candidate

- `patches/0001-tarfilter-preserve-dotfile-identity.patch`
  - Current Git blob: `fca86c0a45cb7f7c2e8534b4dacf8b2dafd55342`.
  - Three-file upstream diff: `coverage.txt`, `tarfilter`, `tests/tarfilter-path-dotfiles`.
- `tests/tarfilter-path-dotfiles`
  - Current Git blob: `516f4e1f3a38175257b68a9d9e524495d7531564`.
  - Upstream-style executable regression.
- `.github/workflows/unit-20-tarfilter-dotfile-identity.yml`
  - Internal exact-source and evidence gate.
  - Current blob before documentation batch: `bf769608742c71e4f3bdd2a1c700905ac1d0c02a`.
- Internal review carrier: Linux Fieldwork draft PR #408.

## Cross-context discriminators

### Real dpkg path-filter behavior

- Script: `scripts/probe_dpkg_path_filters.py`
- Receipt: `artifacts/dpkg-path-filter-differential.json`
- Runtime: dpkg 1.22.22.
- Result: ordinary package members spelled `./path` follow dpkg path filters; bare and repeated `./` spellings extract but sit outside the native filter match.

### GNU tar consumer path identity

- Script: `scripts/probe_tar_path_aliases.py`
- Receipt: `artifacts/gnu-tar-path-aliases.json`
- Runtime: GNU tar 1.35.
- Result: repeated leading `/` and `./` spellings converge on one consumer pathname; root aliases converge on extraction root; parent components are rejected.
- Successor boundary: GNU tar also collapses internal `foo/./.config`, which this unit deliberately leaves open.

### Mutation and alternative control

- Script: `scripts/test_normalization_mutations.py`
- Receipt: `artifacts/normalization-mutations.json`
- Losing variants:
  - current character-set stripping;
  - one-prefix-only parsing;
  - whole-path `posixpath.normpath()`;
  - first candidate before archive-root repair.

## Earlier receipts retained for history

- `artifacts/baseline-native-test.txt`
- `artifacts/candidate-native-test.txt`
- `artifacts/candidate-rerun.txt`
- `artifacts/patch-apply.txt`

These receipts belong to the earlier, narrower test revision. `TESTS.md` marks them as superseded evidence where the current 249-line regression broadens the matrix.

## Exact-execution identities

- Internal draft PR: #408.
- Last semantic technical head before documentation batch: `7b92189ace1de4138d753830f8032c244f1276c6`.
- Workflow run for that head: `30691603829`, last observed queued.
- The documentation batch will create a new exact head and replacement run.

## Destination map

- Intended delivery: Forgejo fork and pull request.
- Controlled fork: `NEEDS FORK`.
- Proposed upstream branch: `linux-fieldwork/unit-20-tarfilter-dotfile-identity`.
- External publication remains unauthorized.
