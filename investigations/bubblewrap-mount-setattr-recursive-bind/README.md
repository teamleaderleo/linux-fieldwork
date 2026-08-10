# Bubblewrap recursive bind attributes with `mount_setattr()`

## TL;DR

Bubblewrap's current recursive bind path snapshots `/proc/self/mountinfo`, applies the requested bind, then remounts the destination and each discovered submount one by one to add `nosuid`, usually `nodev`, and for `--ro-bind`, `ro`. On current Linux, `mount_setattr(AT_RECURSIVE)` is a close semantic fit for that attribute-application phase and moves the recursive tree walk into the kernel.

The strongest source-level result from this pass is narrower than “replace the loop and fall back on any old-looking error.” A compatibility path should treat `ENOSYS` as the unsupported-syscall discriminator. Generic `EINVAL` is unsafe as an old-kernel signal because `mount_setattr()` also returns it for genuine pathname, flag, and attribute errors. Linux's own mount_setattr selftest probes support with `ENOSYS` specifically.

Linux also prepares the complete recursive mount tree before committing attribute changes. Its selftest deliberately forces a recursive read-only request to fail on an open writer and verifies that every checked mount keeps its previous attributes. That is a useful property for Bubblewrap: the new path can remove the userspace mount-table snapshot/per-submount-remount race while avoiding a half-updated tree on that failure class.

Next action: implement a small compatibility wrapper and differential fixture in an owned Bubblewrap fork or disposable checkout, then compare the existing path and `mount_setattr()` path across `--bind`, `--dev-bind`, and `--ro-bind`, including a forced `ENOSYS` fallback and a recursive failure control.

Internal tracking: `teamleaderleo/linux-fieldwork#562`.

## Explain like I'm five

Bubblewrap copies a directory tree into a sandbox and then puts safety labels on every mounted filesystem inside that tree.

Today it makes a list of all those mounts and changes them one at a time. The list can become stale while Bubblewrap is walking it. Linux 5.12 added a syscall that can ask the kernel to apply the requested mount attributes to the whole tree in one operation.

Literal example:

`host tree with /work and a mounted /work/cache` → Bubblewrap recursively binds `/work` → asks Linux to add `nosuid,nodev,ro` to the full bound tree → both `/work` and `/work/cache` receive the requested attributes, or the recursive request fails before the tested attributes are committed.

## Why care

The current userspace walk has two concrete costs:

1. Bubblewrap issue 650 demonstrates a race where a mount disappears after `/proc/self/mountinfo` is read and before Bubblewrap remounts that entry, causing startup failure.
2. Repeating a full mount-table walk for many bind operations contributes to the long-standing scaling problem tracked around issue 384. Earlier optimization proposals grew into large mount-graph implementations; a maintainer later identified `mount_setattr()` as the more viable route.

For sandboxing callers, the security consequence is important: `--ro-bind` must not silently leave a surviving submount writable. The current maintainer direction is to preserve fail-closed behavior for security-boundary use while allowing the separately explicit `--not-a-security-boundary` mode to relax selected failures.

## Current state

- State: `EXECUTING`
- Exact working head: `containers/bubblewrap@2f55bae38468d0c50cf5df87b1e481e882b63acb`
- Latest authoritative gate or artifact: source/history + Linux syscall/selftest review recorded here
- First incomplete step: build and execute a differential nested-mount fixture
- Cleanup state: no runtime state created in this pass
- Next safe action: implement and run a small candidate on an owned fork or disposable checkout
- External-contact state: no upstream interaction authorized or made

## Intent and precedent

### Bubblewrap maintainer direction

Relevant upstream records:

- https://github.com/containers/bubblewrap/issues/650 — mount-table changes can make the current per-submount remount path fail during startup.
- https://github.com/containers/bubblewrap/issues/754 — open `help wanted` request to use `mount_setattr()` on newer kernels and retain the old path for older kernels.
- https://github.com/containers/bubblewrap/pull/629 and https://github.com/containers/bubblewrap/pull/630 — larger userspace optimization variants. In May 2026, a maintainer said the amount of code made high-confidence review difficult and pointed to issue 754 as the more viable approach.
- https://github.com/containers/bubblewrap/issues/653 — rationale for the later `--not-a-security-boundary` mode: sandboxing uses must fail closed when requested mount protections cannot be established; explicitly non-security uses may choose selected fail-open behavior.

The current head includes `--not-a-security-boundary`. Its committed test is a smoke test that proves the option is accepted. It does not execute the actual branch where a recursive submount remount fails and `BIND_FAIL_OPEN` warns and continues.

### Linux syscall contract

