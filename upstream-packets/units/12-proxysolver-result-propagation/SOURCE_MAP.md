# Source map

## Upstream source identity

| Item | Repository path or URL | Exact revision | Notes |
| --- | --- | --- | --- |
| Primary implementation | canonical repository root `proxysolver` | upstream main `77ec9be5417ee44c96343d2347145585da1b1f94` | Upstream listing says this file last changed 2021-09-16. |
| Imported implementation | `upstream/mmdebstrap/proxysolver` | blob `5cd51fab89104d30b8b12bff18a49d38d9be0003` | Exact source used by every retained Linux Fieldwork regression. |
| Upstream tests | `coverage.py`, `coverage.sh`, `tests/` | same upstream main | No focused proxysolver result test located in the public listing. |
| Build or package metadata | Debian source `mmdebstrap` 1.5.7-3 | forky/sid snapshot observed 2026-07-31 | Current packaged source corroboration only; direct source-byte comparison remains open. |
| Contribution instructions | canonical README and Forgejo Issues/Pull requests | upstream main | Public repository exposes fork and pull-request workflow. |

## Linux Fieldwork carriers

| Carrier | Exact head or merge | Role | Status |
| --- | --- | --- | --- |
| Issue #397 / PR #398 | merge `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` | packet protocol and unit boundary | canonical coordination |
| Issue #133 | closed 2026-07-30 | ordinary false-success defect | component record |
| PR #134 | head `f453c2d48f2e7b26e9ccca58b45d7958a34462fa`; merge `ebb11fc382ce6b42597e9130e7abb741c3684ca2` | positive nonzero status patch and regression | merged component evidence |
| Issue #165 | closed 2026-07-30 | negative return-code/signal identity defect | component record |
| PR #166 | head `50fdbcd25b51842ff2b489a91e36668e0e2340ea` | developed and repaired signal follow-up | superseded historical carrier |
| PR #201 | head `da0974a81419d6dc27cb89173bed821ced0e5c53` | current-main execution carrier; run `30579465025` | retired evidence carrier |
| PR #207 | head `e4b16f5180e8bf67bf58621cac4447f4a4a55f44`; merge `72f4d27aadf1863ee1b534d9751f3061c55b2ba4` | clean current-main restack of signal evidence | canonical component evidence |
| Unit 12 branch | base `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` | composed source patch, expanded regression, packet | active |

PRs #143, #159, #172, #204, and #205 appear in Packet G routing comments for other source owners. They carry no proxysolver source or test and are excluded from this unit.

## Candidate code

| File | Lines or symbols | Change | Owning patch |
| --- | --- | --- | --- |
| `proxysolver` | imports | add `signal` | `patches/0001-proxysolver-propagate-solver-results.patch` |
| `proxysolver` | after stdout forwarding | record `p.wait()` result | same |
| `proxysolver` | negative result branch | flush stdout, restore default signal action, unblock, signal self | same |
| `proxysolver` | positive result branch | raise `SystemExit(returncode)` | same |

## Candidate tests

| File | Test or fixture | Baseline failure | Candidate expectation |
| --- | --- | --- | --- |
| `scripts/test_proxysolver_result_propagation.py` | fake solver with independent output, stderr, exit, and signal controls | exit 7 becomes 0; ordinary-only signals become 241/254 | exit 7; actual `-SIGTERM`/`-SIGINT`; identical output/dump; inherited stderr; child gone |
| historical `tests/test_mmdebstrap_proxysolver_exit_status.py` | success and exit 7 | false success | exact positive code |
| historical `tests/test_mmdebstrap_proxysolver_signal_status.py` | SIGTERM and inherited blocked mask | status 241 | exact `-SIGTERM` |

## Patch and branch links

- Linux Fieldwork branch: `upstream/unit-12-proxysolver-result-propagation`
- Controlled upstream fork: `NEEDS FORK`
- Candidate upstream branch: `NEEDS BRANCH`
- Compare or diff: `NEEDS BRANCH`
- Retained patch: `patches/0001-proxysolver-propagate-solver-results.patch`
- Upstream application command: `patch --batch --forward -p1 -i /absolute/path/to/0001-proxysolver-propagate-solver-results.patch`

## Operation ownership map

| Operation | Owner before candidate | Owner after candidate | Evidence |
| --- | --- | --- | --- |
| execute real APT solver | `subprocess.Popen` child | unchanged | imported source and regression fixture |
| forward solver stdout | wrapper loop | unchanged | stdout equals fixture output |
| retain dump bytes | wrapper file context | unchanged | dump equals stdout in every case |
| expose solver stderr | child inherited stderr | unchanged | explicit `solver diagnostic` assertion |
| wait for completion | implicit `Popen.__exit__()` | explicit `p.wait()` before context exit | candidate source assertion |
| positive child result | accidental wrapper 0 | same positive exit code | exit 7 control |
| signal-derived result | modulo-256 ordinary exit | same POSIX signal termination | SIGTERM and SIGINT controls |
| dump closure before signal | interpreter normal exit happened later | file context closes before self-signal | complete dump after `-SIGTERM`/`-SIGINT` |
| wrapper stdout flush before signal | interpreter shutdown flush | explicit `sys.stdout.flush()` | piped stdout remains complete |

## Overlap and current upstream state

Search performed 2026-07-31. The canonical repository displayed main commit `77ec9be5417ee44c96343d2347145585da1b1f94`, 6 open issues, and no surfaced proxysolver result-propagation issue or pull request. The repository listing says `proxysolver` last changed on 2021-09-16. This establishes a strong no-overlap indication, while direct API/raw-source access and a complete authenticated search remain outstanding.

## Files deliberately not changed

- imported `upstream/mmdebstrap/proxysolver` remains unchanged;
- historical investigation patches and tests remain unchanged;
- `coverage.py`, `make_mirror.sh`, `run_qemu.sh`, and their lifecycle tests remain separate owners;
- diagnostics for missing solver, missing dump filename, and dump-file creation remain unchanged.
