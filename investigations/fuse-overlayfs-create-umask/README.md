# fuse-overlayfs Rust rewrite ignores request umask under FUSE_DONT_MASK

Date: 2026-08-12

## TL;DR

The current Rust implementation negotiates `FUSE_DONT_MASK` but ignores the per-request `umask` argument in its three mode-bearing creation callbacks: `create`, `mkdir`, and `mknod`.

At exact reviewed head `containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117`, all three signatures name the argument `_umask` and pass the unmasked request mode to backing creation. Linux and fuser define `FUSE_DONT_MASK` as “don't apply umask to file mode on create operations,” meaning the kernel intentionally leaves that responsibility to the filesystem.

The pre-Rust C implementation negotiated the same capability and explicitly applied `ctx->umask` before creation (`mode & ~ctx->umask`). The Rust rewrite already ignores `_umask`, making this an exact rewrite regression.

This can grant permission bits that the requesting process's umask was supposed to remove whenever the long-lived daemon's own process umask is less restrictive. For example, requested mode `0666`, caller umask `077`, daemon umask `022` can produce backing mode `0644` in current Rust instead of the caller-expected `0600`.

`mknod` has an additional related drift: current Rust unconditionally ORs `0755` into the temporary special-node mode. The C code only widened backing mode when `xattr_permissions` was enabled, and passed the caller-masked logical mode into its ownership/stat-override helper. The tracked candidate restores the default `xattr_permissions=0` backing-mode boundary and records stat-override creation semantics as an adjacent follow-up.

No upstream contact is authorized or has been made.

## FUSE contract

Current Rust `init()` requests:

```rust
InitFlags::FUSE_DONT_MASK | ...
```

Linux UAPI documents:

```text
FUSE_DONT_MASK: don't apply umask to file mode on create operations
```

fuser's `InitFlags` carries the same definition.

Thus the `umask` argument passed to the Filesystem callbacks is not redundant metadata: with DONT_MASK negotiated, userspace is responsible for honoring it.

## Current Rust creation paths

Current callbacks have:

```rust
fn mknod(..., mode: u32, _umask: u32, ...)
fn mkdir(..., mode: u32, _umask: u32, ...)
fn create(..., mode: u32, _umask: u32, ...)
```

and no later use of the request umask.

### Regular create

`create()` passes `mode` directly into the upper-layer `openat()` or workdir creation path.

### mkdir

`mkdir()` passes `mode` directly to `mkdirat()`.

### mknod

`mknod()` currently passes:

```rust
mode | 0o755
```

to `mknodat()` regardless of the `xattr_permissions` configuration.

This means the mknod default path has both request-umask loss and an additional backing-mode widening.

## Pre-Rust C control

The C implementation negotiated the same DONT_MASK capability:

```c
conn->want |= FUSE_CAP_DONT_MASK | ...;
```

and applied the request context umask.

Regular creation used:

```c
direct_create_file(..., mode & ~ctx->umask);
```

Directory creation used:

```c
create_directory(..., mode & ~ctx->umask, ...);
```

mknod explicitly did:

```c
mode = mode & ~ctx->umask;
...
do_fchownat(..., mode, ...);
```

The C mknod backing widening was conditional:

```c
mode_t backing_file_mode = mode | (lo->xattr_permissions ? 0755 : 0);
```

Current Rust changed that to unconditional `mode | 0755`.

## Rewrite introduction boundary

The initial Rust rewrite `71269043450580a03751a72fc8e0b2b827f865b3` already declares `_umask` and ignores it in the creation callbacks. The rewrite therefore forms the exact demonstrated regression boundary.

## Reduced discriminator

Tracked `repro.py` models two independent umasks:

- request/caller umask carried by the FUSE request;
- fixed process umask inherited by the long-running fuse-overlayfs daemon.

Representative result:

```text
requested=0666 caller_umask=077 daemon_umask=022 current=0644 old/candidate=0600
requested=0777 caller_umask=077 daemon_umask=022 current=0755 old/candidate=0700
requested=0666 caller_umask=027 daemon_umask=022 current=0644 old/candidate=0640
requested=0666 caller_umask=022 daemon_umask=022 current=0644 old/candidate=0644
```

The final control explains why the bug can hide in common testing: if daemon and request umasks happen to match, output looks correct despite the request field being ignored.

The strongest impact is when another process using the mounted filesystem has a stricter umask than the daemon inherited at mount time.

## Candidate

Tracked candidate: `candidate.patch`.

It first computes:

```rust
let mode = mode & !umask;
```

in create/mkdir/mknod.

For mknod it also restores the C default-path distinction:

```rust
let backing_mode = if self.config.xattr_permissions != 0 {
    mode | 0o755
} else {
    mode
};
```

The `xattr_permissions != 0` path needs a separate audit of logical stat-override creation metadata, because the old C code paired widened backing permissions with `do_fchownat(..., logical_mode)` semantics that the Rust rewrite did not reproduce directly. This first candidate is strongest for the default `xattr_permissions=0` behavior.

## Tests

A mounted test should hold the daemon umask constant and issue creates from child processes with different umasks.

Required cases:

- daemon `022`, caller `077`, regular create 0666 -> 0600;
- daemon `022`, caller `027`, regular create 0666 -> 0640;
- mkdir 0777 with caller `077` -> 0700;
- FIFO/special mknod mode control when permitted;
- matching daemon/caller `022` control -> 0644 for create 0666;
- default ACL case to ensure the restored request mask remains compatible with the historical ACL inheritance behavior.

## Duplicate/test search

Open and closed upstream issue searches for `umask`, `DONT_MASK`, Rust, create and mkdir returned no matching report during this pass. Current test search did not surface a multi-client/request-umask regression test.

## Evidence boundary

Demonstrated:

- exact current init negotiates `FUSE_DONT_MASK`;
- Linux and fuser define it as disabling kernel-side create umask application;
- exact current create/mkdir/mknod ignore the supplied request umask;
- old C negotiated the same capability and explicitly masked creation modes with request `ctx->umask`;
- the ignored `_umask` behavior is present in the Rust rewrite introduction;
- reduced model shows permission broadening when caller umask is stricter than daemon umask;
- mknod current backing widening is unconditional whereas old C made it conditional on xattr_permissions;
- no matching upstream issue was found.

Not yet demonstrated:

- exact-head mounted multi-process integration because no Rust build/runtime is available locally;
- full logical-mode behavior under `xattr_permissions != 0` after the Rust rewrite;
- whether the daemon intentionally normalizes its own process umask elsewhere outside the repository (no such in-tree normalization was found).

## Cleanup

The reduced discriminator is pure arithmetic and creates no filesystem state.

## Current disposition

State: `EXECUTING`

Next safe actions:

1. mounted multi-umask integration in owned CI if available;
2. reconstruct `do_fchown/do_fchownat` stat-override semantics for Rust creation paths;
3. inspect other FUSE init capabilities where the rewrite opts into userspace responsibility but may not implement the corresponding per-request behavior.

External-contact state: no upstream interaction authorized or made.
