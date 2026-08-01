# Handoff — unit 22 regular-file type class

Date: 2026-08-01  
Worker or variant: GPT-5.6 Thinking  
State: `ACTIVE`  
External contact authorized: `false`

## Exact repository state

- Linux Fieldwork repository: `teamleaderleo/linux-fieldwork`
- Branch: `upstream/unit-22-tarfilter-regular-type-class`
- Branch base: `main@6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Exact branch head immediately before this HANDOFF refresh: `2bf0060a89ac55db74fe519ae18981dbb63c5582`
- Current branch head: the commit that updates this file; issue #397 checkpoint records the exact resulting SHA.
- Internal integration PR: draft PR #410
- Packet: `upstream-packets/units/22-tarfilter-regular-type-class/`

A commit cannot embed its own SHA. Use the issue checkpoint, PR #410 head, or `git rev-parse upstream/unit-22-tarfilter-regular-type-class` for the final handoff commit.

## Exact upstream and candidate identities

- Canonical upstream: `https://gitlab.mister-muffin.de/josch/mmdebstrap`
- Intended base branch: `main`
- Exact current upstream head: `77ec9be5417ee44c96343d2347145585da1b1f94`
- Current upstream defect: `TypeFilterAction` still maps `REGTYPE`/`0` only to `tarfile.REGTYPE`
- Current relevant source identity: Linux Fieldwork Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Debian package tag: `debian/1.5.7-3`
- Debian package resolved commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Canonical historical Linux Fieldwork candidate: PR #77
- Retained candidate head: `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7`
- Candidate merge commit: `4b9e24b0b20c1398dcae825310c6b7d0d5c273d0`
- Historical exact-head CI: run `30537313944`, success
- Source patch: `patches/0001-tarfilter-treat-nul-as-regular.patch`
- Python-focused packet regression: `scripts/test_regular_type_class.py`
- Proposed native test: `native/tests/tarfilter-regular-type-class`
- Proposed native registry stanza: `native/coverage.txt.fragment`
- Exact-source integration gate: `tests/test_unit22_tarfilter_native_packet.py`
- Controlled upstream fork: `NEEDS FORK`

## State

Unit 22 is `ACTIVE`. Current upstream, defect presence, selected mechanism, native test location, adjacent ownership, and bounded overlap are resolved. The hosted exact-source run and complete-upstream native execution remain technical work. Human approval is not a blocker and is not requested yet.

## Completed work