Primary source and test references reviewed:

- Linux `fs/namespace.c` current implementation of `mount_setattr()`.
- Linux `tools/testing/selftests/mount_setattr/mount_setattr_test.c`.
- Linux 5.12 UAPI definitions for `MOUNT_ATTR_RDONLY`, `MOUNT_ATTR_NOSUID`, `MOUNT_ATTR_NODEV`, `struct mount_attr`, and `AT_RECURSIVE`.
- Linux `mount_setattr(2)` documentation.

`mount_setattr()` first appeared in Linux 5.12. `AT_RECURSIVE` applies the change across the mount tree. `attr_set` adds mount properties while leaving unrelated existing properties in place when `attr_clr` is zero.

The kernel implementation performs a prepare walk before the commit walk. During preparation it checks whether attributes can change and, for read-only transitions, holds writers. If preparation fails, it unwinds those holds and returns an error. Only after successful preparation does it commit the new attributes across the tree.

The kernel selftest directly exercises this property. It creates a nested mount tree, applies recursive attributes, then holds a file open for writing in an interior mount and requests recursive read-only. The syscall fails and the test verifies the observed mount flags remain unchanged throughout the checked tree.

## Question

Can Bubblewrap replace the userspace recursive remount loop with `mount_setattr(AT_RECURSIVE)` on supported kernels while preserving:

- the existing `--bind` attribute contract;
- the existing `--dev-bind` attribute contract;
- the existing `--ro-bind` attribute contract;
- fail-closed security behavior;
- explicit non-security fail-open semantics where they remain applicable;
- support for systems whose running kernel or build headers predate `mount_setattr()`?

## Source

- Project: `containers/bubblewrap`
- Requested revision: current `main` observed during this pass
- Resolved commit: `2f55bae38468d0c50cf5df87b1e481e882b63acb`
- Candidate source commit: none
- Local source path: none; source read through the connected GitHub repository surface
- Import metadata: none

Supporting Linux sources were read from current `torvalds/linux`, plus Linux v5.12 UAPI definitions to establish the compatibility floor.

## Environment

- Distribution and release: source-analysis pass; no runtime distribution fixture
- Kernel and architecture: no Bubblewrap execution in this pass; Linux source contract reviewed, including 5.12 UAPI and current kernel implementation
- Shell: none for authoritative execution
- Privileges: no runtime mount operations executed
- Container, virtual machine, or host context: connector-backed source review
- Relevant tool versions: GitHub source/history access; no compiled Bubblewrap binary

## Baseline behavior

`setup_op_bind_mount()` always adds `BIND_RECURSIVE`. Bubblewrap's source comment explains why: a non-recursive directory bind could expose files hidden by host submounts.

`bind_mount()` then:

1. calls `mount(src, dest, ..., MS_BIND | MS_REC, ...)` for the recursive bind;
2. resolves and reopens the destination;
3. reads `/proc/self/mountinfo` and finds the destination plus its submounts;
4. derives the current flags for each discovered mount;
5. ORs in Bubblewrap's requested attributes;
6. remounts the destination;
7. walks the remaining mount-table entries and remounts them individually.

The current attribute mapping is:

| Bubblewrap operation | Attributes added |
| --- | --- |
| `--bind` | `MS_NOSUID | MS_NODEV` |
| `--dev-bind` | `MS_NOSUID` |
| `--ro-bind` | `MS_NOSUID | MS_NODEV | MS_RDONLY` |

Existing unrelated mount flags are preserved because the code reads current flags and ORs these requested bits into them.

During the recursive submount loop, `EACCES` is ignored. With `BIND_FAIL_OPEN`, other submount-remount errors produce a warning and the loop continues. Without `BIND_FAIL_OPEN`, the first such error aborts the bind setup.

## Hypothesis or candidate

### Candidate mechanism

After the recursive bind has created the destination mount tree, use a zero-filled `struct mount_attr` with only the corresponding `attr_set` bits:

```c
struct mount_attr attr = {
    .attr_set = MOUNT_ATTR_NOSUID |
                (devices ? 0 : MOUNT_ATTR_NODEV) |
                (readonly ? MOUNT_ATTR_RDONLY : 0),
};

sys_mount_setattr(AT_FDCWD, resolved_dest, AT_RECURSIVE,
                  &attr, sizeof(attr));
```

This is design pseudocode only. Names, wrapper placement, includes, compatibility definitions, error typing, and exact call ordering need implementation review.

With `attr_clr == 0`, the operation adds Bubblewrap's required attributes without intentionally clearing unrelated existing attributes. This mirrors the current OR-based behavior for the three relevant bits.

### Compatibility rule

