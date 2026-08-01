# Source map

## Upstream source identity

| Item | Repository path or URL | Exact revision | Notes |
| --- | --- | --- | --- |
| Primary implementation | canonical mmdebstrap `gpgvnoexpkeysig` | upstream `main` `77ec9be5417ee44c96343d2347145585da1b1f94` | Current tree still reports the helper's latest change as `59e5870e7b76cc25dc6cb7b34586451d4ec2a524`. |
| Imported implementation | `upstream/mmdebstrap/gpgvnoexpkeysig` | blob `83370755454a1322bf6862751aab7381d175aa8b` | Byte identity used by the retained patch and local fixture. |
| Candidate implementation | temporary source copy after retained patch | blob `de7e0ae24218632fe2e32a1130f5c2a39f8c4aed` | Exact blob asserted by the fixture script. |
| Upstream tests | `coverage.sh`, `coverage.py`, `tests/` | upstream `77ec9be5417ee44c96343d2347145585da1b1f94` | No indexed focused helper regression was found. |
| Build/package metadata | upstream repository root and Debian package sources | current upstream plus Debian 1.5.7-1+deb13u1 | Installed helper contract is documented through `Apt::Key::gpgvcommand`. |
| Contribution instructions | canonical Forgejo repository and issue tracker | inspected 2026-08-01 | Proposed delivery is a fork and pull request. |

## Linux Fieldwork carriers

| Carrier | Exact head or merge | Role | Disposition |
| --- | --- | --- | --- |
| Issue #41 | open | Original verifier-status defect and real process-status requirement | Evidence owner |
| PR #138 | `9b71d143e958e2b2b0823785cbfaf22839d31850` | Focused status-preservation history; FIFO failure led to regular spool | Superseded |
| Issue #175 | open | Missing/malformed `--status-fd` parser defect | Evidence owner |
| PR #177 | `fbf63489916da81c851bee4b0ef1a474275bd014` | Focused parser contract and real-gpgv last-occurrence evidence | Superseded |
| Issue #176 | open | Wrapper-only signal forwarding and child ownership | Evidence owner |
| PR #180 | `a7c453a28e531faa883e63f943a773667023b2bb` | Focused signal carrier; exposed launch/PID-registration race | Superseded |
| PR #196 | head `bc8d88089d931cd0b78dd0c95dd72c784195fcdc`; merge `65d4213393cf2b2d84c71a8b6a05fdad15396b9b` | Canonical composed lifecycle, synthetic matrix, late-filter replay repair | Canonical internal carrier |
| Unit 03 branch | `upstream/unit-03-gpgvnoexpkeysig-lifecycle` | Current-upstream closeout, real GnuPG/APT fixture, drafts, handoff | Canonical packet |

## Candidate code

| File | Lines or symbols | Change | Owning patch |
| --- | --- | --- | --- |
| `upstream/mmdebstrap/gpgvnoexpkeysig` | `find_gpgv_status_fd` | Parse separated/equals forms, validate every occurrence, use last valid occurrence before `--` | canonical lifecycle patch |
| same | verifier launch and wait | Run verifier as owned child, preserve exact status, close launch registration window | canonical lifecycle patch |
| same | status handoff | Use private regular spool to isolate verifier from filter failure | canonical lifecycle patch |
| same | filter launch and wait | Rewrite completed status bytes once on selected descriptor | canonical lifecycle patch |
| same | signal and cleanup functions | Forward HUP/INT/TERM, reap children, clean state, prevent late replay | canonical lifecycle patch |
| same | final precedence | verifier > filter > cleanup > success; handled signal result wins | canonical lifecycle patch |

## Candidate tests and fixtures

| File | Test or fixture | Baseline failure | Candidate expectation |
| --- | --- | --- | --- |
| `tests/test_mmdebstrap_gpgvnoexpkeysig_canonical.py` | eight-test synthetic lifecycle matrix | pipeline/parser/signal defects | exact parser, status, signal, cleanup behavior |
| `tests/test_mmdebstrap_gpgvnoexpkeysig_post_filter_signal.py` | deterministic late-signal replay control | predecessor emits duplicate status | candidate emits once and cleans |
| `fixtures/Release` | APT-style metadata signed by generated historical key | real expired and tampered verification input | reusable source bytes |
| `scripts/run-real-gpg-fixture.sh` | generates key/signatures, applies patch, runs direct wrapper and local APT update | real `BADSIG` status 1 becomes wrapper 0 | candidate returns 1 and preserves status; expired key remains accepted |
| `artifacts/real-gpg-fixture.txt` | two exact execution receipts | records distinguishing result and rerun | durable evidence |

## Patch and branch links

- Linux Fieldwork branch: `upstream/unit-03-gpgvnoexpkeysig-lifecycle`
- Controlled upstream fork: `NEEDS FORK`
- Candidate upstream branch: `NEEDS BRANCH`
- Compare or diff: current upstream base plus retained patch; public compare requires authorization and fork creation
- Retained patch: `investigations/mmdebstrap-gpgvnoexpkeysig-canonical/0001-canonical-lifecycle.patch`
- Patch blob: `a30b37ca1228df1d80fd7611d4a591549314aeb0`
- Patch application command:

```sh
patch -d "$SOURCE_TREE" -p1 < investigations/mmdebstrap-gpgvnoexpkeysig-canonical/0001-canonical-lifecycle.patch
```

## Operation ownership map

| Operation | Owner before candidate | Owner after candidate | Evidence |
| --- | --- | --- | --- |
| Select status descriptor | first separated `--status-fd`; unsafe `$2` expansion | complete pre-execution parser; last valid occurrence before `--` | PR #177 and canonical matrix |
| Verify signature | foreground `gpgv` in pipeline | owned verifier child with exact wait status | PR #196 and real BADSIG fixture |
| Carry status bytes | live pipe into `sed` | private regular spool | early-filter/SIGPIPE negative control in PR #138 review |
| Rewrite `EXPKEYSIG` | pipeline `sed` | separately owned filter after verifier completion | synthetic matrix and real expired-key fixture |
| Report ordinary result | final pipeline command | verifier, then filter, then cleanup | synthetic matrix and real BADSIG fixture |
| Handle wrapper-only signal | shell trap can be deferred; verifier unowned | wrapper forwards signal to owned child and reaps it | issue #176, PR #180, PR #196 matrix |
| Remove temporary state | partial EXIT handling | explicit cleanup plus emergency path | canonical matrix and real fixture rerun |
| Consume wrapper from APT | documented `Apt::Key::gpgvcommand` | same invocation contract | isolated `apt-get update` receipt |

## Overlap and current upstream state

Inspection date: 2026-08-01.

The canonical upstream repository displayed `main` head `77ec9be5417ee44c96343d2347145585da1b1f94`. The helper's displayed latest change was `59e5870e7b76cc25dc6cb7b34586451d4ec2a524`, predating the current head. The current helper text matches the imported 56-line pipeline implementation used by the retained patch. Search of indexed upstream issues, pull requests, and `EXPKEYSIG` references found no equivalent active correction. This search is a collision check, not proof that private or unindexed work does not exist.

## Files deliberately not changed

- The imported source file on Linux Fieldwork `main` remains unchanged; the candidate stays as a retained patch until an upstream branch is authorized.
- Existing canonical synthetic tests remain untouched because their exact-head evidence already passed and the unit's missing gate was a real verifier/APT fixture.
- APT source code, GnuPG source code, Debian packaging, and archive keyrings remain outside this wrapper-owned correction.
- Timeout/escalation and process-group policy remain outside this unit.
