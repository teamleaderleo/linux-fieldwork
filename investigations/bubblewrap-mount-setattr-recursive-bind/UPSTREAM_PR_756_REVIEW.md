# Review of Bubblewrap PR 756 against Fieldwork runtime evidence

Date: 2026-08-11

Internal tracking: `teamleaderleo/linux-fieldwork#562`

## TL;DR

Bubblewrap already has an open upstream implementation of the `mount_setattr()` direction: https://github.com/containers/bubblewrap/pull/756, current head `03d25ff113f4eb9069221ff80d908a14ee41527d`, based on the same `2f55bae38468d0c50cf5df87b1e481e882b63acb` source generation used by this investigation.

The upstream candidate gets the core mechanism right: it applies `MOUNT_ATTR_NOSUID`, conditional `MOUNT_ATTR_NODEV`, conditional `MOUNT_ATTR_RDONLY`, and `AT_RECURSIVE` through the already-open destination fd, with an `ENOSYS` legacy fallback. Maintainer review also independently converged on the raw-syscall wrapper pattern already selected by Fieldwork.

Two decision-changing compatibility gaps remain in the current upstream head:

1. **`BIND_FAIL_OPEN` semantics are not preserved.** The upstream candidate calls `mount_setattr()` unconditionally before the legacy loop. The reviewed base already contains `--not-a-security-boundary`, which maps bind operations to `BIND_FAIL_OPEN`. In the legacy path, that flag is intentionally per-submount: one remount failure can warn, skip that submount, and continue applying flags to later submounts. A single recursive `mount_setattr()` has all-tree error granularity. The current PR therefore changes the explicit non-security mode from per-submount warning/continue behavior into whole-operation success/failure behavior.
2. **Only `ENOSYS` selects the legacy path.** Fieldwork reproduced an outer seccomp policy that denies `mount_setattr()` while still allowing the established `mount(2)` remount path. In that fixture the upstream candidate shape would fail where current Bubblewrap succeeds. The retained zero-size preflight gives a narrower discriminator: since Linux 5.12, `mount_setattr(-1, NULL, 0, NULL, 0)` returns `EINVAL` before the mount-permission check. Exact `EINVAL` means the Linux handler is reachable; a different preflight result can conservatively retain the legacy path. Once the real operation is selected, real errors still fail closed.

These are review findings, not upstream comments. No upstream interaction was made.

## Explain like I'm five

There is already a proposed upstream patch that uses Linux's newer “change all the mounts at once” operation.

Fieldwork found two cases the patch needs to distinguish:

- Bubblewrap has a special mode that deliberately says “this is not a security boundary; if one child mount cannot be changed, warn and keep going.” One all-or-nothing kernel operation does not behave like that.
- Bubblewrap can itself run inside another sandbox. That outer sandbox can block the new syscall while still allowing the old syscall Bubblewrap already uses.

So the safest first optimization is narrower: use the new syscall only for normal fail-closed binds when a harmless probe shows that the syscall really reaches Linux; otherwise keep the old path.

## Why care

PR 756 is the live carrier for the same source problem as this investigation, so further work should review and strengthen that carrier rather than act as if no implementation exists.

The `BIND_FAIL_OPEN` difference is a behavior-contract issue, not merely a performance edge. It was added specifically for non-security callers such as filesystem-layout users that prefer partial progress over fatal setup failure.

The syscall-mediation difference is a compatibility issue. A new optimization should not make Bubblewrap unusable under an outer containment layer when the old implementation still has enough authority to perform the requested mount operation.

## Exact identities

### Upstream candidate

- Repository: `containers/bubblewrap`
- PR: https://github.com/containers/bubblewrap/pull/756
- Base: `2f55bae38468d0c50cf5df87b1e481e882b63acb`
- Current reviewed head: `03d25ff113f4eb9069221ff80d908a14ee41527d`
- State observed: open, not draft
- Product files changed by the current head: `bind-mount.c`, `bind-mount.h`, `utils.c`, `utils.h`
- Upstream contact by this Fieldwork pass: none