Use `ENOSYS` as the clean signal that the running kernel lacks `mount_setattr()` and then execute the established userspace path.

Do **not** use generic `EINVAL` as an automatic old-kernel fallback. `mount_setattr()` documents and implements `EINVAL` for multiple real failures, including an invalid target relationship, unsupported flags, unsupported attribute bits, invalid propagation requests, and invalid attribute size/contents. Falling back after those errors can hide a programming error or change the failure contract.

If future runtime evidence identifies a narrowly scoped kernel/version-specific `EINVAL` that genuinely means “this exact supported operation is unavailable,” that case can receive its own discriminator. The present source evidence does not justify a blanket rule.

### Old build-header compatibility

A project can run on a new kernel while compiling against older headers, and Bubblewrap explicitly wants to keep older distributions viable.

Linux's own mount_setattr selftest demonstrates a compatibility pattern:

- define missing `MOUNT_ATTR_*` values locally;
- define missing `AT_RECURSIVE` locally;
- provide architecture-specific `__NR_mount_setattr` values when system headers lack them;
- call the syscall through `syscall()`;
- identify syscall absence via `ENOSYS`.

Bubblewrap already has a nearby project precedent in `utils.c`: its `pivot_root()` wrapper uses a raw syscall when `__NR_pivot_root` is available and returns `ENOSYS` otherwise.

A candidate should adapt the smallest maintainable version of that pattern to Bubblewrap's supported architecture/build matrix instead of requiring new libc wrappers.

### Interaction with `--not-a-security-boundary`

On a kernel where `mount_setattr()` succeeds, the current per-submount race disappears from attribute application, reducing the occasions where `BIND_FAIL_OPEN` would be needed for this mechanism.

A failed `mount_setattr()` needs deliberate policy. The safe initial candidate is:

- `ENOSYS` → use the legacy path;
- success → continue;
- other errors → preserve fail-closed behavior unless a separately demonstrated non-security policy says that exact error can be relaxed safely.

Blindly converting an all-tree syscall failure into “continue anyway” would create a broader semantic change than issue 754 asks for.

## Reproduction

No commands below were executed in this source-analysis pass. They define the first runtime fixture.

### 1. Build baseline and candidate

```sh
meson setup _build
meson compile -C _build
meson test -C _build
```

Record the exact Bubblewrap source head, candidate head, compiler, libc, kernel, and whether unprivileged user namespaces are enabled.

### 2. Create a small nested mount tree

Inside a disposable mount/user namespace, construct a root with at least one nested submount. Use independent mount-flag inspection through `/proc/self/mountinfo` and/or a small `statvfs()` helper.

For each operation, compare baseline and candidate:

```text
--bind     => destination + nested submount gain nosuid,nodev
--dev-bind => destination + nested submount gain nosuid while device access policy is preserved
--ro-bind  => destination + nested submount gain nosuid,nodev,ro
```

Also seed unrelated flags on at least one nested mount and verify the candidate preserves them.

### 3. Forced old-kernel control

Inject or wrap the `mount_setattr()` call so it returns `-1` with `errno=ENOSYS`, then prove the legacy path runs and produces the same final flags as baseline.

The negative control should also force `EINVAL` and prove that the candidate reports a real failure instead of silently treating it as an old-kernel condition.

### 4. Recursive failure atomicity control

Use the Linux selftest idea: keep a writable file descriptor open in a nested mount and request a recursive read-only transition. Confirm the syscall fails and inspect every mount in the fixture to verify the tested attributes remain unchanged.

This control demonstrates that the test can observe partial publication if it ever occurs.

### 5. Mount-table race discriminator

Reproduce the issue-650 family in a disposable namespace by repeatedly adding/removing a nested mount while launching recursive binds.

Compare:

- current userspace path;
- candidate syscall path;
- forced-`ENOSYS` legacy fallback.

The claim should remain bounded to the observed fixture and kernel. A stress run that happens to stay green is evidence, not proof that every mount race is impossible.

### 6. Non-security mode control

Exercise a deliberately induced legacy submount-remount failure with and without `--not-a-security-boundary` to preserve the existing fail-closed/fail-open distinction on the fallback path. The committed upstream smoke test currently proves only that the option parses.

## Results

### Demonstrated from Bubblewrap source/history

