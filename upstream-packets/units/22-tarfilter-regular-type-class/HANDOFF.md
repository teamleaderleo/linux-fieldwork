# Handoff — unit 22 regular-file type class

Date: 2026-08-01  
Worker or variant: GPT-5.6 Thinking  
State: `ACTIVE`  
External contact authorized: `false`

## Exact repository state

- Repository: `teamleaderleo/linux-fieldwork`
- Branch: `upstream/unit-22-tarfilter-regular-type-class`
- Base: `main@6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Exact predecessor before this final handoff refresh: `0f8af82c560f6a97ecf7ac7acdf41d0aa6a6f3c1`
- Current head: the commit updating this file; issue #397 checkpoint and draft PR #410 record the resulting SHA.
- Internal draft PR: #410
- Packet: `upstream-packets/units/22-tarfilter-regular-type-class/`

## Exact upstream and candidate identities

- Canonical upstream: `https://gitlab.mister-muffin.de/josch/mmdebstrap`
- Base: `main@77ec9be5417ee44c96343d2347145585da1b1f94`
- Current relevant source: Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Current defect: `TypeFilterAction` maps `REGTYPE`/`0` only to `tarfile.REGTYPE`
- Debian packaging context: `debian/1.5.7-3@6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Historical candidate: PR #77 head `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7`, merge `4b9e24b0b20c1398dcae825310c6b7d0d5c273d0`
- Historical exact-head CI: run `30537313944`, success
- Source patch: `patches/0001-tarfilter-treat-nul-as-regular.patch`
- Python packet regression: `scripts/test_regular_type_class.py`
- Native shell test: `native/tests/tarfilter-regular-type-class`
- Native registry stanza: `native/coverage.txt.fragment`
- Exact-source integration gate: `tests/test_unit22_tarfilter_native_packet.py`
- Controlled upstream fork: `NEEDS FORK`

## Current state

`ACTIVE`. Human approval is not a blocker. Current upstream, defect presence, source ownership, selected mechanism, native test owner, cross-consumer semantics, and bounded overlap are resolved. Hosted exact-source completion and complete-upstream native gates remain technical work.

## Completed work

1. Read issue #397, project instructions, packet protocol/INDEX, and every linked carrier.
2. Created the canonical branch and full durable packet.
3. Retained the one-line correction and historical exact-source regression/CI evidence.
4. Identified canonical upstream and exact current base/source identity and confirmed the defect remains current.
5. Corrected the unit from `HOLD` to `ACTIVE` and corrected the destination from packaging Salsa to canonical Forgejo implementation upstream.
6. Re-read units 01, 15, and 16; none owns `TypeFilterAction` regular-class membership or blocks this unit's order.
7. Read upstream `tests/tarfilter-idshift`, `coverage.txt`, `coverage.py`, and `run_null.sh` and mapped the native test contract.
8. Added the native shell test, registry fragment, and exact-source Linux Fieldwork gate.
9. Opened internal draft PR #410 for hosted CI; no upstream contact occurred.
10. Probed Python 3.13.5: `REGTYPE == b"0"`, `AREGTYPE == b"\0"`, and both satisfy `TarInfo.isfile()`.
11. Verified Python USTAR round-trip preserves both bytes and payloads.
12. Verified GNU tar 1.35 lists and extracts both as ordinary regular files with exact payloads.
13. Ran the native shell test against a faithful minimal filter model: baseline failed with leaked `nul-regular`; candidate passed twice.
14. Verified GNU patch 2.8 is available locally; shellcheck/shfmt are absent, so no local formatting claim is made.
15. Performed a bounded current Forgejo issue/pull-request overlap search; no visible equivalent work was found.
16. Recorded direct Git DNS failures as environment transport limitations, not product results.
17. Refreshed README, source map, deep dive, tests, decisions, upstream drafts, and this handoff with exact findings and remaining donuts.

## Latest distinguishing result

Both Python 3.13.5 and GNU tar 1.35 classify type flags `b"0"` and `b"\0"` as regular files. Current mmdebstrap stores only `b"0"` for the documented regular selector. The native regression fails on the unchanged mapping because `nul-regular` survives, then passes twice when the selector stores both bytes. Historical exact-source CI already passed the retained candidate. The new exact-source hosted gate is queued and therefore supplies no new success claim yet.

## Current hosted state

- Draft PR: #410
- Exact predecessor head: `0f8af82c560f6a97ecf7ac7acdf41d0aa6a6f3c1`
- Latest observed run for that predecessor: `30694081756`
- Workflow/job state: queued
- Interpretation: queued is not evidence.

## First incomplete step

Resolve the current PR #410 head, fetch its associated `Linux Fieldwork CI` run, and inspect the `lab-tools` job after completion. On failure, fetch decoded logs and repair the first owned failure. On success, record exact run/job/step results in `TESTS.md`, this handoff, PR #410, and issue #397.

## Next complete-upstream action

In an environment with working Git transport:

```sh
git clone https://gitlab.mister-muffin.de/josch/mmdebstrap mmdebstrap-unit22
cd mmdebstrap-unit22
git checkout 77ec9be5417ee44c96343d2347145585da1b1f94
git rev-parse HEAD
git hash-object tarfilter
git status --short
```

Then install the native test as executable, add the `coverage.txt` stanza, apply the source patch with zero fuzz/offsets, run the real shellcheck/shfmt path, run `CMD=./mmdebstrap ./coverage.py --dist unstable tarfilter-regular-type-class`, run the relevant broader gate, clean and rerun, compose with adjacent tarfilter candidates, and review the complete diff plus refreshed overlap. Move directly to `READY FOR AUTHORIZATION` when those technical gates pass.

## Pending gates

- PR #410 exact-head CI completion and raw log review;
- upstream shellcheck/shfmt acceptance;
- complete exact upstream checkout;
- zero-fuzz/zero-offset source/test/registry application;
- focused native and relevant broader execution;
- cleanup and immediate rerun;
- executable native test mode;
- adjacent-candidate compatibility run;
- complete final diff and refreshed overlap.

## Cleanup and authority

Local probes used temporary directories and removed their state. Failed clone targets contain no successful checkout. No mounts, sockets, containers, package installs, background processes, credentials, upstream forks, upstream branches, public issues, public pull requests, comments, reviews, or email were created. Internal branch, packet, draft PR #410, and issue checkpoint are intentional.

External contact remains unauthorized and requires explicit unit-specific authorization.
