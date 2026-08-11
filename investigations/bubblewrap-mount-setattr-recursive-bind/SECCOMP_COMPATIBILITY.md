# Bubblewrap `mount_setattr()` syscall-mediation compatibility

Date: 2026-08-11

Internal tracking: `teamleaderleo/linux-fieldwork#562`

## TL;DR

A new compatibility boundary showed up while preparing the Bubblewrap `mount_setattr(AT_RECURSIVE)` candidate: an outer seccomp policy can deny `mount_setattr()` while still allowing the legacy `mount(2)` remount path that Bubblewrap uses today.

A disposable Linux 6.18.35 x86_64 user+mount namespace reproduced that boundary directly. A seccomp filter was installed that returned `EPERM` only for `mount_setattr`. The recursive `mount_setattr()` call then failed with `EPERM`, while legacy `mount(2)` remounts in the same filtered process succeeded for the root and nested mount and preserved the fixture's pre-existing nested `noexec` flag. An injected `ENOSYS` control behaved the same way.

The stronger result is a safe discriminator that avoids treating `EPERM` from the *real* attribute request as an automatic fallback condition.

Since Linux 5.12, the `mount_setattr()` syscall validates `usize` before its mount-permission check. The deliberately invalid call

```c
syscall(__NR_mount_setattr, -1, NULL, 0, NULL, 0)
```

therefore returns `EINVAL` from the kernel implementation before `may_mount()` is consulted. That ordering is present both in Linux v5.12 and in the current kernel source reviewed here.

The local runtime control observed:

```text
unfiltered:          EINVAL
seccomp -> EPERM:    EPERM
seccomp -> ENOSYS:   ENOSYS
```

This suggests a smaller compatibility design for the first Bubblewrap candidate:

1. use a side-effect-free zero-size support probe before selecting the new path;
2. `EINVAL` from that probe means the syscall reached the Linux handler, so the real fd-based `mount_setattr()` path may be attempted;
3. any result showing that the syscall did not reach the expected handler contract can keep the established legacy remount path;
4. once the real `mount_setattr()` operation is attempted, preserve the existing rule: success uses the new path, and a real operation error remains an error rather than being silently converted into fallback;
5. `BIND_FAIL_OPEN` remains on the legacy per-submount path in the first candidate.

This separates **syscall availability/mediation** from **operation failure**. It avoids a blanket `EPERM` fallback on the real mount operation, while retaining compatibility with execution environments that block the newer syscall but permit the established `mount(2)` path.

## Explain like I'm five

Bubblewrap has an old way and a new proposed way to put safety flags on a tree of mounts.

A container supervisor can allow the old Linux syscall while blocking the newer one. If Bubblewrap only tries the new syscall and treats the denial as a fatal mount error, it can fail in an environment where the current Bubblewrap implementation works.

The useful trick is to ask Linux a harmless deliberately-invalid question first. Real Linux answers that question with `EINVAL`. A syscall filter can answer before Linux sees it, which gives a different result such as `EPERM`. Bubblewrap can use that distinction to decide whether the new syscall is reachable before it performs the real mount operation.

## Why care

The `mount_setattr()` candidate is primarily an internal replacement for Bubblewrap's recursive mount-attribute application. Its intended compatibility property is that older or constrained environments retain the established legacy path.

The previously recorded `ENOSYS` fallback covers kernels or builds where the syscall is unavailable. It does not by itself cover an execution environment where the kernel supports `mount_setattr()` but an outer syscall policy denies it.

That is particularly relevant to Bubblewrap because it is often itself used as a sandbox building block and can run under another containment layer. This pass does **not** claim that any particular current container runtime default profile blocks `mount_setattr()`. It demonstrates the mechanism and a discriminator in a controlled fixture.

## Source identities

### Bubblewrap

- Project: `containers/bubblewrap`
- Exact source head reviewed: `2f55bae38468d0c50cf5df87b1e481e882b63acb`
- Relevant implementation: `bind-mount.c`
- Existing tracked record: `investigations/bubblewrap-mount-setattr-recursive-bind/README.md`
- Existing runtime record: `investigations/bubblewrap-mount-setattr-recursive-bind/RUNTIME_RESULTS.md`

