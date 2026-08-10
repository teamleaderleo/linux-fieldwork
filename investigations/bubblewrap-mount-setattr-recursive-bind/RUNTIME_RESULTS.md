# Runtime evidence — recursive bind attributes with `mount_setattr()`

Date: 2026-08-11

Internal tracking: `teamleaderleo/linux-fieldwork#562`

Bubblewrap source identity reviewed before execution: `containers/bubblewrap@2f55bae38468d0c50cf5df87b1e481e882b63acb`. A fresh commit search still reported that commit as current `main` before this runtime pass.

## TL;DR

A disposable Linux 6.18.35 x86_64 user+mount namespace executed the central kernel mechanism successfully.

`mount_setattr()` targeted through an `O_PATH` destination fd with `AT_EMPTY_PATH | AT_RECURSIVE` reproduced Bubblewrap's requested mount-attribute mapping on nested bind trees:

- `--bind` equivalent: add `nosuid,nodev`;
- `--dev-bind` equivalent: add `nosuid` and preserve the existing device policy;
- `--ro-bind` equivalent: add `ro,nosuid,nodev`.

A nested mount's pre-existing `noexec` survived all three operations. Individual file binds also worked, including a read-only destination while a writer remained open through the source mount.

The Linux recursive read-only failure control also reproduced: a writer opened through the destination bind itself made `mount_setattr()` return `EBUSY`, and the checked mount attributes remained unchanged across the full tree. A writer opened through the source mount did **not** cause this failure. That distinction is important for Bubblewrap: source-side host activity does not by itself reproduce the `EBUSY` control, while the sandbox destination is still in setup and has not been handed to the payload.

The old-header path can stay small. A compatibility wrapper compiled with Bubblewrap-style warnings both with and without `__NR_mount_setattr`. When the syscall number was deliberately hidden, the wrapper returned `ENOSYS`. This means the first candidate does not need an architecture-specific syscall-number table: builds whose headers do not know `mount_setattr` can simply retain the legacy path.

A synthetic microbenchmark that times only recursive attribute application showed a substantial syscall-fanout advantage. Median results were about 13.4 microseconds versus 101.5 microseconds at 100 nested submounts, and 20.3 microseconds versus 338.8 microseconds at 300 nested submounts, comparing one recursive `mount_setattr()` with one traditional bind-remount syscall per mount. This is a reduced microbenchmark, not a Bubblewrap startup benchmark.

## Environment

- Kernel: `Linux 6.18.35 x86_64`
- Compiler: Debian GCC `14.2.0`
- Initial process UID: `0`
- Initial container capability set: no `CAP_SYS_ADMIN`
- Namespace fixture: `unshare -Urnm`
- Inside the disposable user+mount namespace, namespace-local mount operations succeeded.
- `findmnt` supplied the independent mount-option observation.
- No Bubblewrap executable or candidate source tree was compiled in this pass. The connected GitHub source was read through the connector; the execution fixture directly exercised the Linux primitive that issue 754 proposes using.

## Retained fixtures

- `mount-setattr-probe.c` — small fd-based recursive attribute probe retained from the final successful experiment.
- `mount-attr-bench.c` — reduced timing helper for one recursive syscall versus one legacy remount syscall per known mount.

The retained probe was recompiled after it was written and reproduced the `ro,nosuid,nodev` result on a two-level tree while preserving nested `noexec`.

## 1. Namespace capability gate

The outer container does not hold host `CAP_SYS_ADMIN`, so an ordinary mount operation is not an authoritative test surface. A disposable user namespace supplies namespace-local privilege instead.

Observed setup:

```text
uid=0
kernel=Linux 6.18.35 x86_64 GNU/Linux
cc=cc (Debian 14.2.0-19) 14.2.0
max_userns=7851
```

Outer effective capabilities omitted `cap_sys_admin`.

The following succeeded:

```sh
unshare -Urnm sh -c '
  id -u
  grep CapEff /proc/self/status
  mount --make-rprivate /
'
```

Observed child UID was `0`, the effective capability bitmap was populated inside the new user namespace, and the mount-namespace operation succeeded.

This establishes that later mount results belong to a disposable namespace rather than to host mount state.

## 2. Three-mode recursive attribute differential

### Setup

