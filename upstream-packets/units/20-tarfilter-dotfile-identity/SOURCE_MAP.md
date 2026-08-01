# Source map

## Canonical coordination

- Linux Fieldwork issue #397 — unit boundary, priority, gates, and authority.
- `upstream-packets/README.md` — durable packet protocol.
- `upstream-packets/INDEX.md` — canonical directory `units/20-tarfilter-dotfile-identity/`.

## Canonical defect carrier

- Issue #38 — `tarfilter path normalization aliases dotfiles with non-dot paths`.
  - Identifies `name = "/" + member.name.lstrip("./")` as the source defect.
  - Provides `.config`, `config`, and multi-dot reproducer requirements.

## Historical combined carriers

- Issue #28 — closed duplicate aggregation of #38 and #39.
- PR #33 — closed, unmerged combined carrier at head `32a92eec0aed327dfad4e1ca0df51f6168b80a48`.
  - Bundled no-option passthrough (#29), dotfile matching (#38), parent retention (#39), sparse handling, and wildcard-parent follow-up.
- `investigations/tarfilter-path-filter-matching/README.md`
- `investigations/tarfilter-path-filter-matching/tarfilter-path-filter-matching.patch`
- `tests/test_tarfilter_path_filter_matching.py`
- `tests/test_lf14_sparse_repair.py`
- `tests/test_lf14_wildcard_include_parents.py`
- `programmes/filesystems-images/lanes/LF-14-archive-extraction-metadata-contracts/scouts/LF-SCOUT-FS-01/artifacts/mmdebstrap-tarfilter-preserve-gnu-sparse.patch`
- `programmes/filesystems-images/lanes/LF-14-archive-extraction-metadata-contracts/scouts/LF-SCOUT-FS-01/artifacts/mmdebstrap-tarfilter-wildcard-parent.patch`

## Explicitly separate units

- Issue #29 / unit 18 — byte-preserving no-option passthrough.
- Issue #39 / unit 21 — parent metadata retention for nested includes.

## Current upstream source and test ownership

- Upstream repository: `josch/mmdebstrap`
- Base: main `77ec9be5417ee44c96343d2347145585da1b1f94`
- Source file: `tarfilter`
- Source owner: nested `path_filter_should_skip()` in `main()`.
- Test registry: `coverage.txt`.
- Test directory: `tests/`.
- Existing style reference: `tests/tarfilter-idshift`.

## Unit 20 retained files

- `patches/0001-tarfilter-preserve-dotfile-identity.patch` — three-file upstream candidate.
- `tests/tarfilter-path-dotfiles` — executable copy of the proposed upstream regression.
- `artifacts/baseline-native-test.txt` — failing baseline receipt.
- `artifacts/candidate-native-test.txt` — passing candidate receipt.
- `artifacts/candidate-rerun.txt` — cleanup and rerun receipt.
- `artifacts/patch-apply.txt` — no-fuzz/no-offset application and compilation receipt.

## Destination map

- Delivery: Forgejo fork and pull request.
- Controlled fork: `NEEDS FORK`.
- Proposed upstream branch: `linux-fieldwork/unit-20-tarfilter-dotfile-identity`.
- External publication remains unauthorized.
