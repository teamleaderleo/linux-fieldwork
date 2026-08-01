# Current handoff

Updated: `2026-08-01 08:24 UTC`  
Worker or variant: `primary composition`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-08-current-sid-package-tests` |
| Linux Fieldwork technical head before this handoff update | `7df9137dd170eddacbb29d6af95b3ced78ac4661` |
| Linux Fieldwork final branch head | commit containing this `HANDOFF.md`; #397 checkpoint records the returned SHA |
| Internal execution carrier | draft PR #405; do not merge while unit remains `ACTIVE` |
| Canonical upstream | `https://salsa.debian.org/debian/mmdebstrap.git`; intended branch `master` |
| Executed source base | tag `debian/1.5.7-3`; commit `6fde999741f4fe1e7bf38079acf29432ef87a35e` |
| Controlled repository | `https://github.com/teamleaderleo/mmdebstrap` |
| Controlled repository state | `master` at `574048f2a720057b75e56622003932f344dc700a`; separate downstream history; canonical commit absent |
| Candidate branch | absent; create only from a verified exact Salsa commit |
| Candidate technical state | `DISTILLED SERIES GATE PASSED; LIVE REBASE PENDING` |
| Patch or series | `upstream-packets/units/08-current-sid-package-tests/patches/series` |
| Complete-series gate | `tests/test_upstream_packet_unit_08_current_sid_package_tests.py` |
| Gate source commit | `7782872ae2f731a27ed672df3a37b1d3b1581aa4` |
| Exact gate workflow | PR #405; `Linux Fieldwork CI` run `30690576566` / 1145 |
| Candidate head tested | `a361f91f1b9cc3167baad5fbd6c61bbee546a10e` |
| Generated merge tested | `4c5abe5e3777cfa57a5d1551e1975a8d769a8814` |
| Exact job | `lab-tools`, `91344449950`, success |
| Latest real sid package run | PR #361 workflow `30640356619` / 999; artifact `8798679560`; ZIP SHA-256 `50d8ab7a20cb241ff9821b35329508ecdb0c58cbd3dec348c18d68d1dfe7a244` |

## Current bounded claim

Four upstream package-test corrections are retained as one ordered series against exact Debian mmdebstrap revision `debian/1.5.7-3` / `6fde999741f4fe1e7bf38079acf29432ef87a35e`:

1. accept Deb822 source entries by rooting raw output paths before `exploded_list()`;
2. use `/usr/bin/mmdebstrap` for stable execution after directory changes;
3. deliver process-group SIGINT with current-sid-compatible dash builtin syntax;
4. run `root-without-cap-sys-admin` in a hook-free hard phase with immediate `create-directory` production and later broad-phase regeneration.

Historical current-sid integration proves the selected Deb822 handling, signal spelling, focused producer/consumer order, and broad fixture regeneration reached the next independent `chrootless` result. The exact distilled series applies and reruns cleanly under Linux Fieldwork CI.

A controlled GitHub repository now exists, clearing the repository-ownership question. It does not yet clear the ancestry/rebase gate: `teamleaderleo/mmdebstrap` currently follows a separate downstream import/update history and does not contain canonical Salsa commit `6fde999741f4fe1e7bf38079acf29432ef87a35e`.

## Work completed

- read and classified every directly linked unit-08 carrier;
- selected the upstream-facing four-patch boundary and excluded Linux Fieldwork-only machinery;
- pinned the imported executable base and retained historical current-sid receipts;
- added the exact series application/rerun gate;
- opened draft internal PR #405 solely as an execution carrier;
- ran Linux Fieldwork CI `30690576566` / 1145;
- validated four patch files and seven hunks;
- observed `test_series_applies_exactly_and_reruns_cleanly ... ok`;
- ran 439 tests in 166.008 seconds with final result `OK`;
- completed Python compile, shell syntax/help, deterministic receipt/digest, source immutability, temporary-tree cleanup, and hosted-runner cleanup checks;
- discovered and inspected `teamleaderleo/mmdebstrap`;
- recorded its default branch head `574048f2a720057b75e56622003932f344dc700a`;
- confirmed canonical Salsa commit `6fde999741f4fe1e7bf38079acf29432ef87a35e` is absent from that repository;
- made no Debian, Salsa, mmdebstrap, email, review, or other public contact.

## Exact distinguishing evidence

