# Candidate design: fail copy-up before publication when required metadata cannot be preserved

A correct repair must preserve cleanup ownership. Replacing every ignored metadata call with bare `?` would return the right error but can leave the workdir temporary object behind, so the candidate should pair error propagation with explicit cleanup or an RAII temporary-object guard.

## First repair boundary

Treat the metadata operations that directly preserve source object semantics as pre-publication gates:

### Regular files

After data copy and before the final rename:

- `futimens()` must succeed;
- `copy_xattr()` must succeed according to its existing internal policy (it already deliberately ignores selected per-xattr EPERM/ENOTSUP cases); 
- restoring the original mode with `fchmod()` must succeed.

If any gate fails:

1. save the errno/FsError;
2. close/drop relevant fds as needed;
3. unlink the workdir temporary file;
4. return the original error;
5. do not rename the temp file into the upper layer and do not change `node.layer_idx`.

### Directories

Before rename/publication:

- timestamp preservation via `futimens()` must succeed;
- `copy_xattr()` must succeed under its existing per-attribute policy.

Failure must remove the temporary directory (after dropping the open fd) and return the metadata error without marking the node upper.

## Ownership calls

The rewrite also ignores `fchown`/`fchownat`, while the C implementation used `do_fchown*()` and propagated required failures. Ownership/stat-override behavior has additional rootless policy, so it should be repaired only after re-establishing the Rust equivalent of the old `do_fchown` abstraction rather than naively changing direct `fchown()` to `?`.

This first candidate therefore keeps ownership as an explicitly adjacent subtask while fixing unambiguous timestamp/xattr/mode publication gates.

## Why `copy_xattr()` is already policy-aware

The helper itself chooses which per-xattr failures are tolerated:

- `ENODATA` while fetching a raced-away attribute is skipped;
- `EPERM` / `ENOTSUP` when setting an individual destination attribute are currently skipped;
- other failures are returned.

The bug tracked here is that the *caller discards even the errors the helper intentionally decided were fatal*.

## Tests

A deterministic unit/fake-syscall test should inject failure at each pre-publication gate and assert:

- returned error matches injected errno;
- final upper path does not exist;
- workdir temporary object is removed;
- node still points to the lower layer;
- successful control still publishes exactly once.

Also test a `copy_xattr()` per-attribute failure that the helper intentionally suppresses, to make sure the outer fix does not accidentally tighten the helper's established policy.

No upstream contact is authorized or made.
