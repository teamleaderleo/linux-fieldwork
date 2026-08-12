# fuse-overlayfs Rust rewrite claims killpriv ownership but stat overrides preserve privilege mode

Date: 2026-08-12

## TL;DR

The current Rust daemon negotiates `FUSE_HANDLE_KILLPRIV`, whose Linux contract says the filesystem handles clearing suid/sgid/file capabilities on write, chown, and truncate. The pre-Rust C daemon did not negotiate this capability.

At exact reviewed head `containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117`, the stat-override path does not implement that responsibility coherently:

- a logical chown updates only the uid/gid/mode override xattr and, if mode was not explicitly supplied, preserves `cur_mode` unchanged;
- backing writes/truncates do not update the logical override xattr, so a setuid/setgid mode stored there can survive even if the backing VFS changes physical mode bits;
- no explicit `security.capability` removal associated with the logical stat-override path was found.

This is particularly important under `xattr_permissions`, because the mounted logical mode may intentionally differ from the backing inode mode. Backing-VFS killpriv side effects therefore cannot be assumed to satisfy the logical FUSE contract.

The conservative first candidate is to stop negotiating `FUSE_HANDLE_KILLPRIV`, restoring the old responsibility split until userspace implements killpriv for both physical and logical metadata paths.

No upstream contact is authorized or has been made.

## FUSE contract

Current Rust init requests:

```rust
InitFlags::FUSE_HANDLE_KILLPRIV
```

Linux UAPI defines:

```text
FUSE_HANDLE_KILLPRIV: fs handles killing suid/sgid/cap on write/chown/trunc
```

This is v1, not `FUSE_HANDLE_KILLPRIV_V2`. V2 has additional caller-CAP_FSETID rules and an explicit `FATTR_KILL_SUIDGID` request bit. The current daemon only opts into the older all-responsibility contract.

Current fuser also documents the V2 request flag as meaning the filesystem must clear suid/sgid when the caller lacks CAP_FSETID, confirming that killpriv is a userspace responsibility once negotiated.

## Current logical chown path

When stat override mode is active, current `setattr()` reads existing logical fields, then computes:

```rust
let new_uid = uid.map(...).unwrap_or(cur_uid);
let new_gid = gid.map(...).unwrap_or(cur_gid);
let new_mode = mode.map(|m| m & 0o7777).unwrap_or(cur_mode);
let override_val = format!("{}:{}:{:o}", new_uid, new_gid, new_mode);
fsetxattr(... override_val ...)?;
```

If the operation changes uid/gid but does not explicitly carry a new mode, a current logical mode such as `04755` is serialized unchanged into the new ownership record.

That is incompatible with the negotiated v1 responsibility to kill privilege bits on chown.

## Write/truncate interaction with stat override

A backing write may cause the backing filesystem to update its physical mode according to normal VFS rules. But the mounted stat path can later call `override_mode()` and replace uid/gid/mode from the override xattr.

A local ordinary-file control in tracked `repro.py` shows a `user.containers.override_stat=1000:1000:4755` xattr remains unchanged across a write. The user xattr is separate metadata and backing write semantics do not rewrite it.

Thus the logical setuid mode can survive/reappear even if physical mode handling was correct.

Truncate has the same representation problem: current setattr can change size through backing `ftruncate`/truncate while the logical override mode remains unchanged unless an explicit mode update is also performed.

## File capabilities

The Linux capability contract includes `cap` as well as suid/sgid. No explicit removal of `security.capability` was found in the current stat-override ownership/truncate paths during this pass.

This investigation does not claim a reproduced file-capability exploit. It records the source-contract gap and keeps capability removal as part of the complete implementation requirement.

## Pre-Rust boundary

A source search of the pre-Rust C implementation found no `KILLPRIV` capability negotiation. The old daemon therefore did not tell the kernel that it had taken ownership of this policy.

The initial Rust rewrite `71269043450580a03751a72fc8e0b2b827f865b3` already adds `FUSE_HANDLE_KILLPRIV`, establishing the responsibility-transfer boundary at the rewrite.

## Conservative candidate

Tracked `candidate.patch` removes `InitFlags::FUSE_HANDLE_KILLPRIV` from requested capabilities.

This is intentionally conservative:

- it restores the C-era negotiation boundary;
- it avoids claiming a server capability that is not implemented for logical override metadata;
- it does not prevent a later, fuller implementation from re-enabling HANDLE_KILLPRIV once write/chown/truncate and capability-xattr semantics are covered and tested.

A full implementation would need a shared killpriv helper that updates logical override mode, removes capability metadata where required, and coordinates with backing operations without resurrecting privilege state on subsequent getattr.

## Reduced discriminator

Tracked `repro.py` shows two parts of the issue:

1. a user stat-override xattr carrying `04755` survives an ordinary backing write;
2. current logical-chown arithmetic with uid-only change preserves `cur_mode=04755`, whereas killpriv requires at least clearing the setuid bit under the v1 contract.

The probe does not require a mounted FUSE filesystem; it isolates the metadata channel that backing VFS operations cannot modify for fuse-overlayfs.

## Duplicate/test search

Open and closed upstream issue searches for HANDLE_KILLPRIV + suid/xattr_permissions/Rust returned no matching report during this pass.

Current source search did not surface a test that creates logical setid override metadata, writes/chowns/truncates through the mount, and verifies privilege bits/capabilities are cleared.

## Evidence boundary

Demonstrated:

- current Rust negotiates HANDLE_KILLPRIV v1;
- Linux defines that as filesystem responsibility for suid/sgid/cap on write/chown/trunc;
- stat-override chown preserves current logical mode when only uid/gid changes;
- stat-override xattr survives an ordinary backing write in a local control;
- backing mode side effects therefore cannot by themselves clear logical override mode;
- old C did not negotiate killpriv;
- Rust rewrite introduction already requests it;
- no matching upstream issue was found.

Not yet demonstrated:

- exact-head mounted setuid/write/chown/truncate integration;
- file-capability behavior through an actual FUSE mount;
- every kernel behavior after removing the capability on the modern fuser stack (the old C negotiation is the compatibility precedent).

## Cleanup

The local control used a temporary regular file and user xattr and removed both with the temporary-file lifecycle. No mount, namespace, or device state remained.

## Current disposition

State: `EXECUTING`

Next safe actions:

1. mounted owned-CI setid/write/chown/truncate tests if available;
2. audit whether passthrough mode changes killpriv ownership further, because data writes can bypass the FUSE write callback;
3. keep HANDLE_KILLPRIV disabled unless/until logical and physical metadata paths have a shared tested implementation.

External-contact state: no upstream interaction authorized or made.
