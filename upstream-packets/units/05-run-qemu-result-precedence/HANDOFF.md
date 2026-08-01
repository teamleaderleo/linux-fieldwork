# HANDOFF — unit 05 `run_qemu.sh` result precedence

Handoff date: 2026-08-01  
State: `ACTIVE`  
External contact authorized: `false`  
External contact made: `none`

## Branch and packet

- Linux Fieldwork branch: `upstream/unit-05-run-qemu-result-precedence`
- Packet directory: `upstream-packets/units/05-run-qemu-result-precedence/`
- Complete technical packet head immediately before this final HANDOFF-only commit: `512a64ede55432fc87322d129516a09a06df18fe`
- The branch tip after handoff creation is the commit containing this file; its exact SHA is recorded in the unit checkpoint on issue #397.
- Canonical internal composition head: `2fe3f99364df29de217536dc35a4d03b10f49640`
- Canonical internal merge: `b196d6b45f496d8eb2d763922532ad257f24bba8`

## Current result

The canonical four-patch correction is extracted, copied byte-identically into this packet, and locally applicable to the exact imported source.

Selected result order:

```text
captured host failure
> completed guest or protocol failure
> first signal received during ordinary cleanup
> first cleanup failure
> success
```

The unit remains `ACTIVE` because current canonical Salsa `master` identity, live source comparison, current upstream carrier search, and upstream-native execution remain incomplete.

## Completed work

1. Read priority-zero issue #397 and unit 05 scope.
2. Read `upstream-packets/README.md` and `upstream-packets/INDEX.md`.
3. Read every directly linked carrier:
   - issue #269 and its comment;
   - issue #297;
   - canonical PR #319 and both complete reviews.
4. Read the component and fixture carriers required by the canonical lineage:
   - PR #270;
   - PR #282;
   - PR #290;
   - PR #304.
5. Created branch `upstream/unit-05-run-qemu-result-precedence` from current Linux Fieldwork `main`.
6. Posted the internal `CLAIMED — unit 05` checkpoint on issue #397.
7. Created the full required packet bundle:
   - `README.md`;
   - `SOURCE_MAP.md`;
   - `DEEP_DIVE.md`;
   - `TESTS.md`;
   - `UPSTREAM_ISSUE.md`;
   - `UPSTREAM_PR.md`;
   - `DECISIONS.md`;
   - `HANDOFF.md`.
8. Copied all four canonical patches into `patches/` and verified their Git blob IDs match the originals exactly.
9. Reconstructed the exact imported source and patch series in a disposable local Git repository.
10. Ran ordered `git apply --check`, ordered `git apply`, and `/bin/sh -n` successfully.
11. Preserved the raw receipt in `artifacts/2026-08-01-apply-and-syntax.txt`.
12. Identified the canonical upstream repository and current published Debian source metadata without contacting upstream.

## Exact identities

### Imported source

```text
path: upstream/mmdebstrap/run_qemu.sh
git blob: 426aeeb854173569b24e64d6eb85019f45bdf0b6
bytes: 2029
SHA-256: da89b51df80786f4e379b2ba5b033aab6c4e1d7acc8ba17cf57e67159a32e300
```

### Retained patches

```text
0001-preserve-primary-result.patch
  blob 387b0e1d9ae0adb067a2efdc5177bf8e6814668d

0002-retain-first-signal-through-cleanup.patch
  blob 8f4713ab827eaf643a97ba0f9d0e9b190ab7cd49

0003-retain-signal-during-exit-cleanup.patch
  blob 227b2600851828d20861d191c1bdb54c0008ca10

0004-preserve-completed-guest-before-cleanup-signal.patch
  blob 3769c89a002511c09350a6a9735910eb53947d66
```

### Composed source

```text
bytes: 2924
SHA-256: 8d2b0fdef2c93fcd3d97f296dfe58d3cbe198e8a02ac85930aa8c3c89aedb90f
/bin/sh -n: success
```

### Canonical historical gate

```text
PR: #319
base: 782774b01002abf37878d834a54d0bbf8b226397
head: 2fe3f99364df29de217536dc35a4d03b10f49640
merge: b196d6b45f496d8eb2d763922532ad257f24bba8
review: 4828231099
CI run: 30628645668
CI job: 889
result: success
repository tests: 276 passed
```

## Exact extraction commands and results