The first candidate remains bounded to the normal fail-closed recursive-bind path. `BIND_FAIL_OPEN` stays on the legacy loop initially because it has per-submount warning-and-continue semantics that a single recursive syscall does not reproduce.

### Linux

Current source reviewed:

- Project: `torvalds/linux`
- Exact commit: `d58772d8520c7ef247c4b95c9bd76d3a25da9ff5`
- File: `fs/namespace.c`

Introduction-floor cross-check:

- Tag: `v5.12`
- File: `fs/namespace.c`

At v5.12 the syscall performs these checks in order:

```text
validate flags
validate usize <= PAGE_SIZE
validate usize >= MOUNT_ATTR_SIZE_VER0  -> EINVAL if too small
may_mount()                              -> EPERM if denied
copy userspace attribute structure
...
```

The current implementation retains the same important ordering through `wants_mount_setattr()`: a zero `usize` returns `EINVAL` before `may_mount()`.

That gives the zero-size call a useful property for this candidate: kernel-level mount privilege is not required to observe the expected `EINVAL` support signature.

### util-linux precedent

- Project: `util-linux/util-linux`
- Exact commit reviewed: `4aa18ba04cedfb4defc738b59182579c25a96088`
- File: `libmount/src/hook_mount.c`

libmount already contains a `mount_setattr_is_supported()` helper using the same general probe form:

```c
mount_setattr(-1, NULL, 0, NULL, 0)
```

Its current support check treats `ENOSYS` as unsupported. Its real `mount_setattr()` flag application returns operation errors rather than treating generic errors as old-kernel fallback signals.

The Bubblewrap-specific extension proposed by this pass is to use the known `EINVAL` handler signature to distinguish a reachable syscall from an outer layer that intercepts the probe with another errno.

## Environment

- Kernel: `Linux 6.18.35 x86_64`
- Compiler: Debian GCC `14.2.0`
- Initial UID: `0`
- Outer effective capability set: no host `CAP_SYS_ADMIN`
- Outer seccomp mode before the test: `Seccomp: 0`, zero filters
- Namespace fixture: `unshare -Urnm`
- Mount cleanup: namespace exit

The mount fixture used namespace-local mount privilege. No host mount state was retained.

## Probe 1 — seccomp denial versus legacy remount

### Fixture

Each case entered a fresh user+mount namespace, made `/` recursively private, and created:

```text
source tmpfs
└── sub/    separate tmpfs with noexec

source tree --rbind--> destination tree
```

The probe process then installed a seccomp BPF filter that affected only `__NR_mount_setattr` and returned a selected errno. All other syscalls, including `mount(2)`, were allowed.

The new-path attempt used an `O_PATH` fd for the destination and:

```c
struct mount_attr attr = {0};
attr.attr_set = MOUNT_ATTR_NOSUID | MOUNT_ATTR_NODEV;

syscall(__NR_mount_setattr,
        fd,
        "",
        AT_EMPTY_PATH | AT_RECURSIVE,
        &attr,
        sizeof(attr));
```

After the injected failure, the same process used legacy `mount(2)` bind-remount operations for the root and nested mount, adding `nosuid,nodev` while retaining the nested `noexec` control.

### Injected `EPERM`

Observed:

```text
before-root=rw,relatime
before-sub=rw,noexec,relatime
mount_setattr_rc=-1 errno=1 (Operation not permitted)
legacy_root_rc=0 errno=0 (Success)
legacy_sub_rc=0 errno=0 (Success)
after-root=rw,nosuid,nodev,relatime
after-sub=rw,nosuid,nodev,noexec,relatime
```

### Injected `ENOSYS`

Observed:

```text
before-root=rw,relatime
before-sub=rw,noexec,relatime
mount_setattr_rc=-1 errno=38 (Function not implemented)
legacy_root_rc=0 errno=0 (Success)
legacy_sub_rc=0 errno=0 (Success)
after-root=rw,nosuid,nodev,relatime
after-sub=rw,nosuid,nodev,noexec,relatime
```

### Interpretation

This proves the compatibility shape in the tested environment: syscall mediation can make the new primitive unavailable while leaving Bubblewrap's established old primitive usable.