1. Read issue #397, its durable packet protocol, project instructions, packet README/INDEX, and every linked unit-22 carrier.
2. Created the canonical branch and full packet bundle.
3. Retained the one-line source patch and historical exact-source archive regression.
4. Identified canonical current upstream as `josch/mmdebstrap` `main@77ec9be5417ee44c96343d2347145585da1b1f94`.
5. Confirmed current relevant `tarfilter` content matches blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` and still carries the defect.
6. Corrected the packet from `HOLD` to `ACTIVE` and corrected the destination from Debian Salsa packaging context to canonical Forgejo implementation upstream.
7. Re-read units 01, 15, and 16 and established that they own separate code paths; no final-order blocker exists for unit 22.
8. Read upstream `tests/tarfilter-idshift`, `coverage.txt`, `coverage.py`, and `run_null.sh` to identify exact test ownership and execution mechanics.
9. Added upstream-native test `native/tests/tarfilter-regular-type-class` and exact registration stanza `native/coverage.txt.fragment`.
10. Added `tests/test_unit22_tarfilter_native_packet.py`, which verifies exact source blob identity, requires baseline failure, applies with GNU patch `--fuzz=0`, and requires two candidate passes.
11. Opened internal draft PR #410 to obtain exact-head Linux Fieldwork CI. This is internal Fieldwork work, not upstream contact.
12. Performed a Python 3.13.5 semantics probe: `REGTYPE` is `b"0"`, `AREGTYPE` is `b"\0"`, and both are regular according to `TarInfo.isfile()`.
13. Verified Python USTAR round-trip preserves both type bytes and payloads distinctly.
14. Verified GNU tar 1.35 lists and extracts both encodings as ordinary regular files with exact payloads.
15. Characterized the native shell test against a faithful minimal model: baseline failed with leaked `nul-regular`; candidate passed twice.
16. Performed a bounded canonical Forgejo issue/pull-request overlap search and found no visible equivalent current work.
17. Recorded the Git transport DNS limitation separately from product/source conclusions.
18. Updated `README.md`, `SOURCE_MAP.md`, `DEEP_DIVE.md`, and `TESTS.md` with exact findings and remaining donuts.

## Latest distinguishing result

The current upstream selector stores only `b"0"`, while both Python 3.13.5 and GNU tar 1.35 classify `b"0"` and `b"\0"` as regular files. The native test fails on the baseline because `nul-regular` survives `--type-exclude=REGTYPE`, then passes twice after the selected mapping expands the class to both bytes. Historical exact-source CI run `30537313944` passed the retained candidate. Draft PR #410 now carries an exact-source integration gate; its latest hosted run is queued, so no new hosted success is claimed yet.

## Current hosted state

- Internal draft PR: #410
- Workflow: `Linux Fieldwork CI`
- Latest observed state before this handoff refresh: queued
- Interpretation: queue presence is not evidence. Fetch the exact current PR head, associated run, jobs, steps, and failure logs before changing the disposition.

## First incomplete step

Inspect the latest exact-head workflow for PR #410:

1. Resolve the current branch head.
2. Fetch its `Linux Fieldwork CI` run.
3. When the `lab-tools` job completes, inspect every step.
4. On failure, fetch the decoded job log and repair the first owned failure.
5. On success, record exact run and job IDs in `TESTS.md`, this handoff, PR #410, and issue #397.

## Next safe technical action after hosted CI

Materialize the exact current upstream checkout in an environment with Git access:

```sh
git clone https://gitlab.mister-muffin.de/josch/mmdebstrap mmdebstrap-unit22
cd mmdebstrap-unit22
git checkout 77ec9be5417ee44c96343d2347145585da1b1f94
git rev-parse HEAD
git hash-object tarfilter
git status --short
```

Then:

1. Copy `native/tests/tarfilter-regular-type-class` to `tests/tarfilter-regular-type-class` and set executable mode.
2. Add `Test: tarfilter-regular-type-class` to `coverage.txt`.
3. Apply the source patch with zero fuzz and zero offsets.
4. Run shellcheck and shfmt through the real `coverage.py` path.
5. Run the focused candidate test using:

```sh
CMD=./mmdebstrap ./coverage.py --dist unstable tarfilter-regular-type-class
```

6. Run the relevant broader tarfilter/project gate.
7. Clean the checkout and rerun the focused test immediately.
8. Compose with adjacent tarfilter candidates for one compatibility run.
9. Review the complete diff and refresh overlap.
10. Move directly to `READY FOR AUTHORIZATION` when the technical gates pass.

## Tests and gates still pending

- draft PR #410 exact-head CI completion and raw log review;
- shellcheck/shfmt acceptance in the upstream runner;
- complete upstream checkout materialization;
- zero-fuzz/zero-offset source, test, and registry application;
- upstream-native focused execution;
- relevant broader gate;
- cleanup and immediate rerun;
- executable native test mode in the final diff;
- adjacent-candidate compatibility run;
- complete final diff and refreshed overlap review.

## Cleanup state

- Local semantics and GNU tar probes used temporary directories and removed their state.
- The native shell test owns a temporary directory with an EXIT/HUP/INT/TERM cleanup trap.
- The Python integration gate uses `TemporaryDirectory` and runs the candidate twice.
- Failed clone targets contain no successful checkout.
- No mounts, sockets, containers, package installations, background processes, or credentials were created.
- Linux Fieldwork branch, packet files, draft PR #410, and issue checkpoint are intentional retained internal state.
- No upstream fork, branch, issue, pull request, comment, review, email, or other public contact was created.

## Authority

Internal Linux Fieldwork work, draft PRs, tests, review, and issue checkpoints are authorized. External contact remains unauthorized. Explicit authorization is required before creating or using an upstream fork for public contribution, opening an upstream pull request, posting an upstream issue/comment/review, or sending email.
