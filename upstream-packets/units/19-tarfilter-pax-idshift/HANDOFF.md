# Current handoff

Updated: `2026-08-01 15:50 +08:00`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-19-tarfilter-pax-idshift` |
| Linux Fieldwork parent head before this final handoff commit | `19b29f5120690a4b19cfec1066096197a8c117a7` |
| Linux Fieldwork final head | the commit containing this `HANDOFF.md`; exact SHA is recorded in the #397 `UNIT CHECKPOINT` |
| Upstream base repository/branch | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, repository default branch |
| Upstream repository head observed | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Current tarfilter file commit | `87b9b385b38795c58bc13ffb33b8724bed27f7a0` |
| Imported/local tarfilter blob | `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Imported native test blob | `6956e76aca153147d3a8a6668196d913ebc8a49e` |
| Project README blob | `281e551bdf4af6e8336dca8a93cdf278a6be4cab` |
| Suite wrapper blob | `58e90568804db9f259b9ab99ce99ed74672fe2c5` |
| Test dispatcher blob | `9a522484aef05deae514a98e4b6adf5feb6c886d` |
| Test declaration blob | `87f4cccf5fc646c82600672113830419e20b95dd` |
| Debian testsuite blob | `9f4eda87430da38b08a23a50a51e53b22cf7414b` |
| Debian test-control blob | `58582587412629e180ba1712abd35b8d7f7bc7de` |
| Candidate fork/branch | `NEEDS FORK` / `NEEDS BRANCH` |
| Candidate head | `NEEDS BRANCH` |
| Source patch | `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch` |
| Source patch SHA-256 | `b86da5f6a2f2f1757b5b3fc0e32ebeabeeadbdebebb4cdc1961d3d1ff5eb3303` |
| Native test patch | `patches/0002-tests-cover-pax-idshift.patch` |
| Native test patch SHA-256 | `ce5442b10be51b900a86947f25046ff39392fd2e9e9a776e982eabe79a177edc` |
| Owning issue/PR | issue #37; PR #78 |
| Prior reviewed candidate | `8d6443626e4338b180ec0533969bfe4d32b20d52` |
| Latest workflow/run | Linux Fieldwork CI `30538012863`, success on prior reviewed candidate |

## Current bounded claim

Current mmdebstrap `tarfilter` retains PAX `uid` and `gid` strings after `--idshift` changes the numeric fields. Those strings override shifted large IDs during output serialization. Removing only the two stale numeric PAX keys after successful validation and shifting corrects large-ID output while preserving ordinary header behavior, unrelated PAX metadata, payloads, and inverse-shift ownership.

The native owner is `tests/tarfilter-idshift`. Its retained extension has an executable losing path: the baseline model exits `1` with `large ownership was not shifted`; the candidate model exits `0`.

The project-aligned readiness gate is now exact: prepare the mirror, run `CMD=./mmdebstrap ./coverage.sh tarfilter-idshift` with QEMU enabled, and repeat it on the same candidate. That path checks `tarfilter` with Black and checks the generated native test with the project's ShellCheck and shfmt settings.

## Work completed in this pass

- resumed unit 19 at branch head `3cd8d9c1c17bf38a3f96f17d9a7a2526c6a874a9`;
- read the imported mmdebstrap `README.md`, `coverage.sh`, `coverage.py`, `coverage.txt`, `debian/tests/control`, and `debian/tests/testsuite`;
- recorded exact instruction-file blobs in `PROJECT_INSTRUCTIONS.md` and `SOURCE_MAP.md`;
- confirmed the README's broad and named-test entry points;
- confirmed `coverage.sh` runs `black --check ./tarfilter` before dispatch;
- confirmed `coverage.py` accepts named tests, copies the checkout's `tarfilter`, checks rendered `shared/test.sh` with exact ShellCheck and shfmt options, and selects the runner;
- confirmed `tarfilter-idshift` is declared `Needs-QEMU: true`;
- confirmed the Debian package testsuite exports `HAVE_QEMU=no`, causing this named test to be skipped in that package-test phase;
- converted that finding into an explicit QEMU-backed readiness requirement;
- updated the unit README, source map, and upstream PR draft with the exact project gate and package-test coverage limit;
- checked local tool availability: Python `3.13.5` and GNU patch `2.8` are present; Black, ShellCheck, and shfmt are absent;
- retried GitHub access with `git ls-remote`; DNS resolution failed with status `128` and `Could not resolve host: github.com`;
- preserved the external-contact boundary.

## Changed paths in this continuation

- `upstream-packets/units/19-tarfilter-pax-idshift/PROJECT_INSTRUCTIONS.md`
- `upstream-packets/units/19-tarfilter-pax-idshift/README.md`
- `upstream-packets/units/19-tarfilter-pax-idshift/SOURCE_MAP.md`
- `upstream-packets/units/19-tarfilter-pax-idshift/UPSTREAM_PR.md`
- `upstream-packets/units/19-tarfilter-pax-idshift/HANDOFF.md`

## Complete retained packet

- `README.md`
- `SOURCE_MAP.md`
- `DEEP_DIVE.md`
- `TESTS.md`
- `PROJECT_INSTRUCTIONS.md`
- `DECISIONS.md`
- `UPSTREAM_ISSUE.md`
- `UPSTREAM_PR.md`
- `HANDOFF.md`
- `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch`
- `patches/0002-tests-cover-pax-idshift.patch`
- `scripts/test_pax_idshift.py`

## Distinguishing observations

