# Source map

## Upstream source

| Area | Exact location | Owner / relevance |
| --- | --- | --- |
| Selector parsing | `tarfilter`, `TypeFilterAction.__call__()` | Maps `REGTYPE`/`0` to stored type bytes. The defect lives here. |
| Filter decision | `tarfilter`, `type_filter_should_skip()` | Compares `member.type` by raw equality against stored bytes. |
| Archive copy | `tarfilter`, main member loop | Calls `member.isfile()` when copying payloads, showing Python already treats both regular encodings as files. |
| User contract | `tarfilter` argparse description and `--type-exclude` help | Describes `REGTYPE` as “regular file” and `0` as its flag value. |
| Native test registry | `coverage.txt` | Requires one `Test:` entry for every file in `tests/`. |
| Native test driver | `coverage.py` | Copies `tarfilter`, materializes `shared/test.sh`, runs shellcheck/shfmt, and dispatches the selected test. |
| Native null runner | `run_null.sh` | Executes `shared/test.sh` explicitly with `sh -x`; source test executable mode is not required by this runner, but must still be correct in the eventual upstream diff. |

## Exact source identities

- Canonical repository: `https://gitlab.mister-muffin.de/josch/mmdebstrap`
- Intended branch: `main`
- Exact current upstream head: `77ec9be5417ee44c96343d2347145585da1b1f94`
- Current relevant `tarfilter` content: matches Linux Fieldwork Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` and still contains `items.append(tarfile.REGTYPE)` in the `REGTYPE | 0` case
- Debian package mirror tag: `debian/1.5.7-3`
- Debian package resolved commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Linux Fieldwork imported path: `upstream/mmdebstrap/tarfilter`
- Imported blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Current Linux Fieldwork packet base: `main@6cc74d846c50b9bbb88247e8a128b67e8c174c1e`

## Canonical carriers read

| Carrier | Exact identity | Use |
| --- | --- | --- |
| Priority issue | Linux Fieldwork #397, unit 22 | Scope, priority, authority boundary |
| Finding | Linux Fieldwork #76 | Baseline mechanism, reproducer, expected correction |
| Finding checkpoint | #76 comment `5130042009` | Candidate head and CI receipt |
| Candidate PR | Linux Fieldwork #77 | Canonical retained composition |
| Candidate review | PR #77 review `4818250508` | Exact-head acceptance rationale |
| Investigation | `investigations/tarfilter-legacy-regular-type-filter/README.md` at `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7` | Durable original analysis |
| Retained patch | `investigations/tarfilter-legacy-regular-type-filter/tarfilter-legacy-regular-type-filter.patch` at the same head | One-line source correction |
| Retained regression | `tests/test_tarfilter_legacy_regular_type.py` at the same head | Baseline/candidate archive matrix |
| Import metadata | `upstream/mmdebstrap/.linux-fieldwork-source.json` | Debian package tag and resolved commit |
| Current upstream source | `josch/mmdebstrap` `main@77ec9be5417ee44c96343d2347145585da1b1f94` | Canonical implementation base and current defect check |
| Native test example | `upstream/mmdebstrap/tests/tarfilter-idshift` | Test style, executable lookup, temporary cleanup |
| Native registry | `upstream/mmdebstrap/coverage.txt` | Exact `Test:` registration format |
| Native driver | `upstream/mmdebstrap/coverage.py` | Test discovery, shellcheck/shfmt, and runner path |
| Native null runner | `upstream/mmdebstrap/run_null.sh` | Confirms `shared/test.sh` runs via `sh -x` |

## Packet files

- Source patch: `patches/0001-tarfilter-treat-nul-as-regular.patch`
- Reproducible focused Python regression: `scripts/test_regular_type_class.py`
- Proposed upstream-native shell regression: `native/tests/tarfilter-regular-type-class`
- Proposed native registration: `native/coverage.txt.fragment`
- Exact-source/native-packet Linux Fieldwork gate: `tests/test_unit22_tarfilter_native_packet.py`
- Test commands and receipts: `TESTS.md`
- Mechanism and alternatives: `DEEP_DIVE.md`

## Adjacent ownership

- Unit 01 owns GNU basic/extended transform regex compatibility in `TransformAction`.
- Unit 15 owns transform, target, path, link, and PAX metadata semantics.
- Unit 16 owns type-excluded hard-link dependency handling after selection.
- Units 18–21 own no-option byte preservation, shifted PAX IDs, dotfile identity, and parent metadata.

Unit 22 touches only `TypeFilterAction`. Adjacent patches may be composed for a complete-gate run, but their completion order does not block unit 22's independent implementation, test, or review.

## Upstream overlap review

A 2026-08-01 search of the canonical Forgejo repository, its visible issue index, and web-indexed issue/pull-request results found no current item mentioning `REGTYPE`, `AREGTYPE`, NUL regular type flags, or the equivalent `--type-exclude` defect. This is a bounded search result, not proof that an unindexed private or newly-created equivalent does not exist. Refresh immediately before any authorized submission.

## Destination map

- Project host: maintainer Forgejo at `gitlab.mister-muffin.de`.
- Proposed delivery: controlled fork branch plus pull request.
- Controlled fork: `NEEDS FORK`.
- External contact: unauthorized.