It does **not** justify falling back on `EPERM` from the real `mount_setattr()` operation. The kernel can use `EPERM` for real mount-attribute failures, so that would conflate two classes of error.

## Probe 2 — side-effect-free support signature

A second helper called only:

```c
syscall(__NR_mount_setattr, -1, NULL, 0, NULL, 0)
```

and reported the result before and after installing the same single-syscall seccomp filter.

Observed:

```text
unfiltered rc=-1 errno=22 (Invalid argument)

unfiltered rc=-1 errno=22 (Invalid argument)
filtered   rc=-1 errno=1  (Operation not permitted)

unfiltered rc=-1 errno=22 (Invalid argument)
filtered   rc=-1 errno=38 (Function not implemented)
```

The unfiltered process lacked host `CAP_SYS_ADMIN`, yet still received `EINVAL`. That matches the Linux source ordering: the too-small structure size is rejected before mount privilege is checked.

## Candidate implication

The previous candidate sketch was:

```text
real mount_setattr succeeds -> new path
real mount_setattr ENOSYS    -> legacy path
other real errno             -> fail closed
BIND_FAIL_OPEN               -> legacy path
```

This pass suggests moving availability classification ahead of the real operation:

```text
BIND_FAIL_OPEN -> legacy path

support probe:
    expected EINVAL -> syscall handler is reachable; try new path
    unavailable/intercepted result -> legacy path

real operation:
    success -> new path
    any error -> fail closed
```

The exact accepted set for the support probe should stay explicit in source and tests. The strongest source contract is that `EINVAL` is the expected Linux-handler signature for the zero-size probe from v5.12 through the current reviewed kernel. `ENOSYS` is the conventional syscall-absence result. An outer seccomp policy can replace either with its configured action before the handler runs.

A conservative first implementation could cache whether the zero-size probe returns exactly `EINVAL`; only that result enables the new path. Every other result retains the established legacy path. That makes unknown mediation or future ABI surprises a performance fallback rather than a mount-policy relaxation.

This is an implementation recommendation, not yet a compiled Bubblewrap candidate.

## Negative controls and boundaries

Demonstrated:

- zero-size support probe returns `EINVAL` on the tested Linux 6.18.35 kernel even without host `CAP_SYS_ADMIN`;
- a seccomp filter targeting only `mount_setattr` can replace that result with `EPERM` or `ENOSYS`;
- under the same filter, legacy `mount(2)` remounts remain usable;
- the tested legacy remount control preserves a nested `noexec` flag while adding `nosuid,nodev`;
- Linux v5.12 and current Linux source both place the zero-size `EINVAL` check before the mount-permission check;
- util-linux uses the same invalid-call shape as a `mount_setattr` support probe.

Not demonstrated:

- prevalence of `mount_setattr` blocking in any named container-runtime default profile;
- behavior under every seccomp action, seccomp user notification, ptrace-based syscall mediation, or non-Linux compatibility layer;
- a compiled Bubblewrap candidate using this discriminator;
- Bubblewrap full-suite behavior with the new path;
- end-to-end performance effect.

## Cleanup and rerun

Both mount cases used fresh disposable user+mount namespaces. Namespace exit owned the tmpfs, recursive bind, and remount cleanup. The support-signature helper created no mount state.

The `EPERM` and `ENOSYS` mount cases were run separately and produced the expected differential each time.

## Current disposition

- State: `EXECUTING`
- Exact Bubblewrap head: `2f55bae38468d0c50cf5df87b1e481e882b63acb`
- New finding: distinguish syscall mediation with a zero-size preflight instead of blanket fallback on errors from the real operation
- Candidate policy: `BIND_FAIL_OPEN` legacy; preflight `EINVAL` enables new path; other preflight results retain legacy; once new path is selected, real operation errors remain fail-closed
- Evidence boundary: Linux source + local syscall/namespace/seccomp primitive; no Bubblewrap source candidate or full suite in this pass
- Cleanup state: complete through namespace exit
- Next safe action: implement the smallest preflight-gated fd-based candidate on the owned Bubblewrap fork and run its full CI plus focused fallback controls
- External-contact state: no upstream interaction authorized or made
