# fuse-overlayfs Rust rewrite drops create-time stat overrides under xattr_permissions

Date: 2026-08-12

## TL;DR

The current Rust implementation activates a stat-override mode when `xattr_permissions` is configured, but its object-creation paths still call ordinary backing `fchown`/`fchownat`, discard those failures, and do not write the logical uid/gid/mode override xattr that the option exists to provide.

At exact reviewed head `containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117`:

- `layer::init_layers()` forces the upper `DirectAccess` into `StatOverrideMode::Privileged` or `Containers` when requested and no pre-existing marker was detected;
- regular `create()` performs `fchown(fd, host_uid, host_gid)` and ignores the result;
- `mkdir()` and `mknod()` perform `fchownat(...)` and ignore the result;
- symlink creation follows the same direct `fchownat` pattern;
- source-wide override-xattr writes in the Rust tree are found in `setattr()`, not these creation paths.

The pre-Rust C implementation did the opposite under `xattr_permissions`: `do_fchown`, `do_fchownat`, and `do_fchmod` routed logical uid/gid/mode changes through `write_permission_xattr()` instead of relying on physical ownership changes that can fail in a user namespace.

A local rootless control demonstrates the exact feature boundary: after dropping to uid/gid 65534, changing an owned file to uid/gid 12345 failed with `EPERM`, while writing `user.containers.override_stat=12345:12345:600` to the same file succeeded and round-tripped. Current Rust's create path would ignore the chown failure but never perform the successful logical-metadata write.

This is broader than the special-file device-mode regression tracked separately: regular files and directories can also be published with backing uid/gid/mode instead of the requested logical values.

No upstream contact is authorized or has been made.

## Current startup boundary

`layer::init_layers()` receives `xattr_permissions` and, for the upper layer, does:

```rust
if ds.stat_override_mode() == StatOverrideMode::None {
    match xattr_permissions {
        1 => ds.set_stat_override(StatOverrideMode::Privileged),
        2 => ds.set_stat_override(StatOverrideMode::Containers),
        _ => {}
    }
}
```

So the option does establish an in-memory override mode for the mounted session. The problem is not simply that the feature flag is ignored.

However `set_stat_override()` only changes an in-memory enum; it does not initialize an override marker xattr on the upper root. The old program had root-marker initialization behavior. That mount-to-mount persistence/detection difference is kept as an adjacent follow-up rather than required for this finding.

## Current regular create

After creating/opening the upper file, current Rust does:

```rust
let host_uid = inner.map_uid(req.uid(), &self.config);
let host_gid = inner.map_gid(req.gid(), &self.config);
let _ = crate::sys::fs::fchown(fd.as_raw_fd(), host_uid, host_gid);
inner.inherit_acl(...);
...
let st = layer.ds.fstat(...)?;
...
reply.created(... stat_to_attr(&st) ...);
```

There is no conditional override-xattr write in this path. If backing chown fails, the failure is discarded and the subsequent stat/report uses the physical backing owner unless an override somehow already exists.

## Current mkdir/mknod/symlink pattern

`mkdir()` and `mknod()` create a workdir object, compute mapped request uid/gid, then:

```rust
let _ = crate::sys::fs::fchownat(... host_uid, host_gid, ...);
```

and continue toward rename/publication.

Symlink creation likewise uses raw `fchownat` rather than a stat-override-aware helper.

This is especially significant because these workdir objects are new: there is no pre-existing child override xattr to rescue the logical metadata after the ignored chown failure.

## Pre-Rust C contract

The old code centralized this policy:

```c
static int do_fchown(... uid, gid, mode)
{
    if (lo->xattr_permissions)
        ret = write_permission_xattr(lo, fd, NULL, uid, gid, mode);
    else
        ret = fchown(fd, uid, gid);
    ...
}
```

`do_chown`, `do_fchownat`, and `do_fchmod` used the same distinction.

Creation/copy-up paths called these helpers when ownership differed or stat override was active and checked their return values. Required override-xattr failures therefore prevented publication rather than being silently converted into backing metadata.

This was the mechanism behind `xattr_permissions`: logical ownership/mode lived in an xattr when the backing filesystem/user namespace could not represent it directly.

## Rootless discriminator

Tracked `repro.py` captures the operating-system side of that design.

A control run performed:

1. create a temporary file and make uid/gid 65534 its physical owner;
2. permanently drop the probe process to uid/gid 65534;
3. try `chown(..., 12345, 12345)` -> `EPERM`;
4. set `user.containers.override_stat` to `12345:12345:600` -> success;
5. read the xattr back -> exact logical metadata is present while physical owner remains 65534.

That is not a contrived syscall contrast; it is exactly why an unprivileged overlay implementation has an xattr-based ownership mode.

## Rewrite boundary

The May 2026 Rust rewrite `71269043450580a03751a72fc8e0b2b827f865b3` replaced the old stat-override-aware ownership helpers with direct Rust syscall calls in the creation paths. The current rewrite-era source does not recreate create-time logical override writes.

The special-file subcase is independently corroborated by the project's 2023 fix `2d8613e7f5f85afb9077f2d9e3eadb48249fedf1` and NEWS v1.14, but this carrier covers the broader regular/directory ownership contract.

## Candidate design

See `CANDIDATE.md`.

The coherent repair is to restore a Rust equivalent of `do_fchown`/`do_fchownat`/`do_fchmod`:

- stat override inactive -> physical ownership/mode syscall;
- stat override active -> serialize logical uid/gid/mode into the configured override xattr;
- use caller-umask-masked logical mode (#624), not broadened backing mode;
- propagate required override-write failures and clean up uncommitted objects;
- extend the same helper with type/rdev data for special files (#625).

## Duplicate/test search

Open and closed upstream issue searches for `xattr_permissions` + create/owner/uid/gid/Rust override behavior returned no matching report during this pass.

Current tests contain stat-override parsing coverage but this investigation has not found a rootless create test where physical chown is deliberately impossible and logical override metadata must be used.

## Evidence boundary

Demonstrated:

- current startup can activate stat override in memory from `xattr_permissions`;
- current regular/directory/special creation paths use raw chown calls and discard failures;
- no create-time uid/gid/mode override write was found in those paths;
- old C `do_fchown` family used `write_permission_xattr()` under `xattr_permissions`;
- old callers checked required helper failures;
- local unprivileged control shows physical chown can fail while user override xattr succeeds on the same owned object;
- no matching upstream issue was found.

Not yet demonstrated:

- exact-head mounted rootless create integration because the local environment does not provide a compiled Rust fuse-overlayfs binary;
- complete behavior for privileged vs containers vs legacy user override formats;
- upper-root marker persistence/re-detection across mounts, which remains a separate startup/persistence question.

## Cleanup

The executed rootless control used a disposable temporary regular file and the probe environment owned cleanup. No mount, namespace, device, or persistent repository state was changed.

## Current disposition

State: `EXECUTING`

Next safe actions:

1. fake/rootless owned-CI create integration;
2. inspect upper-root marker initialization/persistence relative to the C startup path;
3. extend the logical-stat helper design to copy-up and chmod/chown without duplicating #621/#625.

External-contact state: no upstream interaction authorized or made.
