# Candidate design: make ACL inheritance an error-returning creation gate

## Contract

Change `inherit_acl()` from a best-effort `fn ... -> ()` into `fn ... -> FsResult<()>`.

Absence/unsupported **on the parent read side** can preserve the historical no-ACL behavior:

- `ENODATA` -> `Ok(())`
- `ENOTSUP` -> `Ok(())`

Other parent lookup/open/getxattr errors should propagate.

If a default ACL is present, failure to apply it to the newly created target must propagate. The old C helper returned the target `fsetxattr()` result directly.

## Dynamic xattr read

Do not keep the fixed 4096-byte buffer. The C helper used `safe_read_xattr(..., initial_size=4096)` and retried with a larger allocation on `ERANGE`.

A Rust version can either:

1. issue a size query (`getxattr` with zero-length buffer) then allocate exactly, with a race-aware retry; or
2. retain a starting buffer and double/retry on `ERANGE` up to Linux `XATTR_SIZE_MAX`.

This keeps large ACL values from being silently treated as “no ACL.”

## Callers

All child-creation paths should treat inherited ACL application as a pre-publication gate.

For workdir-temp + rename flows:

- failure must unlink the temporary object and return the ACL error;
- do not rename/publish the child.

For a directly created upper object:

- if ACL application fails, close/unlink the newly created object before returning the error, matching the old create-path behavior.

## Existing `noacl` control

`config.noacl` remains an intentional bypass and should return `Ok(())` without reading or applying ACLs.

## Tests

Use a fake xattr layer for deterministic unit tests, plus a Linux integration control where available:

- parent has a default ACL;
- target layer rejects `system.posix_acl_default` with `ENOTSUP`;
- current source would continue;
- candidate returns ENOTSUP and leaves no published child.

Also cover:

- parent `ENODATA` -> child creation succeeds;
- parent `ENOTSUP` -> child creation succeeds with no inherited ACL (historical behavior);
- target `ENOTSUP` -> child creation fails;
- `ERANGE` on first ACL read -> retry/grow rather than silently skip;
- `noacl` -> no xattr calls.

No upstream contact is authorized or made.