```sh
git apply --check patches/0001-preserve-primary-result.patch  # rc 0
git apply patches/0001-preserve-primary-result.patch          # rc 0

git apply --check patches/0002-retain-first-signal-through-cleanup.patch  # rc 0
git apply patches/0002-retain-first-signal-through-cleanup.patch          # rc 0

git apply --check patches/0003-retain-signal-during-exit-cleanup.patch  # rc 0
git apply patches/0003-retain-signal-during-exit-cleanup.patch          # rc 0

git apply --check patches/0004-preserve-completed-guest-before-cleanup-signal.patch  # rc 0
git apply patches/0004-preserve-completed-guest-before-cleanup-signal.patch          # rc 0

/bin/sh -n upstream/mmdebstrap/run_qemu.sh  # rc 0
```

## Public upstream observations

- Canonical repository: `https://salsa.debian.org/debian/mmdebstrap.git`.
- Intended branch: `master`.
- Debian Sources publishes mmdebstrap `1.5.7-3` for sid/forky.
- The Salsa tag view lists `debian/1.5.7-3` at abbreviated commit `6fde9997`.
- Debian Sources lists published `run_qemu.sh` at 2,029 bytes, matching the imported source size.

The equal byte count is a compatibility clue. A live byte comparison is still required.

## First incomplete step

Obtain a live canonical Salsa checkout and record:

```sh
git remote -v
git status --short --branch
git rev-parse HEAD
git rev-parse master^{commit}
git hash-object run_qemu.sh
sha256sum run_qemu.sh
wc -c run_qemu.sh
```

Then compare those identities with the imported blob and apply the packet series at repository-root `run_qemu.sh`.

## Next safe technical action

1. Clone or fetch `https://salsa.debian.org/debian/mmdebstrap.git` in a runtime with GitLab access.
2. Record the full current `master` SHA and live `run_qemu.sh` identities in `README.md`, `SOURCE_MAP.md`, `TESTS.md`, and this handoff.
3. Search current Salsa branches, issues, and merge requests for equivalent work.
4. Create a disposable candidate branch or a controlled fork only when needed; record `NEEDS FORK` until then.
5. Apply the four packet patches in order.
6. When paths or context changed, re-express the same four logical corrections as source-aligned commits and retain the original patches as historical evidence.
7. Run `/bin/sh -n`, the five focused Linux Fieldwork modules against the rebased source, and current upstream ordinary gates.
8. Clean the checkout and rerun the focused gate on the exact candidate head.
9. Refresh the upstream drafts with exact upstream identities and commands.
10. Change state to `READY FOR AUTHORIZATION` only after those gates pass and no current equivalent carrier supersedes the work.

## Expected test ownership

The canonical focused modules are:

```text
tests/test_run_qemu_result_precedence.py
tests/test_run_qemu_cleanup_failure_precedence.py
tests/test_run_qemu_first_signal_cleanup.py
tests/test_run_qemu_exit_cleanup_signal.py
tests/test_run_qemu_guest_before_cleanup_signal.py
```

They use reduced real-`/bin/sh` fixtures. Preserve their negative controls while adapting source paths or fixture extraction.

## Known hazards

- The packet patches reference `upstream/mmdebstrap/run_qemu.sh`; canonical upstream uses repository-root `run_qemu.sh`. Path rewriting may be required even when content matches.
- Patch 4 depends on completed guest publication before host cleanup. Reconfirm this sequence on live upstream.
- Ignoring later INT/TERM is appropriate across bounded cleanup. Escalation requires separate design if cleanup can block indefinitely.
- PR #290 is fixture history, not a fifth product patch.
- Equal file size does not establish byte identity.
- A green reduced harness cannot substitute for upstream-native gates or an authorized real QEMU smoke test.

## Environment limitation encountered

Direct GitLab clone, raw-file retrieval, and API access failed because the GitLab host could not be resolved in this runtime. GitHub repository reads/writes and public metadata views remained available. No source claim beyond the exact imported blob was made.

## Drafts and publication state

`UPSTREAM_ISSUE.md` and `UPSTREAM_PR.md` are polished internal drafts marked `DRAFT — DO NOT SEND`.

No upstream contact has been authorized. No upstream contact has been made. Do not create a Salsa issue, fork-visible merge request, comment, review, email, or mailing-list post without explicit authorization.

## Disposition and exit criteria

Current disposition: `ACTIVE`.

Move to `READY FOR AUTHORIZATION` after all of these are recorded on one exact live candidate head:

- current Salsa base identity;
- current source comparison;
- clean or documented patch application;
- focused behavior matrix;
- upstream ordinary gates;
- cleanup and immediate rerun;
- current equivalent-carrier search;
- clean worktree rerun;
- final drafts matching the exact delta.
