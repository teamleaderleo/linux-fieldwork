# Source map

## Upstream source identity

| Item | Repository path or URL | Exact revision | Notes |
| --- | --- | --- | --- |
| Primary implementation | `debian/tests/testsuite` in `https://salsa.debian.org/debian/mmdebstrap.git` | dgit master view `c8a789205ded12daccfb16deaa35ddd1fc8d688f`; direct Salsa verification pending | Two account-presence conditions near the package-test setup prelude. |
| Released Debian source | Debian Sources `mmdebstrap 1.5.7-3` | Debian tag abbreviated `6fde9997`; source package currently in forky/sid | Latest published Debian source found on 2026-08-01. |
| Imported Linux Fieldwork source | `upstream/mmdebstrap/debian/tests/testsuite` | blob `9f4eda87430da38b08a23a50a51e53b22cf7414b` | Carries the same two unanchored checks. |
| Upstream runtime adjacency | upstream `mmdebstrap`, `mmdebstrap` and `tests/numeric-uid-gid` | `6f0a2fcd7f0b21a69d6c2b7c90272a132ed58ff5` | Numeric UID/GID support; separate owner and behavior. |
| Current upstream runtime head observed | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, branch `main` | `77ec9be5417ee44c96343d2347145585da1b1f94` | Latest visible head on 2026-08-01; package-test file lives in Debian packaging. |
| Upstream tests | Debian autopkgtest `debian/tests/testsuite`; upstream coverage cases invoked by it | same packaging base | Full focused integration gate still pending. |
| Contribution instructions | Debian Salsa project and normal Debian package contribution flow | current public pages read 2026-08-01 | External contact remains unauthorized. |

## Linux Fieldwork carriers

| Carrier | Exact head or merge | Role | Classification |
| --- | --- | --- | --- |
| Issue #80 | closed completed | focused defect and scope | canonical issue |
| PR #92 | head `f105dac7d9357747d5ec6559b21dfec837380e1a`; merge `3cc250da7798679bd20c1a1f34396f83c9b0ee04` | product patch, regression, investigation, reusable note | canonical component |
| PR #215 | historical head `ab504b...`; later branch state `ea21...` | current-main duplicate carrying stronger controls | superseded |
| PR #218 | head `cde9d361d659357527d2c06a634b42c5b8070169`; CI `30581822309` success | leading-hyphen and full-shell proof | superseded proof |
| PR #225 | reviewed head `73e2a1b45852181df2922109b5bfac5c78d9e355` | restacked proof | superseded proof |
| PR #252 | failed run `30598944690` / 797 | zero-fuzz proof exposed malformed ten-line hunk declaration | superseded defect-finding carrier |
| PR #291 | head `125d4e5097625b38850292525c7eb2f98818f5d9`; merge `920a4b354386e32e7f13d004d62fba055a5f1518`; CI `30624718470` / 845 | repaired zero-fuzz, strict full-diff proof | canonical evidence |
| Issue #53 / PR #72 | current broader sid harness lineage | package-test integration context | adjacent hold |
| PR #86 | head `34414b665c4ab074a9ed9e2572be1095a59e503a` | `dev-ptmx` dependency correction | adjacent separate unit |

## Candidate code

| File | Lines or symbols | Change | Owning commit or patch |
| --- | --- | --- | --- |
| `debian/tests/testsuite` | subuid presence condition | pipe field 1 through `cut -s -d: -f1` and use `grep -Fxq --` | `patches/0001-debian-tests-match-subid-account-field-exactly.patch` |
| `debian/tests/testsuite` | subgid presence condition | same semantics as subuid | same patch |

## Candidate tests

| File | Test or fixture | Baseline failure | Candidate expectation |
| --- | --- | --- | --- |
| Linux Fieldwork `tests/test_mmdebstrap_subid_account_match.py` | exact, substring, malformed, regex, leading hyphen, empty, absent, parity, rerun | whole-record grep accepts unrelated substring/regex matches | field-1 literal equality and idempotent append |
| Packet-local synthetic smoke recorded in `TESTS.md` | reconstructed package-test block with upstream path | substring account suppresses append | candidate appends exact account once |
| Debian autopkgtest / relevant unshare cases | package-level integration | pending | setup provides required ranges and namespace cases proceed |

## Patch and branch links

- Linux Fieldwork branch: `upstream/unit-10-subid-exact-match`
- Controlled upstream fork: `NEEDS FORK`
- Candidate upstream branch: `NEEDS BRANCH`
- Compare or diff: `NEEDS BRANCH`
- Retained patch: `patches/0001-debian-tests-match-subid-account-field-exactly.patch`
- Patch application command: `patch --batch --forward --fuzz=0 -p1 -i upstream-packets/units/10-subid-exact-match/patches/0001-debian-tests-match-subid-account-field-exactly.patch`

## Operation ownership map

| Operation | Owner before candidate | Owner after candidate | Evidence |
| --- | --- | --- | --- |
| Parse subordinate-ID account identity | whole-line regex in Debian package-test shell | colon field 1, fixed exact string | candidate two-line diff and synthetic matrix |
| Append missing subuid range | existing Debian package-test shell | unchanged | identical echo line |
| Append missing subgid range | existing Debian package-test shell | unchanged | identical echo line |
| Runtime acceptance of numeric UID/GID records | upstream mmdebstrap runtime | upstream commit `6f0a2fcd...` | adjacent upstream commit and Debian 1.5.7-2/3 changelog |
| Execute namespace/coverage tests | Debian package-test harness | unchanged | surrounding testsuite flow deliberately untouched |

## Overlap and current upstream state

Search date: 2026-08-01.

The latest published Debian source found is 1.5.7-3. Public source and Linux Fieldwork’s exact imported blob retain the whole-record package-test checks. Upstream runtime commit `6f0a2fcd...` adds numeric UID/GID support inside mmdebstrap and its own tests; it does not change Debian’s package-test setup condition. No public equivalent correction was found in the current bug list or visible repository summaries.

A direct current Salsa clone/API receipt remains required before claiming exact-head freshness or active-overlap completeness.

## Files deliberately not changed

- upstream runtime `mmdebstrap`;
- `tests/numeric-uid-gid` and `coverage.txt`;
- Debian `debian/tests/control`;
- appended range values `100000:65536`;
- user creation, sudoers setup, HTTP server, mirror generation, coverage selection, timeout handling, and cleanup;
- Linux Fieldwork imported source.
