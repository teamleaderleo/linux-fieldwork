# Current handoff

Updated: `2026-08-01 08:09 +08:00`  
Worker or variant: `GPT-5.6 Thinking`  
State: `HOLD`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-17-directory-mtime-authority` |
| Linux Fieldwork technical-content parent | `9dbe3a81ddb87d72ebebc4098b0807941f9d7d0a` |
| Linux Fieldwork final head | this HANDOFF file's containing commit; exact SHA is recorded in the unit checkpoint on #397 |
| Upstream base repository/branch | `https://gitlab.mister-muffin.de/josch/mmdebstrap`; current branch/revision `NEEDS CURRENT UPSTREAM PIN` |
| Retained imported source | mmdebstrap 1.5.7, `upstream/mmdebstrap/mmdebstrap`, blob `41aa46f989a2660cebdb0138e0847cde25b269a3` on base `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Controlled upstream fork/branch | `NEEDS FORK`; candidate branch unselected |
| Descriptor candidate | PR #389 head `0319755b71ec594f2019cf40cd3cf9ee68ad7d60` |
| Authority matrix | PR #394 head `cffc0ce00f57050539a0e11f11e609d13e9ca604` |
| Pathname carrier reviewed | PR #395 live head `74c996394819c3a717d55193d84336c2e06b3b7c`; generated merge `a7fa7fe838e499ee52912c7be276cc89cfad4dec` |
| Selected product patch or series | none |
| Owning issues | #397 unit 17; policy #380; authority #392 |
| Latest workflow evidence | PR #395 Linux Fieldwork CI `30659899178` / 1099 success; dedicated run `30659899105` / 25, job `91253360438`, failure |
| Baseline artifact | run 999 artifact `8798679560`, digest `sha256:50d8ab7a20cb241ff9821b35329508ecdb0c58cbd3dec348c18d68d1dfe7a244` |

## Current bounded claim

Directory-only mtime normalization is the selected policy class for explicit-epoch root/chrootless direct tar output. Full timestamp normalization destroys older regular-file mtimes, and comparison-only normalization weakens the byte-identity contract.

No product implementation is selected. Descriptor mutation prevents pathname redirection and retains an unresolved operation-authority question after out-of-root rename. The packet process probe is mechanically tested but has not run at real mmdebstrap archive boundaries.

PR #395 live head is unfit as the selected candidate because it:

1. overwrites directory access time through `utime($mtime, $mtime, path)`;
2. retains path-based check-to-mutation identity risk;
3. lacks a completed exact-head real product-helper metadata run.

## Work completed in this pass

- refreshed issue #397, `upstream-packets/README.md`, and `upstream-packets/INDEX.md`;
- read the unit carrier chain and exact current identities for #380, #392, PRs #383, #384, #386, #388, #389, #390, #391, #393, #394, and #395;
- confirmed the unit branch existed and was ahead of `main` from base `6cc74d...`;
- reviewed all nine changed paths in PR #395 live head;
- found and recorded the directory-atime overwrite;
- confirmed the existing path authority gap remains;
- inspected exact-head workflow runs and job logs;
- classified dedicated run `30659899105` as a whole-source formatting-gate failure;
- confirmed the real product-helper metadata step was skipped and no receipt artifact existed;
- completed the packet README, source map, deep dive, tests, decisions, live-head review, upstream draft boundaries, and this handoff;
- made no external contact.

## Changed paths

- `upstream-packets/units/17-directory-mtime-authority/README.md`
- `upstream-packets/units/17-directory-mtime-authority/SOURCE_MAP.md`
- `upstream-packets/units/17-directory-mtime-authority/DEEP_DIVE.md`
- `upstream-packets/units/17-directory-mtime-authority/TESTS.md`
- `upstream-packets/units/17-directory-mtime-authority/DECISIONS.md`
- `upstream-packets/units/17-directory-mtime-authority/LIVE_HEAD_REVIEW.md`
- `upstream-packets/units/17-directory-mtime-authority/UPSTREAM_ISSUE.md`
- `upstream-packets/units/17-directory-mtime-authority/UPSTREAM_PR.md`
- `upstream-packets/units/17-directory-mtime-authority/HANDOFF.md`
- `upstream-packets/units/17-directory-mtime-authority/scripts/archive_boundary_process_probe.py`
- `upstream-packets/units/17-directory-mtime-authority/scripts/test_archive_boundary_process_probe.py`

## Distinguishing observations

- PR #395's helper uses both epoch arguments to `utime`; Perl assigns the first to atime and the second to mtime.
- The candidate unit test positively requires the incorrect two-epoch call and contains no directory-atime negative control.
- The real metadata probe also lacks an atime assertion.
- PR #395's path `lstat` followed by path `utime` retains the already-known replacement gap.
- Dedicated run `30659899105` applied the patch exactly and passed Perl syntax plus synthetic candidate tests.
- The run failed when whole-source sid `perltidy` output differed at char 1676, line 42.
- The real product-helper metadata matrix was skipped; artifact upload found no files.
- PR #395's body still names earlier head `e700839...`; use live ref `74c996...`.
- The primary unit discriminator remains archive-boundary process quiescence, not another descriptor-membership check.

## Gates completed

- packet probe parser/live descendant/zombie/self-exclusion controls: 4/4 PASS from the recorded local execution;
- PR #395 complete nine-file diff review: COMPLETE;
- PR #395 current workflow and job-log inspection: COMPLETE;
- packet required-file bundle: COMPLETE;
- external-contact boundary check: COMPLETE; authorization remains false.

## Red or neutral runs classified

- PR #395 dedicated run `30659899105` / 25: red, first owner is the whole-source sid formatting gate; product real-metadata step did not run.
- PR #395 Linux Fieldwork CI `30659899178` / 1099: green repository gate only; it does not clear atime or authority findings.
- local clone attempt in this environment: neutral tooling limitation; DNS resolution for GitHub was unavailable, so no checkout or new local rerun occurred in this pass.

## Cleanup state

No package roots, mounts, containers, sockets, long-lived processes, or imported-source modifications were created in this pass. The failed local clone created no repository checkout. GitHub branch commits and packet files are the intentional retained state.

The earlier packet probe tests recorded in `TESTS.md` cleaned helper processes, zombie ownership, temporary roots, and JSON temporary files.

## First incomplete step

Create a retained, evidence-only instrumentation patch against the exact imported source blob `41aa46f...` that invokes `scripts/archive_boundary_process_probe.py` synchronously at both required worker phases:

1. immediately after `setup($options)` returns;
2. immediately before the root/chrootless GNU tar `system(...)` call.

The patch must write receipts outside the temporary root, use worker PID `$$`, leave product behavior unchanged, and fail closed only in the dedicated evidence execution. It must not be applied to an upstream branch or sent publicly.

## Next safe action

From a checkout of `upstream/unit-17-directory-mtime-authority`:

```text
python3 -m py_compile \
  upstream-packets/units/17-directory-mtime-authority/scripts/archive_boundary_process_probe.py \
  upstream-packets/units/17-directory-mtime-authority/scripts/test_archive_boundary_process_probe.py

