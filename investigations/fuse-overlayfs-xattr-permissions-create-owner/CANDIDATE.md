# Candidate design: restore do_fchown/do_fchmod stat-override semantics in Rust creation paths

The pre-Rust implementation centralized ownership/mode application behind `do_fchown`, `do_fchownat`, and `do_fchmod`. Under `xattr_permissions` those helpers wrote the logical uid/gid/mode override xattr instead of attempting a backing chown/chmod that may be impossible in a user namespace.

The Rust rewrite should restore that abstraction rather than sprinkling conditional xattr writes into individual FUSE callbacks.

## 1. A Rust logical-stat helper

Add a helper taking:

- target fd or dirfd/path;
- logical uid/gid/mode;
- target object type/rdev when extended stat override is needed;
- active `StatOverrideMode`.

Behavior:

- `StatOverrideMode::None`: perform the physical `fchown`/`fchownat` (and chmod where required), preserving current non-xattr behavior;
- override active: write the correct override xattr carrying logical uid/gid/mode instead of requiring the backing filesystem to represent those identities directly.

For regular files/directories the existing three-field `uid:gid:mode` form is sufficient. Special files use the four-field form tracked separately in #625.

Required override-xattr write failures must propagate.

## 2. Creation call sites

Use the helper in at least:

- regular `create()`;
- `mkdir()`;
- `mknod()`;
- symlink creation where ownership override is expected;
- copy-up paths when source logical owner/mode must survive a user-namespace-incompatible backing layer.

Do not call raw `fchown` and discard its result when stat override is active.

## 3. Logical mode source

Creation must use the caller-requested mode after the FUSE request umask has been applied (#624), not the potentially broadened backing mode.

## 4. Cleanup ownership

If a required logical override write fails before rename/publication:

- remove the workdir temporary;
- return the underlying error;
- do not register the node as upper.

For direct create, unlink the just-created upper object before returning if it is not otherwise safe to leave it behind.

## 5. Startup/root marker remains separate

Current `init_layers()` can force an in-memory `StatOverrideMode` from `xattr_permissions` even if the upper root has no marker. The old C program also initialized/persisted an upper-root override marker. That persistence behavior should be audited separately so this repair does not conflate per-child logical metadata with mount-to-mount detection.

## Tests

A deterministic rootless test should model the feature's actual purpose:

1. run daemon/backing operations under an unprivileged uid;
2. create a child whose logical uid/gid cannot be applied by physical chown;
3. verify raw chown fails with EPERM;
4. verify user override xattr is writable;
5. candidate create succeeds and mounted getattr reports the logical uid/gid/mode;
6. backing uid/gid can remain the daemon's representable identity.

Also cover:

- override-xattr write failure -> creation fails and cleans up;
- `xattr_permissions=0` -> physical chown behavior remains;
- squash options retain their historical semantics;
- requested mode is already caller-umask-masked before serialization.

No upstream contact is authorized or made.
