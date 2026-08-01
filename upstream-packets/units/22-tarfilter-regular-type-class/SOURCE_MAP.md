# Source map

## Upstream source

| Area | Exact location | Owner / relevance |
| --- | --- | --- |
| Selector parsing | `tarfilter`, `TypeFilterAction.__call__()` | Maps `REGTYPE`/`0` to stored type bytes. The defect lives here. |
| Filter decision | `tarfilter`, `type_filter_should_skip()` | Compares `member.type` by raw equality against stored bytes. |
| Archive copy | `tarfilter`, main member loop | Calls `member.isfile()` when copying payloads, showing Python already treats both regular encodings as files. |
| User contract | `tarfilter` argparse description and `--type-exclude` help | Describes `REGTYPE` as “regular file” and `0` as its flag value. |
| Native test runner | `coverage.py` | Supports individual named project tests; README documents `CMD=./mmdebstrap ./coverage.py --dist unstable <test-name>`. |

## Exact source identities

- Canonical repository: `https://gitlab.mister-muffin.de/josch/mmdebstrap`
- Intended branch: `main`
- Exact current upstream commit: `77ec9be5417ee44c96343d2347145585da1b1f94`
- Current upstream `tarfilter`: still maps `REGTYPE`/`0` only to `tarfile.REGTYPE`
- Current relevant source identity: matches Linux Fieldwork imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`, independently recorded by unit 15
- Debian package tag: `debian/1.5.7-3`
- Debian package resolved commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Linux Fieldwork imported path: `upstream/mmdebstrap/tarfilter`
- Imported blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Current Linux Fieldwork packet base: `main@6cc74d846c50b9bbb88247e8a128b67e8c174c1e`

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
| Import metadata | `upstream/mmdebstrap/.linux-fieldwork-source.json` | Debian package tag and resolved commit |
| Current upstream | `josch/mmdebstrap` `main@77ec9be5417ee44c96343d2347145585da1b1f94` | Current implementation base and native test conventions |
| Unit 01 packet | branch `upstream/unit-01-tarfilter-regex-dialects` | Owns `TransformAction` regex grammar; no direct unit-22 overlap |
| Unit 15 packet | branch `upstream/unit-15-tarfilter-transform-metadata` | Owns transform/link/PAX behavior; explicitly excludes unit 22 |
| Unit 16 packet | branch `upstream/unit-16-tarfilter-type-hardlinks` | Owns hard-link dependency state; consumes type decisions after selector mapping |

## Packet files

- Source patch: `patches/0001-tarfilter-treat-nul-as-regular.patch`
- Reproducible focused regression: `scripts/test_regular_type_class.py`
- Test commands and receipts: `TESTS.md`
- Mechanism and alternatives: `DEEP_DIVE.md`

## Adjacent ownership

- Unit 01 owns GNU basic/extended transform regex compatibility in `TransformAction`.
- Unit 15 owns transform, target, path, link, and PAX metadata semantics.
- Unit 16 owns type-excluded hard-link dependency handling and final-name state.
- Units 18–21 own no-option byte preservation, shifted PAX IDs, dotfile identity, and parent metadata.

The unit-22 patch touches `TypeFilterAction` only. No adjacent packet changes the same source owner. Composition testing remains useful, while final adjacent patch order is no longer treated as a blocker.

## Destination map

- Canonical project host: `gitlab.mister-muffin.de` Forgejo.
- Proposed delivery: controlled fork branch plus pull request.
- Debian Salsa/package repository: packaging context, not the current canonical implementation destination.
- Controlled fork: `NEEDS FORK`.
- External contact: unauthorized.