1. Every directory bind handled by `setup_op_bind_mount()` is recursive.
2. The current mount attribute contract is `nosuid` plus conditional `nodev` and conditional `ro`.
3. The current recursive flag application depends on a userspace `/proc/self/mountinfo` snapshot followed by individual remount syscalls.
4. Bubblewrap issue 650 records a real failure mode when a mount disappears between those phases.
5. Bubblewrap issue 754 is an open maintainer-authored `help wanted` direction for `mount_setattr()` with an older-kernel fallback.
6. A maintainer explicitly preferred issue 754 over the much larger userspace optimization in PR 629 because the latter was difficult to review with high confidence.
7. The current `--not-a-security-boundary` test exercises argument acceptance, not the actual ignored-remount-failure branch.

### Demonstrated from Linux source/selftests

1. `mount_setattr()` and the required initial mount attributes exist from Linux 5.12.
2. `AT_RECURSIVE` applies mount attribute changes across the mount tree.
3. `attr_set` can add `RDONLY`, `NOSUID`, and `NODEV` while `attr_clr == 0` leaves other mount attributes untouched by request.
4. The kernel performs recursive preparation before commit.
5. The Linux selftest verifies a failed recursive read-only transition with an open writer leaves the checked mount flags unchanged.
6. The Linux selftest uses `ENOSYS` specifically as the unsupported-syscall discriminator.
7. `EINVAL` has multiple ordinary error meanings for `mount_setattr()` and therefore cannot safely serve as a generic compatibility fallback signal.
8. The kernel selftest includes old-header fallback definitions and a raw-syscall wrapper, establishing a concrete portability pattern.

### Runtime results

None yet. No Bubblewrap candidate was compiled or executed during this pass, and no performance number is claimed here.

## Interpretation

The source evidence is strong enough to promote this from broad reconnaissance into a focused implementation experiment.

The smallest likely repair boundary is Bubblewrap's recursive bind attribute-application phase, not argument parsing, mount graph modeling, or the complete new mount API family. The initial `MS_BIND | MS_REC` operation can remain. On supported kernels, the subsequent per-mount attribute walk is the part `mount_setattr(AT_RECURSIVE)` can replace.

This has two attractive properties at once:

- fewer userspace operations and no userspace mount-table snapshot for applying the recursive flags;
- all-tree preparation before attribute commit for the failure class exercised by the Linux selftest.

The most important correction to the issue sketch is fallback classification. An implementation that falls back on any `EINVAL` risks converting a genuine candidate error into legacy behavior. The first candidate should be deliberately boring: feature absence through `ENOSYS`, success through the new path, all other errors surfaced until evidence establishes a narrower exception.

## Evidence boundary

This record establishes source and history relationships. It does not establish Bubblewrap runtime compatibility yet.

Untested here:

- compilation against Bubblewrap's supported compiler/libc/header matrix;
- runtime behavior on Linux 5.12 and later kernels;
- runtime behavior with old headers and a new kernel;
- all architectures Bubblewrap supports;
- set of errors returned by real recursive bind trees under user namespaces;
- real issue-650 race frequency before/after a candidate;
- performance improvement;
- interaction with every mount propagation mode;
- exact `EACCES` behavior equivalence between the legacy per-path remount loop and the kernel tree operation;
- `--not-a-security-boundary` behavior on the new syscall path;
- full Bubblewrap test suite.

One adjacent semantic question deserves an explicit probe: the legacy loop ignores `EACCES` while walking individual submount paths. `mount_setattr()` traverses the mount tree inside the kernel after resolving the target mount. The runtime fixture should include an access-restricted nested path and compare final attributes and exit status rather than assuming the two mechanisms expose identical errno behavior.

Reopen or widen this question if:

- the syscall path cannot reproduce current `--dev-bind` behavior;
- a required existing mount property is altered;
- an old supported kernel/header combination cannot use a clean `ENOSYS` fallback;
- a recursive failure partially changes the tested tree on a supported kernel;
- non-security mode needs a broader, separately justified error policy;
- the target project's supported architecture matrix makes a local syscall-number compatibility layer unreasonable.

## Next step

Create an owned Bubblewrap fork or disposable executable checkout and implement one small candidate:

1. minimal `mount_setattr()` compatibility wrapper;
2. recursive attribute-set helper for `NOSUID`, conditional `NODEV`, conditional `RDONLY`;
3. `ENOSYS` legacy fallback;
4. focused nested-mount differential test;
5. forced `ENOSYS` and `EINVAL` controls;
6. open-writer recursive failure control;
7. existing test suite and clean rerun.

If that passes, measure the issue-650 race fixture and a many-bind workload, then inspect the complete diff for compatibility drift. Keep broader new-mount-API work separate.

## Authority

No upstream issue, pull request, email, patch submission, comment, review, or other external interaction was authorized or made during this investigation.

All third-party activity in this pass was read-only source/history research. The internal coordination carrier is `teamleaderleo/linux-fieldwork#562`.