python3 -m unittest -v \
  upstream-packets/units/17-directory-mtime-authority/scripts/test_archive_boundary_process_probe.py

# Then create a retained patch against exact blob 41aa46f... only.
# Gate the instrumentation with a Linux Fieldwork-only environment variable.
# Write four JSON receipts per repetition:
#   root-after-setup, root-before-tar,
#   chrootless-after-setup, chrootless-before-tar.
# Run at least two clean repetitions plus one adjacent uninstrumented control.
```

Required receipt review:

- classify live and zombie descendants separately;
- inspect temporary-root cwd/root/exe/fd references;
- record process group, session, cgroup, namespace, UID, and start time;
- prove the synchronous probe PID is excluded;
- compare package result and cleanup with the adjacent uninstrumented control;
- retain exact commands, kernel/runtime identities, receipts, hashes, and cleanup in `TESTS.md`.

## Unresolved blockers

- technical: real root/chrootless archive-boundary process receipts are absent;
- technical: no selected implementation preserves directory atime under a resolved authority model;
- compatibility: no-tree-mutation archive rewriting still needs PAX/xattr/link/sparse extraction controls if selected;
- overlap: current public upstream base and active equivalent work remain unrefreshed;
- environment or tooling: real root/chrootless evidence requires a disposable capable runner with `/proc` visibility and package access;
- authority: external contact, upstream issue/MR creation, review, merge, and package publication remain unauthorized.

## Files to read first

1. `README.md`
2. `LIVE_HEAD_REVIEW.md`
3. `SOURCE_MAP.md`
4. `DEEP_DIVE.md`
5. `TESTS.md`
6. `DECISIONS.md`
7. issue #392 comment `5146645972`
8. PR #394 authority matrix
9. PR #389 descriptor candidate
10. PR #395 live diff and exact run `30659899105`

## External-contact state

`false; none occurred.` Internal Linux Fieldwork issue checkpoints are permitted by the packet workflow. No Debian/mmdebstrap upstream issue, merge request, email, comment, review, package upload, release, or deployment occurred.

## Do not repeat

- do not rerun full timestamp normalization; it destroys the old regular-file mtime;
- do not weaken the current byte comparison through comparison-only normalization without an explicit contract change;
- do not promote path-based `lstat` then path-based `utime`;
- do not add another best-effort descriptor ancestry check and present it as atomic containment;
- do not treat PR #395 Linux Fieldwork CI success as real product metadata evidence;
- do not inherit PR #391's artifact as proof of PR #395's exact live helper;
- do not trust PR #395 body head `e700839...` as current;
- do not run the full sid package matrix before the authority discriminator and access-time repair;
- do not contact upstream without explicit authorization.