```text
validated 4 patch file(s) and 7 hunk(s)
fieldwork discovery retained 439 of 462 tests; removed 23 exact inherited duplicate(s)
test_series_applies_exactly_and_reruns_cleanly (test_upstream_packet_unit_08_current_sid_package_tests.Unit08CurrentSidPackageTestsSeriesTest.test_series_applies_exactly_and_reruns_cleanly) ... ok
Ran 439 tests in 166.008s
OK
```

Controlled-repository identity receipt:

```text
repository=teamleaderleo/mmdebstrap
default_branch=master
master=574048f2a720057b75e56622003932f344dc700a
canonical_base=6fde999741f4fe1e7bf38079acf29432ef87a35e
canonical_base_present=false
```

## Gates completed

- exact imported base identified;
- complete carrier/source ownership review;
- exact four-patch application and immediate rerun on a hosted checkout;
- zero-fuzz policy, expected-path receipts, Python compilation, shell parsing, deterministic candidate bytes, imported-source immutability, and cleanup;
- complete Linux Fieldwork suite on exact candidate head through PR #405;
- controlled GitHub repository located and inspected.

## Gates still open

- fetch current Salsa `master` and record its exact commit;
- search active upstream overlap for each correction;
- compare the controlled repository to canonical Salsa rather than assuming ancestry;
- create an exact canonical candidate branch in `teamleaderleo/mmdebstrap`;
- reapply or rebase the series with zero fuzz and zero offset;
- rerun the distilled-series gate against the refreshed source;
- run focused Deb822, direct command-path, SIGINT, focused-pair, and broad-regeneration tests;
- run current sid package tests from the exact upstream-facing series without LF proxy/evidence machinery;
- review the final exact upstream diff;
- obtain explicit authorization before any Salsa merge request or other public contact.

## Cleanup state

The hosted job completed post-checkout and orphan-process cleanup. The gate released both temporary source trees and verified the imported source remained unchanged. Repository inspection made no source changes in `teamleaderleo/mmdebstrap`.

GitHub intentionally retains the Linux Fieldwork unit branch, draft PR #405, packet, patches, test, workflow logs, issue coordination comments, and the user-controlled mmdebstrap repository.

## First incomplete step

Obtain the exact current commit for canonical Salsa `master`, then determine the safest way to establish an exact canonical branch in `teamleaderleo/mmdebstrap` without inheriting unreviewed downstream divergence.

## Next safe action

From a full checkout with Salsa access:

```sh
set -eu
git clone --filter=blob:none https://salsa.debian.org/debian/mmdebstrap.git /tmp/mmdebstrap-unit08-upstream
cd /tmp/mmdebstrap-unit08-upstream
git switch master
git pull --ff-only
printf 'upstream-master=%s\n' "$(git rev-parse HEAD)"
```

Record the exact commit. Add `https://github.com/teamleaderleo/mmdebstrap.git` as a separate remote and compare histories and trees. Do not merge the current GitHub `master` into the canonical source. Create a candidate branch only when its base is proven to be the exact fetched Salsa commit. Then search overlap, apply the four patches in order with `patch --batch --forward --fuzz=0 -p1`, capture receipts, run syntax checks, and rerun the packet gate.

## Unresolved blockers

- overlap: current Salsa `master` exact identity and equivalent-work search remain incomplete;
- ancestry: the controlled GitHub repository is a separate downstream lineage and needs an exact canonical branch;
- execution: focused upstream-native and exact current-sid package runs remain incomplete;
- compatibility: direct `/usr/bin/mmdebstrap` still needs package execution on the refreshed live head;
- authority: Salsa fork/MR creation and every public upstream action require explicit authorization.

## External-contact state

`false; none occurred`. Draft PR #405 and issue #397 comments are internal Linux Fieldwork coordination. The only outward-looking text remains unpublished in `UPSTREAM_ISSUE.md` and `UPSTREAM_PR.md`.

## Do not repeat

- do not assume `teamleaderleo/mmdebstrap` is an exact Salsa fork from its name alone;
- do not merge its current downstream `master` into the canonical candidate;
- do not rerun the imported-base gate merely to prove the recorded PR #405 result;
- do not revive the relative formatted installed-command proxy;
- do not move the capability consumer into the soft phase;
- do not mark `create-directory` hook-free-only;
- do not rerun the full sid matrix solely for run-999 `chrootless`; #380 owns that result;
- do not merge draft PR #405 while the packet remains `ACTIVE`;
- do not contact Debian or mmdebstrap upstream without explicit authorization.
