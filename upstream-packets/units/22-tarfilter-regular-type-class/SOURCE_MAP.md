# Source map

## Upstream source

| Area | Exact location | Owner / relevance |
| --- | --- | --- |
| Selector parsing | `tarfilter`, `TypeFilterAction.__call__()` | Maps `REGTYPE`/`0` to stored type bytes. The defect lives here. |
| Filter decision | `tarfilter`, `type_filter_should_skip()` | Compares `member.type` by raw equality against stored bytes. |
| Archive copy | `tarfilter`, main member loop | Calls `member.isfile()` when copying payloads, showing Python already treats both regular encodings as files. |
| User contract | `tarfilter` argparse description and `--type-exclude` help | Describes `REGTYPE` as “regular file” and `0` as its flag value. |

## Exact source identities

- Canonical repository: `https://salsa.debian.org/debian/mmdebstrap.git`
- Intended branch: `master`
- Retained package tag: `debian/1.5.7-3`
- Retained resolved commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Linux Fieldwork imported path: `upstream/mmdebstrap/tarfilter`
- Imported blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Current Linux Fieldwork packet base: `main@6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Current Salsa `master` commit: unresolved because the runtime could read the official web project and tags but could not resolve DNS for `git clone`; no commit identity is inferred.

## Canonical carriers read

| Carrier | Exact identity | Use |
| --- | --- | --- |
| Priority issue | Linux Fieldwork #397, unit 22 | Scope, order, authority boundary |
| Finding | Linux Fieldwork #76 | Baseline mechanism, reproducer, expected correction |
| Finding checkpoint | #76 comment `5130042009` | Candidate head and CI receipt |
| Candidate PR | Linux Fieldwork #77 | Canonical retained composition |
| Candidate review | PR #77 review `4818250508` | Exact-head acceptance rationale |
| Investigation | `investigations/tarfilter-legacy-regular-type-filter/README.md` at `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7` | Durable original analysis |
| Retained patch | `investigations/tarfilter-legacy-regular-type-filter/tarfilter-legacy-regular-type-filter.patch` at the same head | One-line source correction |
| Retained regression | `tests/test_tarfilter_legacy_regular_type.py` at the same head | Baseline/candidate archive matrix |
| Import metadata | `upstream/mmdebstrap/.linux-fieldwork-source.json` | Upstream tag and resolved commit |

## Packet files

- Source patch: `patches/0001-tarfilter-treat-nul-as-regular.patch`
- Reproducible focused regression: `scripts/test_regular_type_class.py`
- Test commands and receipts: `TESTS.md`
- Mechanism and alternatives: `DEEP_DIVE.md`

## Adjacent ownership

- Unit 01 owns GNU basic/extended transform regex compatibility.
- Unit 15 owns transform, target, path, and PAX metadata semantics.
- Unit 16 owns type-excluded hard-link dependency handling.
- Units 18–21 own no-option byte preservation, shifted PAX IDs, dotfile identity, and parent metadata.

The unit-22 patch touches `TypeFilterAction` only and can remain a separate upstream commit. Its final ordering must follow the source-line overlap review for the active tarfilter series.

## Destination map

- Project host: Debian Salsa / GitLab.
- Proposed delivery: controlled fork plus merge request.
- Controlled fork: `NEEDS FORK`.
- External contact: unauthorized.