### Fieldwork competing candidate

- Owned fork: `teamleaderleo/bubblewrap`
- Branch: `linux-fieldwork/mount-setattr-recursive-bind`
- Base: `2f55bae38468d0c50cf5df87b1e481e882b63acb`
- Candidate head: `d8bd56585ce31d4f9f5f7ef271bc47d2e029f51f`
- Internal draft PR: `teamleaderleo/bubblewrap#1`
- Diff: one commit, one file, `bind-mount.c`, +68/-2
- Hosted CI state at this checkpoint: no workflow run or commit status was attached after repeated checks; do not describe CI as executed
- Mechanical review note: connector replacement dropped the final newline from `bind-mount.c`; rebuild before presentation
- DCO/sign-off state: not prepared for upstream submission; no contributor identity was inferred or synthesized

### Upstream-review mirror

- Owned fork branch: `linux-fieldwork/review-pr-756`
- Exact mirrored upstream head: `03d25ff113f4eb9069221ff80d908a14ee41527d`
- Purpose: disposable read/review carrier only; not a submission candidate

## What PR 756 gets right

### Core attribute mapping

The current upstream candidate uses:

```text
base attr_set: NOSUID
!devices:      + NODEV
readonly:      + RDONLY
recursive:     + AT_RECURSIVE
```

That agrees with the source contract and with the retained Fieldwork runtime differential for `--bind`, `--dev-bind`, and `--ro-bind`.

### Destination-fd targeting

PR 756 applies the syscall through `dest_fd` with `AT_EMPTY_PATH`. Fieldwork independently tested this form and found it reproduced the intended recursive attributes on nested mounts and file binds while preserving unrelated `noexec`.

### Raw syscall wrapper

Review discussion on PR 756 rejected hard-coded cross-architecture syscall numbers and preferred the existing Bubblewrap `pivot_root()` pattern: use `__NR_mount_setattr` when supplied by the build headers, otherwise return `ENOSYS` and retain the old path.

Fieldwork reached the same boundary independently. A build whose headers do not know the syscall loses an optimization opportunity on a newer runtime kernel, but does not lose functional compatibility.

### Early-return shape

Maintainer review asked for an early return after successful `mount_setattr()` so the legacy path stays visually intact. The current PR now has that structure. The Fieldwork candidate also uses an early-return structure.

## Gap 1 — `BIND_FAIL_OPEN`

The base commit contains the new `BIND_FAIL_OPEN` policy used by `--not-a-security-boundary`.

Legacy behavior inside the recursive submount loop is:

```text
submount remount fails
  EACCES -> ignore as inaccessible
  otherwise + BIND_FAIL_OPEN -> warn, skip this submount, continue
  otherwise -> fail the bind
```

PR 756 attempts recursive `mount_setattr()` before reaching this loop regardless of `BIND_FAIL_OPEN`.

That creates two possible differences:

- syscall succeeds: every reachable mount receives the requested attributes, whereas legacy fail-open might have intentionally skipped one failing submount;
- syscall fails: the whole bind fails, whereas legacy fail-open might have warned for one submount and continued.

The smallest compatibility rule remains:

```text
BIND_FAIL_OPEN set -> legacy path directly
normal fail-closed bind -> eligible for mount_setattr path
```

A future optimization for fail-open mode needs its own policy and discriminator rather than inheriting the fail-closed all-tree syscall behavior accidentally.

## Gap 2 — syscall mediation

The retained `SECCOMP_COMPATIBILITY.md` fixture installed a seccomp filter that returned a chosen errno only for `mount_setattr` while permitting `mount(2)`.

Observed:

```text
mount_setattr -> EPERM   ; legacy root/submount remounts -> success
mount_setattr -> ENOSYS  ; legacy root/submount remounts -> success
```

The nested `noexec` control survived the legacy remounts while `nosuid,nodev` were added.

