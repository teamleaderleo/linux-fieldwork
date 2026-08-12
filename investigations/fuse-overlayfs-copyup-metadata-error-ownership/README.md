# fuse-overlayfs Rust rewrite publishes copy-up after metadata preservation failure

Date: 2026-08-12

## TL;DR

The current Rust copy-up path can publish a new upper object even when required source metadata could not be preserved.

At exact reviewed head `containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117`, regular-file copy-up performs:

```rust
let _ = fchown(...);
copy_data(...) ?;
let _ = futimens(...);
let _ = copy_xattr(...);
let _ = fchmod(...);
renameat(...)?;
```

Directory copy-up likewise ignores ownership, timestamp, and xattr-copy errors before renaming the temporary directory into place.

The pre-Rust C implementation treated the corresponding required metadata failures as fatal. In the regular-file copy-up path it checked `do_fchown()`, `futimens()`, and `copy_xattr()` and jumped to cleanup on failure instead of publishing the upper copy.

The ignored calls are present in the May 2026 Rust rewrite, making this an error-ownership regression introduced by the rewrite.

This investigation deliberately separates the unambiguous timestamp/xattr/mode gates from ownership/stat-override policy, which needs a distinct rootless-compatible abstraction.

No upstream contact is authorized or has been made.

## Current regular-file publication boundary

Current Rust creates a temporary workdir file with an extra owner-write bit, copies data, attempts metadata restoration, then renames the temporary file into the final upper path.

The following failures are discarded before publication:

- `futimens()` — source atime/mtime may not be preserved;
- `copy_xattr()` — the helper can return an error after deciding it is not one of its tolerated per-attribute failures, but the caller still discards it;
- `fchmod()` — the temporary file was deliberately created with `mode | 0o200`, so failure to restore the original mode can leave an extra write permission on the published upper object.

`fchown()` is also ignored, but ownership has additional stat-override/rootless semantics and is kept as an adjacent subtask rather than oversimplified here.

## Directory publication boundary

`create_node_directory()` creates a workdir directory, opens it, then currently does:

```rust
let _ = fs::fchown(...);
let _ = fs::futimens(...);
let _ = copy_xattr(...);
...
renameat(...)
```

A timestamp/xattr failure therefore does not stop the directory from becoming the upper object.

## Pre-Rust C control

The old C copy-up had explicit failure ownership.

For ownership where required:

```c
ret = do_fchown(...);
if (ret < 0)
    goto exit;
```

For timestamps:

```c
times[0] = st.st_atim;
times[1] = st.st_mtim;
ret = futimens(dfd, times);
if (ret < 0)
    goto exit;
```

For xattrs:

```c
ret = copy_xattr(...);
if (ret < 0)
    goto exit;
```

Thus the previous implementation did not intentionally define these preservation failures as best-effort success.

## Introduction boundary

Rust rewrite commit:

`71269043450580a03751a72fc8e0b2b827f865b3` — `fuse-overlayfs: rewrite in Rust`

The rewrite already contains the current `let _ =` calls for directory and regular-file copy-up. No later regression boundary is required.

## `copy_xattr()` policy control

This finding does **not** require every xattr operation to become fatal.

The current helper already has its own policy:

- raced-away `ENODATA` while fetching is skipped;
- selected destination `EPERM` / `ENOTSUP` failures are skipped;
- other failures return `Err`.

The outer copy-up bug is that even those explicitly returned errors are discarded.

That gives a clean compatibility boundary for repair: propagate `copy_xattr()`'s existing final result without changing its per-xattr tolerance policy in the same patch.

## Mode-restoration consequence

Regular files are created with:

```rust
mode | 0o200
```

so data can be written even if the original owner-write bit was clear.

After copying, the code attempts:

```rust
let _ = fchmod(dfd, mode);
```

and publishes the file even if that restoration fails.

This is a particularly concrete correctness boundary because the temporary mode is knowingly different from the requested final mode.

The investigation does not label this a security vulnerability; failure prevalence and attacker control have not been established.

## Reduced discriminator

Tracked `repro.py` models an injected pre-publication metadata error.

Current state machine:

```text
metadata gate -> EIO
error discarded
rename/publish -> success
```

Candidate state machine:

```text
metadata gate -> EIO
unlink temp
return EIO
final upper object not published
```

This model isolates error ownership; it does not claim an exact mounted syscall-failure injection run.

## Candidate design

See `CANDIDATE.md`.

The first safe repair boundary is:

- regular `futimens`, `copy_xattr`, final `fchmod` are required pre-publication gates;
- directory `futimens`, `copy_xattr` are required pre-publication gates;
- failures clean up the workdir temporary and leave the node on the lower layer;
- ownership handling gets a follow-up that restores the old `do_fchown`-style stat-override semantics rather than blindly propagating direct `fchown()` failures.

A bare `?` is insufficient unless temp-object cleanup is guaranteed.

## Duplicate/test search

Open and closed upstream issue searches for Rust copy-up metadata/futimens/xattr ignored-error behavior returned no matching report during this pass.

Current source has happy-path copy-up tests but this investigation has not found a fault-injection test asserting that metadata failure prevents publication.

## Evidence boundary

Demonstrated:

- exact current regular/directory copy-up ignores metadata return values before rename;
- `copy_xattr()` has a meaningful returned-error policy which the caller discards;
- regular temp mode is intentionally broader (`mode | 0o200`) and final fchmod error is discarded;
- pre-Rust C treated required ownership/timestamp/xattr preservation failures as fatal;
- ignored metadata calls are present in the Rust rewrite introduction;
- no matching upstream issue was found.

Not yet demonstrated:

- mounted exact-head fault injection for `futimens`, `copy_xattr`, or `fchmod`;
- prevalence of these syscall failures on ordinary healthy local filesystems;
- the correct complete Rust ownership/stat-override repair;
- a compile-tested RAII cleanup implementation.

## Cleanup

No mount, namespace, device, or persistent filesystem state was changed for this investigation. The reduced discriminator is a pure state model.

## Current disposition

State: `EXECUTING`

Next safe actions:

1. design/inject a fake metadata syscall failure in owned CI if available;
2. separately reconstruct old `do_fchown` semantics in the Rust stat-override model;
3. audit copy-data short-read/EOF handling and temporary-object cleanup on every pre-rename error.

External-contact state: no upstream interaction authorized or made.
