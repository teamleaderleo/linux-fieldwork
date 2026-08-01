# HANDOFF — unit 11 coverage backend cancellation

Date: 2026-08-01  
State: `ACTIVE`  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-11-coverage-backend-cancellation`  
Last content head before this handoff commit: `ebfee4fa7d734b8278c7a9b69857464abe3b47d2`  
External contact authorized: `false`  
External contact made: `none`

## Exact stopping point

The durable unit packet has been created from the canonical protocol and contains:

- a retained upstream-root product patch;
- current state and exact identities;
- full source/carrier map;
- mechanism, compatibility, rejected alternatives, and open discriminators;
- historical test receipts separated from unexecuted current-upstream gates;
- dated decisions;
- polished upstream issue and pull-request drafts;
- this handoff.

The selected product mechanism is PR #313's narrow candidate:

```python
proc = subprocess.Popen(argv, start_new_session=True)
...
try:
    os.killpg(proc.pid, signal.SIGTERM)
except ProcessLookupError:
    pass
proc.wait()
print("interrupted by SIGINT", file=sys.stderr)
raise SystemExit(130)
```

The retained patch is:

`upstream-packets/units/11-coverage-backend-cancellation/patches/0001-coverage-own-selected-backend-group.patch`

## Exact identities

- canonical upstream repository: `https://gitlab.mister-muffin.de/josch/mmdebstrap`;
- intended branch: `main`;
- current upstream head observed: `77ec9be5417ee44c96343d2347145585da1b1f94`;
- controlled fork: `NEEDS FORK`;
- Linux Fieldwork imported source: `upstream/mmdebstrap/coverage.py`;
- imported source blob: `9a522484aef05deae514a98e4b6adf5feb6c886d`;
- historical canonical candidate: PR #313 head `dfc6d0503fb844f4c428ce16a567a9fdcd35280a`;
- executed mechanism generation: `e90fc438f530f7bd78ffd6fd1ba24c665bd96913`;
- mechanism CI: `30632491641`, job `91161937871`, success;
- current-head Linux Fieldwork CI: `30633602052` / 943, success;
- QEMU refinement: PR #339 head `8253ab2ef6fed22b34fc5f5d6d20cda75c25e2c7`, CI `30633578396` / 942, success;
- stronger policy research: issue #341 / closed PR #347, no product escalation selected.

## Work completed in this session

1. Read issue #397 and its canonical workflow comment.
2. Read `upstream-packets/README.md` and `upstream-packets/INDEX.md`.
3. Claimed unit 11 internally on issue #397.
4. Created branch `upstream/unit-11-coverage-backend-cancellation` from current Linux Fieldwork `main`.
5. Read direct and superseding carriers: issues #141, #306, #341; PRs #143, #204, #313, #332, #336, #339, #347, and #353; exact retained patches; relevant comments and receipts.
6. Verified Linux Fieldwork `main` still contains the original immediate-child launch/terminate/`break` block in blob `9a5224...`.
7. Verified the canonical Forgejo repository advertises `main` at `77ec9be...` and identifies `coverage.py` as unchanged since its 2024 formatting commit.
8. Reframed the exact PR #313 product hunk as an upstream-root patch against `coverage.py`.
9. Recorded all exact evidence and pending gates in the packet.
10. Made no external contact.

## Latest distinguishing result

Historical exact execution under parent-only SIGINT:

| Variant | Driver status | Nested responsive work | Later work |
| --- | ---: | --- | --- |
| imported baseline | 0 after deliberate release | survives before release | yes |
| status-only predecessor | 130 after deliberate release | survives before release | yes |
| selected group candidate | 130 | no live in-group process | no |

This result was executed on PR #313's mechanism generation and supported across null, QEMU-wrapper, and actual passwordless-sudo models.

## First incomplete step

Create or obtain a clean local checkout of canonical mmdebstrap at exact commit `77ec9be5417ee44c96343d2347145585da1b1f94`, then apply the retained patch with zero fuzz and compile `coverage.py`.

Exact initial commands are recorded in `TESTS.md`:

```sh
set -eu
git status --short
test "$(git rev-parse HEAD)" = 77ec9be5417ee44c96343d2347145585da1b1f94
patch --batch --forward --fuzz=0 -p1 < /path/to/0001-coverage-own-selected-backend-group.patch
python3 -m py_compile coverage.py
git diff --check
git diff -- coverage.py
```

## Next safe technical action

1. Use a network-capable worktree or a controlled fork after internal fork authorization.
2. Apply the packet patch to exact upstream `77ec9be...` with `--fuzz=0`.
3. Record the resulting candidate commit and `coverage.py` blob in `README.md`, `SOURCE_MAP.md`, and this handoff.
4. Port the PR #339-strengthened lifecycle fixture into the smallest upstream-acceptable regression.
5. Run null, QEMU-wrapper, sudo, unsignaled, cleanup, and immediate-rerun controls on the exact candidate.
6. Run the full feasible upstream gate and record exact commands and output.
7. Change state to `READY FOR AUTHORIZATION` only when the technical gates are complete.

## Blockers and caveats

- The execution container lacked DNS access, so this session could not create a canonical upstream shell checkout or execute the patch there.
- A controlled upstream fork has not been identified: `NEEDS FORK`.
- Historical CI is strong mechanism evidence and is not a substitute for current-upstream execution.
- TERM-resistant descendants, repeated SIGINT, group escape, cleanup timeout, and TERM-to-KILL remain outside the selected product claim.
- No eligible independent upstream review exists because no upstream candidate has been published.

## Recovery guide

Read in this order:

1. `README.md`;
2. `DECISIONS.md`;
3. `TESTS.md`;
4. `SOURCE_MAP.md`;
5. `DEEP_DIVE.md`;
6. retained patch;
7. `UPSTREAM_PR.md`.

Use issue #397 only for routing. This packet is the unit's durable technical record.

## Authorization boundary

Internal repository work may continue. Creating a public issue, pull request, review, email, comment, release, or package upload requires explicit authorization. No upstream contact occurred.
