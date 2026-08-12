# fuse-overlayfs Rust rewrite silently drops ACL inheritance failures

Date: 2026-08-12

## TL;DR

The current Rust implementation treats POSIX default-ACL inheritance as best-effort even when a parent ACL is present and the target refuses it.

At exact reviewed head `containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117`, `OverlayInner::inherit_acl()`:

- returns `()` rather than an error;
- reads `system.posix_acl_default` into one fixed 4096-byte buffer;
- returns silently on **any** parent getxattr error;
- ignores the final target `fsetxattr()` result.

Child-creation callers invoke `inherit_acl()` and continue to rename/register/publish the new object.

The pre-Rust C implementation had a different error contract:

- it read the default ACL with `safe_read_xattr(..., 4096)`, whose buffer grows/retries on `ERANGE`;
- parent `ENODATA`/`ENOTSUP` meant “no ACL” and returned success;
- other parent read errors were returned;
- when an ACL existed, the helper returned the destination `fsetxattr()`/`setxattr()` result;
- callers checked that result and aborted creation/copy-up on failure.

A local cross-filesystem control demonstrates a realistic apply failure: an ext4 `/tmp` directory accepted a default ACL, while a `/dev/shm` tmpfs target returned `ENOTSUP` when the same ACL xattr was applied. Current Rust's helper would discard that error and continue creation without the inherited ACL.

This is a Rust rewrite regression affecting access-control metadata, not merely a buffer-size corner case.

No upstream contact is authorized or has been made.

## Exact current source

Current helper:

```rust
fn inherit_acl(&self, parent_id: NodeId, target_fd: RawFd, config: &OverlayConfig) {
    if config.noacl {
        return;
    }
    ...
    const ACL_XATTR: &str = "system.posix_acl_default";
    let mut buf = vec![0u8; 4096];
    let len = match layer.ds.getxattr(&parent_path, ACL_XATTR, &mut buf) {
        Ok(n) => n,
        Err(_) => return,
    };
    if len == 0 {
        return;
    }
    let _ = crate::sys::xattr::fsetxattr(target_fd, ACL_XATTR, &buf[..len], 0);
}
```

The two silent boundaries are distinct:

1. read failures are all treated as “no ACL”;
2. apply failure is ignored even after a real ACL was successfully read.

## Current call-site consequence

The helper is called from multiple object-creation paths, including workdir-backed regular/directory creation and direct file creation. Callers do not receive a status from it and continue with rename/stat/register logic.

Thus the result visible through the mounted filesystem can be a successfully created child whose expected inherited default ACL was never applied.

## Pre-Rust C control

Old helper:

```c
s = safe_read_xattr(&v, dfd, ACL_XATTR, 4096);
if (s < 0) {
    if (errno == ENODATA || errno == ENOTSUP)
        return 0;
    return -1;
}
if (targetfd >= 0)
    return fsetxattr(targetfd, ACL_XATTR, v, s, 0);
return setxattr(path, ACL_XATTR, v, s, 0);
```

Old callers checked:

```c
ret = inherit_acl(...);
if (ret < 0)
    return ret; /* or goto cleanup */
```

So target ACL application failure was not historically declared best-effort.

### Dynamic ACL read control

`safe_read_xattr()` starts from the supplied 4096-byte size, but on `ERANGE` grows the buffer and retries. The Rust rewrite replaced that retrying helper with one fixed allocation.

Therefore an ACL too large for 4096 bytes is also silently treated as missing by current Rust, even on a filesystem that supports larger xattrs.

## Local cross-layer reproduction

Tracked `repro.py` constructs a valid small POSIX default ACL xattr.

Observed locally:

```text
lower default ACL read: OK bytes= 36
upper ACL apply errno: 95 Operation not supported
current Rust inherit_acl outcome: success (error discarded)
pre-Rust/candidate outcome: error propagated; child not published
```

The lower parent lives on ext4 under `/tmp`, while the target file lives on tmpfs under `/dev/shm`. This establishes an ordinary Linux case where a parent ACL exists but target application can fail.

It is not a full mounted fuse-overlayfs integration; it isolates the exact xattr operation pair used by the helper.

## History boundary

Rust rewrite commit:

`71269043450580a03751a72fc8e0b2b827f865b3` — `fuse-overlayfs: rewrite in Rust`

The Rust ACL helper's best-effort return contract and fixed buffer are part of the rewrite-era implementation. The previous C implementation had the error-returning/dynamic-read behavior described above.

## Candidate design

See `CANDIDATE.md`.

Key boundary:

- parent `ENODATA` / `ENOTSUP` remain nonfatal “no inherited ACL” controls;
- other parent read errors propagate;
- ACL read grows/retries on ERANGE;
- once a parent ACL exists, target apply errors propagate;
- creation/copy-up cleans up the new temp/object instead of publishing it without the ACL.

This reproduces the old semantic distinction rather than making every ACL-related condition fatal.

## Test design

Deterministic fake-xattr tests should cover:

- parent missing ACL -> success;
- parent ACL unsupported -> success;
- parent read EIO/EACCES -> failure;
- parent first read ERANGE then success -> inherited ACL applied;
- target apply ENOTSUP/EIO -> creation fails and cleans up;
- `noacl` -> explicit success without ACL operations.

A cross-filesystem integration can mirror the local ext4-parent/tmpfs-target control if the mount arrangement supports those layers.

## Duplicate search

Open and closed upstream issue searches for ACL inheritance/ENOTSUP/Rust silent failure returned no matching report during this pass.

## Evidence boundary

Demonstrated:

- exact current helper suppresses all read errors and final apply errors;
- current buffer is fixed at 4096;
- current creation callers cannot observe ACL failure;
- old C helper distinguished absent/unsupported parent ACL from real errors;
- old target setxattr error propagated;
- old read helper grew on ERANGE;
- local ext4->tmpfs control produces a real target ENOTSUP after successful ACL read;
- no matching upstream issue was found.

Not yet demonstrated:

- exact-head mounted creation against mixed backing filesystem capability;
- practical occurrence of default ACL xattrs larger than 4096 on a currently targeted backing filesystem;
- a compile-tested API change in the Rust tree.

## Cleanup

The local control created one temporary ext4 directory and one tmpfs file, set/removed the default ACL on the directory, and removed both objects. No mount, namespace, device, or persistent state remained.

## Current disposition

State: `EXECUTING`

Next safe actions:

1. fake-xattr/owned-CI fault tests if available;
2. audit inherited ACL mode/umask reconciliation for semantic drift from the C helper;
3. keep this ACL-specific error contract separate from the broader copy-up metadata publication issue #621.

External-contact state: no upstream interaction authorized or made.
