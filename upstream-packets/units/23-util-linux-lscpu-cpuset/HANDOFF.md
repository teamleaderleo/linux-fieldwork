# Handoff

## Current state

State: `HOLD`  
Unit: issue #397, unit 23  
Linux Fieldwork branch: `upstream/unit-23-util-linux-lscpu-cpuset`  
Exact durable evidence head before this HANDOFF commit: `c75e4aac6d00daf3998515ff2eead50c9b05920d`  
Branch base: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`  
External-contact state: unauthorized; none made

The exact final branch tip that adds this HANDOFF is recorded in the unit checkpoint on issue #397. The technical tree through `c75e4aac...` contains every packet file, retained patch, receipt, and index change except this HANDOFF file.

## Executive result

The canonical carriers are about cpuset output ownership after `ul_path_cpuparse()` frees an allocation on parse failure. The issue/index phrase about deriving ownership from an owning cgroup mount has no matching mechanism in those carriers.

Upstream owns the source correction in commit `4581ede384f22983d6155768635ce43cb5304cb0`, with stable cherry-pick identity `3cd5f1dd69495864f3046cdbcefa104786fe5a27`. Current util-linux `master`, `stable/v2.40`, `stable/v2.41`, and `stable/v2.42` all contain free-then-NULL.

Debian testing and unstable carry newer fixed upstream releases. Debian trixie stable still ships `util-linux 2.41-5`. That package uses upstream 2.41, whose `lib/path.c` lacks the NULL assignment, and the published Debian patch series contains no `cpuset`, `lib/path.c`, or `4581ede` match. Debian trixie is the remaining plausible maintained destination, pending exact package-level execution.

## Completed work

- read issue #397, `upstream-packets/README.md`, `upstream-packets/INDEX.md`, and the canonical workflow comments;
- read Linux Fieldwork PR #387, issue #234 and all comments, draft PR #239, the retained investigation README, patch, fixture, model, runner, and test;
- read util-linux issues #3641 and #4401 and all comments;
- read canonical commits `4581ede...` and `3cd5f1d...`;
- checked exact current upstream heads and `lib/path.c` on master and stable/v2.40, v2.41, and v2.42;
- checked upstream tag `v2.41` and retained its affected `lib/path.c` blob identity;
- checked current Debian trixie/testing/unstable package versions and Debian `2.41-5` published patch series;
- claimed unit 23 on issue #397;
- created branch `upstream/unit-23-util-linux-lscpu-cpuset` from exact main `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`;
- created the complete required packet bundle;
- retained the canonical upstream patch with authorship;
- ran the full focused Linux Fieldwork regression: 5/5 pass in 0.082s;
- recorded baseline status 42, candidate status 0, zero-fuzz patch dry-run/application, final ordering, fixture and patch digests, cleanup, and unexecuted gates;
- drafted withheld Debian BTS and Salsa submissions with explicit send gates;
- changed the packet index state to `HOLD: Debian trixie package verification`;
- made no external contact.

## Exact identities

| Item | Identity |
| --- | --- |
| Linux Fieldwork evidence head | `c75e4aac6d00daf3998515ff2eead50c9b05920d` |
| Canonical LF carrier merge | `4a2196a705c06f5604879f655d465a4ac6fcb198` |
| Canonical upstream fix | `4581ede384f22983d6155768635ce43cb5304cb0` |
| Stable backport | `3cd5f1dd69495864f3046cdbcefa104786fe5a27` |
| Upstream affected tag/blob | `v2.41`; `42a33ffc53752ba5e00aed2396ca9a4fc876c1ef` |
| Current upstream master | `fd82c4043fab942b889f478800118c66edfbc39f` |
| Current stable/v2.40 | `160b7e47d4e6ba0fd15e66b4041bbdc67d2c457f` |
| Current stable/v2.41 | `2dacaf3eea391e3bbf48e7d3ecce02cafe045b6d` |
| Current stable/v2.42 | `84796d917bcbad37aecfdadf36d71fee5b356efd` |
| Debian target | trixie stable `util-linux 2.41-5` |
| Retained patch | `patches/0001-clear-cpuset-output-after-error.patch` |
| Patch SHA-256 | `3930c2402aeddb37149b2f50ef0b7b692674cfa3898a371f3fc174131672a523` |
| Retained fixture SHA-256 | `ee86a1384bdad67633dfb8e106937f43b00c33836be6791ffcb7099da3273f96` |
| Fresh receipt | `artifacts/2026-08-01-focused-regression.txt` |

## Latest distinguishing result

```text
/usr/bin/python3 -m unittest -v tests/test_util_linux_lscpu_cpuset_double_free.py

Ran 5 tests in 0.082s
OK

baseline: duplicate cleanup detected (status 42)
candidate: output cleared, later cleanup is harmless (status 0)
patch dry-run: status 0, --fuzz=0
patch application: status 0, --fuzz=0
fixture drift control: pass
```

## First incomplete step

Obtain the exact Debian trixie source package inputs:

```text
util-linux_2.41.orig.tar.xz
util-linux_2.41-5.debian.tar.xz
util-linux_2.41-5.dsc
```

Verify their published checksums, unpack them, apply the Debian quilt series, and record the final effective `lib/path.c` excerpt and SHA-256. This clears or disproves the inferred package gap before any build or submission work.

## Next safe technical action

1. unpack exact Debian `2.41-5` source and retain checksums;
2. inspect the effective `ul_path_cpuparse()` error path after Debian patches;
3. dry-run and apply `patches/0001-clear-cpuset-output-after-error.patch` with `--fuzz=0`;
4. build baseline and candidate packages where feasible;
5. execute issue #4401's attachment or a validated equivalent, plus ordinary valid text/JSON controls;
6. run relevant util-linux native tests and package gates;
7. clean all build/test state and immediately rerun;
8. update `TESTS.md`, `README.md`, `DECISIONS.md`, and this handoff with exact receipts;
9. only then request a human decision on Debian BTS versus Salsa versus hold.

## Stop conditions

Stop and record a new decision when any of these occurs:

- Debian effective source already contains an equivalent correction;
- trixie publishes a fixed package before the backport is prepared;
- the canonical patch conflicts or requires adjacent source changes;
- package-level tests identify a different first owner;
- ordinary output or status compatibility changes;
- issue #397 supplies exact carriers for a separate cgroup-mount unit;
- external-contact authorization changes.

## Unexecuted gates

- exact Debian source unpack and quilt result;
- baseline/candidate Debian package builds;
- issue #4401 attachment execution;
- ASan/Valgrind actual-binary run;
- valid text and JSON output comparison;
- util-linux native lscpu tests on the package tree;
- Debian autopkgtest/stable-update policy review;
- architecture matrix;
- public report or merge request.

## Workspace guide

- canonical state and identities: `README.md`
- source/carrier/ownership map: `SOURCE_MAP.md`
- mechanism and approach history: `DEEP_DIVE.md`
- exact test matrix and gaps: `TESTS.md`
- scope and hold decisions: `DECISIONS.md`
- retained patch: `patches/0001-clear-cpuset-output-after-error.patch`
- fresh test receipt: `artifacts/2026-08-01-focused-regression.txt`
- withheld Debian BTS draft: `UPSTREAM_ISSUE.md`
- withheld Salsa MR draft: `UPSTREAM_PR.md`

## Authority reminder

Internal source retrieval, builds, tests, packet updates, branches, commits, and issue checkpoints are authorized. No external issue, comment, email, pull request, merge request, review, or package upload is authorized. No upstream or downstream contact occurred during this pass.