- current public tarfilter still increments `member.uid` and `member.gid` while retaining stale PAX numeric keys;
- baseline large ID after `+7`: `1000000000:1000000001`;
- candidate large ID after `+7`: `1000000007:1000000008`, with matching regenerated PAX strings;
- native detector baseline: status `1`, stderr `large ownership was not shifted`;
- native detector candidate: status `0`, empty stderr;
- `tests/tarfilter-idshift` is the narrow native owner;
- `coverage.txt` declares the named test `Needs-QEMU: true`;
- `coverage.py` skips `Needs-QEMU` tests when `HAVE_QEMU=no`;
- Debian's package testsuite explicitly uses `HAVE_QEMU=no`, so a green package autopkgtest does not execute this named test;
- `coverage.sh` owns Black validation for `tarfilter`;
- `coverage.py` owns exact ShellCheck and shfmt validation for the generated native shell test;
- the current worker environment cannot execute those formatter/linter gates or clone the current upstream checkout.

## Exact project checks

```sh
black --check ./tarfilter
shellcheck --exclude=SC2050,SC2194,SC2016 -f gcc shared/test.sh
shfmt --posix --binary-next-line --case-indent --indent 2 --simplify -d shared/test.sh
```

The ShellCheck and shfmt commands are run by `coverage.py` against the generated `shared/test.sh`; they are listed here for exact evidence identity.

## Gates completed

- prior exact imported-source regression: PASS on PR #78 exact head;
- prior independent exact-head review: ACCEPT;
- prior Linux Fieldwork CI: PASS, run `30538012863`;
- packet semantic probe: PASS on Python 3.13.5;
- immediate probe rerun and output comparison: PASS;
- current source persistence review: complete;
- indexed overlap refresh: complete;
- imported native test-owner review: complete;
- native test patch drafting: complete;
- native detector losing/winning model run: expected FAIL/PASS;
- project instruction review and gate mapping: complete;
- package autopkgtest coverage-limit classification: complete;
- packet cleanup verification: complete.

## Red or neutral runs classified

- early PR #78 patch revisions: patch-packaging failures before semantic execution; superseded by final block-replacement candidate;
- native detector baseline model: intended product failure, status `1`, exact diagnostic `large ownership was not shifted`;
- current GitHub access attempt: environment DNS failure, status `128`, zero source mutation;
- local Black/ShellCheck/shfmt checks: unavailable tools; no gate result claimed;
- complete upstream-native test: unexecuted because a current checkout, QEMU preparation, and controlled candidate branch remain unavailable.

## Cleanup state

This continuation created no temporary source tree, archive, service, socket, mount, container, lock, or package state. The tool-availability and DNS checks left no retained local files. The branch intentionally retains the packet documents and two ordered patches. Shared imported source and test files remain unchanged.

## First incomplete step

Apply both retained patches to an exact checkout of upstream head `77ec9be5417ee44c96343d2347145585da1b1f94`, then run the exact Black and QEMU-backed named-test sequence documented in `PROJECT_INSTRUCTIONS.md`.

## Next safe action

```sh
git clone https://gitlab.mister-muffin.de/josch/mmdebstrap mmdebstrap
cd mmdebstrap
git checkout 77ec9be5417ee44c96343d2347145585da1b1f94
git checkout -b linux-fieldwork/unit-19-tarfilter-pax-idshift

packet=/path/to/linux-fieldwork/upstream-packets/units/19-tarfilter-pax-idshift

git apply --check "$packet/patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch"
git apply --check "$packet/patches/0002-tests-cover-pax-idshift.patch"
git apply "$packet/patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch"
git apply "$packet/patches/0002-tests-cover-pax-idshift.patch"

git diff --check
git diff -- tarfilter tests/tarfilter-idshift
black --check ./tarfilter
./make_mirror.sh
CMD=./mmdebstrap ./coverage.sh tarfilter-idshift
CMD=./mmdebstrap ./coverage.sh tarfilter-idshift
```

Record the exact candidate commit, Black result, named-test statuses, generated-test lint/format results, cleanup, cache state, immediate rerun, and complete two-file diff review in `TESTS.md` and `HANDOFF.md`.

## Unresolved blockers

- technical: exact current-head application, Black, generated-test lint/format, and QEMU-backed native execution;
- compatibility: alternate Python and external tar-reader matrix remain optional review questions after the native gate;
- overlap: indexed search is clean; recheck before authorization;
- environment or tooling: current environment lacks Black, ShellCheck, shfmt, upstream DNS access, and a prepared QEMU test tree;
- authority: external contact is unauthorized;
- destination: controlled upstream fork and candidate branch are absent.

## Files to read first

1. `README.md`
2. `HANDOFF.md`
3. `PROJECT_INSTRUCTIONS.md`
4. `TESTS.md`
5. `SOURCE_MAP.md`
6. `DECISIONS.md`
7. `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch`
8. `patches/0002-tests-cover-pax-idshift.patch`
9. issue #37 and PR #78 exact head/review

## External-contact state

`false; none occurred`. The #397 claim and checkpoints are internal Linux Fieldwork coordination actions. No upstream issue, pull request, comment, email, review, reaction, or other public upstream action occurred.

## Do not repeat

- avoid treating a green Debian package autopkgtest as proof for `tarfilter-idshift`; that configuration skips the QEMU-required test;
- avoid bypassing the project runner for the final focused receipt, because it owns Black, generated-test ShellCheck/shfmt, local-source copying, and QEMU dispatch;
- avoid rebuilding every PAX key; it risks unrelated metadata loss;
- avoid assigning numeric PAX strings directly to ordinary IDs; key removal preserves the writer's representation choice;
- avoid using the early malformed PR #78 patch revisions;
- avoid creating a second upstream test file before new evidence changes the ownership decision;
- avoid editing shared `upstream/mmdebstrap/tarfilter` or its test on the packet branch;
- avoid folding unit 18 no-option passthrough or unit 15 broader metadata work into this candidate.