PR 756 falls back only when the **real** operation returns `ENOSYS`. An outer policy returning `EPERM` therefore converts an optimization-availability problem into a fatal bind failure.

Falling back on every real-operation `EPERM` would be unsafe because Linux can also return `EPERM` for genuine mount-attribute permission or locked-flag failures.

The zero-size preflight separates those classes more cleanly:

```text
probe mount_setattr(-1, NULL, 0, NULL, 0)
  exact EINVAL -> expected Linux handler contract reached
  other result -> keep legacy path

real mount_setattr operation, after selection
  success -> new path
  any error -> fail closed
```

Linux v5.12 and the current reviewed Linux source both validate the too-small `usize` before `may_mount()`, which is why the probe does not require mount privilege to produce the expected `EINVAL` signature.

This does not protect against every possible mediation action. A seccomp action that kills, traps, blocks for userspace notification, or deliberately emulates the exact `EINVAL` signature has a different boundary. The conservative exact-signature rule covers the demonstrated errno-mediation case without weakening real-operation error handling.

## Adjacent review — inaccessible submounts

The legacy path ignores `EACCES` from an individual submount remount because an unreadable mountpoint is not usable by the sandboxed user.

The fd-based recursive syscall does not perform the same userspace pathname walk for each child. That can turn a legacy path-lookup skip into either a successful restrictive attribute update or a kernel-level permission/locked-flag failure.

Current review does **not** justify treating a real recursive syscall `EPERM` as legacy fallback: that would also hide genuine locked-flag or permission failures. This remains a runtime compatibility context worth exercising before any final upstream recommendation.

## Current comparison

| Boundary | PR 756 current head | Fieldwork recommendation |
| --- | --- | --- |
| normal recursive bind | `mount_setattr` | `mount_setattr` when preflight selects it |
| `--bind` attributes | `nosuid,nodev` | same |
| `--dev-bind` attributes | `nosuid` | same |
| `--ro-bind` attributes | `nosuid,nodev,ro` | same |
| unrelated mount flags | additive `attr_set` | same; runtime `noexec` preservation proven |
| old build headers / no `__NR_mount_setattr` | `ENOSYS` wrapper fallback | same |
| old runtime kernel | real call `ENOSYS` fallback | preflight does not return `EINVAL`, so legacy |
| errno-style outer syscall mediation | real call becomes fatal except `ENOSYS` | preflight mismatch -> legacy |
| real operation `EINVAL`/`EPERM`/`EBUSY` | fail | fail closed |
| `BIND_FAIL_OPEN` | new all-tree syscall attempted | legacy per-submount path |
| destination-side writer + `ro` | syscall can return `EBUSY` | fail closed; atomicity control retained |
| source-side writer + `ro` | not specifically demonstrated by PR | Fieldwork runtime control succeeded |

## Review disposition

The existence of PR 756 changes the useful next action.

Do not prepare an independent upstream PR for the same issue while this carrier is active. Retain the owned candidate as a competing implementation/evidence surface, but use it primarily to test the two missing compatibility boundaries.

Before any upstream interaction is considered, the strongest next gates are:

1. execute a real Bubblewrap build and focused bind matrix on the Fieldwork candidate or a stacked review variant;
2. exercise `BIND_FAIL_OPEN` with an induced submount failure and prove the legacy warning/continue behavior survives;
3. exercise the support preflight under errno-style syscall mediation inside the actual Bubblewrap process;
4. exercise at least one inaccessible-submount case to distinguish successful kernel-tree handling from a new locked-flag failure;
5. rebuild the owned candidate cleanly with a final newline and any project-preferred helper placement;
6. preserve one atomic product commit and obtain a real configured contributor sign-off only if a human later decides to submit anything.

## Authority

No upstream comment, review, reaction, issue, pull request, or email was created or modified by this pass.

Reading the public PR and mirroring its exact head into an owned disposable branch are evidence/review actions only.