For each mode, a fresh namespace created:

```text
source tmpfs
└── sub/    separate tmpfs, initially noexec
```

The source tree was recursively bind-mounted onto a fresh destination. The probe then applied attributes to the destination fd.

Core operation:

```c
fd = open(destination, O_PATH | O_CLOEXEC);
attr.attr_set = requested_bits;
syscall(__NR_mount_setattr,
        fd,
        "",
        AT_EMPTY_PATH | AT_RECURSIVE,
        &attr,
        sizeof(attr));
```

No attribute bits were placed in `attr_clr`.

### Observed results

```text
bind-before-root=rw,relatime
bind-before-sub=rw,noexec,relatime
bind-after-root=rw,nosuid,nodev,relatime
bind-after-sub=rw,nosuid,nodev,noexec,relatime

dev-bind-before-root=rw,relatime
dev-bind-before-sub=rw,noexec,relatime
dev-bind-after-root=rw,nosuid,relatime
dev-bind-after-sub=rw,nosuid,noexec,relatime

ro-bind-before-root=rw,relatime
ro-bind-before-sub=rw,noexec,relatime
ro-bind-after-root=ro,nosuid,nodev,relatime
ro-bind-after-sub=ro,nosuid,nodev,noexec,relatime
```

### Interpretation

On this kernel and fixture, `attr_set` has the needed additive behavior. The requested Bubblewrap bits are added recursively while an unrelated existing `noexec` bit survives on the nested mount.

This is a direct runtime discriminator for the core mapping proposed in the source-analysis README.

## 3. `O_PATH` + `AT_EMPTY_PATH` form

The first source sketch used a pathname. Bubblewrap already opens the destination with `O_PATH`, so a stronger candidate is to address the mount through that fd.

The fd form executed successfully:

```text
ok
fd-root=ro,nosuid,nodev,relatime
fd-sub=ro,nosuid,nodev,noexec,relatime
```

This avoids another destination pathname lookup after Bubblewrap has already opened the exact destination mountpoint.

### Candidate implication

The likely new-path call boundary is immediately after Bubblewrap successfully obtains `dest_fd`, before the legacy `/proc/self/mountinfo` parsing work.

If the new syscall succeeds, the new path does not need the mount-table snapshot for attribute application. If the syscall is unavailable, the existing code can continue into the legacy mountinfo/remount path.

This is a design inference. A real Bubblewrap candidate still needs source review and compilation.

## 4. Read-only writer discriminator

### Destination-side writer

A writable fd was opened through the recursive bind destination's nested mount before requesting recursive read-only.

Observed:

```text
atomic-before-root=rw,relatime
atomic-before-sub=rw,noexec,relatime
atomic-rc=16
atomic-error=mount_setattr: errno=16 (Device or resource busy)
atomic-after-root=rw,relatime
atomic-after-sub=rw,noexec,relatime
```

This reproduces the Linux selftest's all-or-no-change property for the checked attributes: the recursive request failed and neither checked mount received a partial attribute update.

### Source-side writer

The same experiment was repeated with the writable fd opened through the source mount instead of the new bind destination.

Observed:

```text
writer-side=source
rc=0
root=ro,nosuid,nodev,relatime
sub=ro,nosuid,nodev,noexec,relatime

writer-side=target
rc=16
mount_setattr: errno=16 (Device or resource busy)
root=rw,relatime
sub=rw,noexec,relatime
```

### Why this changes the interpretation

An early reading of the first `EBUSY` result suggested that ordinary host writers might make a `--ro-bind` replacement unusable. The source/target differential rejects that explanation in this fixture.

A writer through the source mount remains compatible with making the new bind view read-only. A writer through the target bind blocks the recursive read-only transition.

Bubblewrap performs bind setup before the sandbox payload runs, and its current code holds an `O_PATH` fd rather than a writable fd on the destination. The runtime evidence therefore supports keeping `EBUSY` as a useful negative control instead of treating it as a demonstrated ordinary-host regression.

Reopen this concern if a real Bubblewrap source walk finds a writable destination fd, an externally reachable `/newroot`, or another setup path that can create destination-side writers before attribute application.

## 5. Direct legacy remount comparison

