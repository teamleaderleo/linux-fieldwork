# fuse-overlayfs Rust rewrite loses special-file stat overrides

Date: 2026-08-12

## TL;DR

The current Rust implementation contains the parser needed to restore logical uid/gid/mode/type for devices and other special files, but production stat code makes those branches unreachable.

At exact reviewed head `containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117`:

- `mknod()` creates the workdir special node with `mode | 0755` unconditionally;
- creation does not write a stat-override xattr for the logical requested/masked mode;
- `override_mode()` immediately returns for every object that is not a regular file or directory;
- yet `parse_and_apply_override()` explicitly supports `symlink`, `pipe`, `socket`, `blockMAJ:MIN`, and `charMAJ:MIN`, with unit tests for block/char/symlink types.

The project fixed exactly this class in 2023: commit `2d8613e7f5f85afb9077f2d9e3eadb48249fedf1` (“honor mode for devices with xattr_permissions”) separated permissive backing mode from the caller-masked logical mode. The pre-Rust C mknod used conditional backing widening and then passed the masked logical mode into `do_fchownat`, whose stat-override path stored logical metadata.

The May 2026 Rust rewrite reintroduced the bug in two places: it broadens mknod without recreating the logical override metadata, and its stat reader rejects special files before the extended parser can run.

No upstream contact is authorized or has been made.

## Current mknod creation path

Current Rust:

```rust
fn mknod(... mode: u32, _umask: u32, ...) {
    ...
    mknodat(workdir_fd, ..., mode | 0o755, ...)?;
    ...
    let _ = fchownat(...);
    ...
    renameat(...)?;
}
```

There is no write of `user.containers.override_stat`, `security.fuseoverlayfs.override_stat`, or the corresponding user override during this creation path.

A source-wide search of override-xattr `fsetxattr` calls found the logical uid/gid/mode override write in `setattr()`, but not in create/mkdir/mknod.

## Current stat reachability defect

Production `override_mode()` says:

```rust
let file_type = st.st_mode & libc::S_IFMT;
if file_type != libc::S_IFDIR && file_type != libc::S_IFREG {
    return Ok(());
}
```

It therefore refuses to read any override xattr for:

- FIFO;
- socket;
- character device;
- block device;
- symlink.

Immediately below, however, `parse_and_apply_override()` understands the extended fourth field:

```text
...:symlink
...:pipe
...:socket
...:blockMAJ:MIN
...:charMAJ:MIN
```

and updates both `st_mode` and `st_rdev` for device types.

The current unit tests call `parse_and_apply_override()` directly for block and char devices, so they do not exercise the production early-return that makes those parser branches unreachable.

This is a valuable test-design lesson for the carrier: regression coverage must call `override_mode()` or a mounted getattr path, not just the parser.

## Historical fix boundary

Commit:

`2d8613e7f5f85afb9077f2d9e3eadb48249fedf1` — `fuse-overlayfs: honor mode for devices with xattr_permissions`

The diff explicitly introduced:

```c
mode_t backing_file_mode = mode | (lo->xattr_permissions ? 0755 : 0);
...
mode = mode & ~ctx->umask;
...
mknodat(..., backing_file_mode, ...);
```

The key is that `backing_file_mode` and logical `mode` are separate values. After creation the C path calls:

```c
do_fchownat(..., uid, gid, mode, ...)
```

so stat-override mode can store/report the logical masked permissions while the backing special file remains usable in the unprivileged environment.

NEWS for v1.14 records both “honor umask with xattr_permissions” and “honor mode for devices with xattr_permissions.”

## Rust rewrite boundary

The initial Rust rewrite `71269043450580a03751a72fc8e0b2b827f865b3` already contains:

- `_umask` ignored by mknod;
- broad special-file creation;
- `override_mode()` early return for non-regular/non-directory objects;
- extended type parsing/tests below that unreachable production gate.

Thus the rewrite is the exact demonstrated regression boundary.

## Reduced discriminator

Tracked `repro.py` models the stat gate:

```text
backing FIFO mode: 0o10755
current getattr after override xattr 0:0:600:pipe: 0o10755
candidate/old logical mode: 0o10600
```

It also shows the default `xattr_permissions=0` mknod widening defect:

```text
requested FIFO 0600
current backing: FIFO 0755
old/default candidate: FIFO 0600
```

The model is intentionally about mode/override semantics; no privileged device creation is required.

## Candidate design

See `CANDIDATE.md`.

A complete repair needs both halves:

1. creation stores the caller-masked logical override metadata when stat override is active, using the extended type/rdev form;
2. `override_mode()` reads and applies overrides for special files instead of returning before the parser.

For default `xattr_permissions=0`, no override metadata is needed and backing mode should not be widened.

## Duplicate/test search

Open and closed upstream issue searches for device/mknod/xattr_permissions/Rust mode regressions returned no matching report in this pass.

Current tests include direct parser tests for block/char override strings, but no production-wrapper/mounted test showing a special-file override xattr actually changes getattr output.

## Evidence boundary

Demonstrated:

- exact current mknod unconditionally broadens backing mode;
- current creation does not write logical stat-override metadata;
- current production stat wrapper rejects every special file before parsing an override;
- current parser explicitly supports special-file extended types, proving the intended representation exists;
- the project shipped a 2023 fix specifically separating backing vs logical device mode under xattr_permissions;
- the C path passed caller-masked logical mode into the stat-override ownership helper;
- the broken creation/stat behavior is present in the Rust rewrite introduction;
- no matching upstream issue was found.

Not yet demonstrated:

- exact-head rootless mounted mknod integration under `xattr_permissions`;
- a compile-tested Rust implementation of create-time extended override serialization;
- full ownership behavior for every user/privileged/containers stat-override mode.

## Cleanup

The reduced model creates no filesystem/device state.

## Current disposition

State: `EXECUTING`

Next safe actions:

1. add a production-wrapper unit test around `override_mode()` with FIFO/char/block xattrs in owned CI;
2. reconstruct the C `do_fchown/do_fchownat` write semantics for regular/directory creation too;
3. audit whether copy-up of existing stat-override special files preserves the extended xattr and logical type/rdev.

External-contact state: no upstream interaction authorized or made.