To ensure the comparison was against the kernel operation Bubblewrap actually uses rather than behavior added by the `mount(8)` command, a small helper called `mount(2)` directly with the same family of flags:

```c
mount("none",
      target,
      NULL,
      MS_SILENT | MS_BIND | MS_REMOUNT | current_and_requested_flags,
      NULL);
```

With a source-side writer, direct legacy remounts of both root and nested destination mounts succeeded and produced:

```text
direct-root=ro,nosuid,nodev,relatime
direct-sub=ro,nosuid,nodev,noexec,relatime
```

The source-side writer also remained valid after the fd-based `mount_setattr()` file-bind test below. On the tested ownership boundary, the new syscall and traditional bind-remount agree on the important source-writer behavior.

## 6. Individual file bind control

A regular file was bind-mounted onto another regular file. A writer remained open through the source file while the destination attributes changed.

Observed:

```text
file-case=bind
rc=0
opts=rw,nosuid,nodev,relatime

file-case=ro-bind
rc=0
opts=ro,nosuid,nodev,relatime
dest-write=blocked
source-writer=still-open
```

This closes one adjacent context: the fd-based recursive flag form is not limited to directory mountpoints in this fixture.

## 7. Inherited mount controls

The synthetic tmpfs mounts are owned inside the test user namespace. Bubblewrap also consumes inherited host mounts, so `/usr` and `/dev` were sampled after entering a new user+mount namespace.

Observed successful cases included:

```text
inherited-usr-bind-root=rw,nosuid,nodev,...
inherited-usr-dev-bind-root=rw,nosuid,...
inherited-/usr-ro-bind=ro,nosuid,nodev,...
inherited-/dev-dev-bind-root=rw,nosuid,...
inherited-/dev-dev-bind-pts=rw,nosuid,noexec,...
```

The `/dev` source already carried `nodev` on this system; `dev-bind` correctly preserved that existing restriction instead of clearing it. This agrees with Bubblewrap's current OR-based policy: `--dev-bind` avoids adding `nodev`; it does not promise to remove `nodev` from a source that already has it.

One combined `/dev` cleanup loop hit an `umount` teardown error after the observation. The case was rerun in a one-case-per-namespace fixture, where namespace exit owned cleanup. Treat the first teardown error as fixture cleanup, not product behavior.

## 8. `EINVAL` negative control

`mount_setattr()` was directed at an ordinary directory below a mounted tree instead of at a mountpoint.

Path and fd variants both returned `EINVAL` (`22`). The fd result was:

```text
fd-nonmount-rc=22
mount_setattr(fd): errno=22 (Invalid argument)
```

This gives the planned fallback classifier a real negative control: a candidate that silently falls back on generic `EINVAL` would hide this genuine misuse.

The initial compatibility rule remains:

```text
success -> use new path
ENOSYS  -> run established legacy path
other   -> report the real failure
```

Any additional fallback errno needs its own demonstrated compatibility reason.

## 9. Old-header compilation boundary

A small compatibility wrapper was compiled under warning flags chosen to mirror Bubblewrap's strict Meson build, including missing-prototype, implicit-declaration, pointer, conversion, and return-type errors.

Two builds were made:

1. normal headers, where `__NR_mount_setattr` is available;
2. a forced-old-header simulation that `#undef`s `__NR_mount_setattr` after including the syscall header.

Observed outer-namespace calls:

```text
have-nr: errno=1 Operation not permitted
no-nr: errno=38 Function not implemented
```

The first result is expected outside the namespace because the container lacks host `CAP_SYS_ADMIN`. The second proves the compile-time fallback branch can return `ENOSYS` without any architecture-specific syscall-number table.

### Recommended compatibility design

Prefer the existing Bubblewrap pattern used by its raw-syscall helpers:

```text
#ifdef __NR_mount_setattr
    call syscall
#else
    errno = ENOSYS
    return -1
#endif
```

Supply small local compatibility definitions for the required attribute/`AT_*` constants when older headers lack them. A private four-`uint64_t` ABI struct is also possible if maintainers want to avoid depending on the header's `struct mount_attr` definition.

The cost of this simple choice is that a Bubblewrap binary compiled against headers older than `mount_setattr` will keep using the legacy path even if later run on a newer kernel. That is a performance opportunity cost, not a functional compatibility loss. Hardcoding syscall numbers across architectures should require a demonstrated need for that optimization.

## 10. Reduced performance probe

### What was measured

The benchmark creates the mount tree before timing starts. It then measures only one of these attribute-application operations:

- one `mount_setattr(fd, "", AT_EMPTY_PATH | AT_RECURSIVE, ...)` syscall; or
- one `mount(2)` bind-remount for the root plus one `mount(2)` bind-remount for every known nested mount.

The fixture uses sibling tmpfs submounts with the same initial options. It does **not** include Bubblewrap argument parsing, mountinfo loading/parsing, path setup, the initial recursive bind, process creation, or payload startup.

### Median observations

100 nested submounts, five runs each:

```text
mount_setattr ns: 14341, 13393, 13806, 12405, 10717
legacy ns:        102942, 100942, 103548, 101461, 98675
median:           13393 ns vs 101461 ns
ratio:            7.58x
```

300 nested submounts, three runs each:

```text
mount_setattr ns: 20295, 19984, 20471
legacy ns:        314297, 338760, 521938
median:           20295 ns vs 338760 ns
ratio:            16.69x
```

### Evidence limit

These numbers demonstrate the syscall-fanout difference on one kernel and synthetic tree. They do not establish a Bubblewrap end-to-end speedup and should not be quoted as one.

The legacy microbenchmark also omits Bubblewrap's `/proc/self/mountinfo` parse and lookup cost. That makes it useful as a narrow lower-bound comparison for per-mount syscall fanout, not a model of total legacy cost.

## Current interpretation

The runtime pass strengthened the original candidate instead of overturning it.

The best current implementation sketch is:

1. perform Bubblewrap's existing recursive bind;
2. open the destination as Bubblewrap already does;
3. for the normal fail-closed path, try the fd-based recursive `mount_setattr()` with the three exact requested attribute mappings;
4. on success, skip the legacy mountinfo/remount work for attribute application;
5. on `ENOSYS`, execute the established legacy path unchanged;
6. on other errors, fail closed and report the syscall error;
7. keep `BIND_FAIL_OPEN` on the legacy per-submount path in the first candidate, because its warning-and-continue semantics are intentionally more granular than one all-tree syscall failure.

The writer control adds one reopen condition: if a real Bubblewrap code path can create writable destination-side references before the attribute call, `MOUNT_ATTR_RDONLY` needs another design review. Source-side host writers did not reproduce that problem.

## Evidence boundary

Proven here:

- direct Linux runtime behavior on one Linux 6.18.35 x86_64 environment;
- nested directory and individual-file bind behavior;
- additive preservation of `noexec` in the tested tree;
- source-writer versus destination-writer distinction for recursive read-only;
- all-or-no-checked-attribute behavior on the reproduced `EBUSY` control;
- fd-based `AT_EMPTY_PATH | AT_RECURSIVE` behavior;
- selected inherited `/usr` and `/dev` cases inside a user namespace;
- a real `EINVAL` negative control;
- compilation of a no-syscall-number `ENOSYS` compatibility branch;
- reduced syscall-fanout timing.

Still open:

- a real Bubblewrap candidate build;
- Bubblewrap's full gcc sanitizer test suite and clang/CodeQL build;
- old-kernel runtime fallback on an actual pre-5.12 kernel;
- distribution/header matrix builds;
- stress reproduction of issue 650 against a real Bubblewrap candidate;
- behavior with `BIND_FAIL_OPEN` after candidate integration;
- less common mount topologies such as stacked/covered mounts, propagation changes during setup, and filesystems with unusual locked-flag behavior;
- end-to-end performance with many bind arguments.

## Next safe action

Prepare the smallest source candidate once an owned Bubblewrap fork or local source checkout is available:

- fd-based recursive syscall helper in or near `bind-mount.c`;
- `ENOSYS` legacy fallback;
- no generic `EINVAL` fallback;
- `BIND_FAIL_OPEN` stays legacy initially;
- focused nested directory + file tests;
- one injected/fake `ENOSYS` classifier test if the code can expose a small syscall seam without adding test-only product machinery;
- run the existing suite and inspect the complete diff before treating the candidate as reviewable.

Upstream contact remains unauthorized and has not occurred.
