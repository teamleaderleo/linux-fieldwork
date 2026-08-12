# Candidate design: persist stat-override mode on the upper root

The old C startup path used the upper-root override xattr as a durable marker for how that filesystem layer should be interpreted. The Rust rewrite currently changes only an in-memory enum when `xattr_permissions` is requested.

## Startup contract

When the upper layer has no existing override marker and `xattr_permissions` selects a stat-override mode:

1. choose the matching override xattr name;
2. write a valid root marker such as the historical logical `0:0:0555` representation;
3. fail mount initialization if this required marker cannot be written;
4. set the in-memory mode only after the durable marker succeeds.

For containers mode, preserve the historical compatibility check for the legacy user override marker where applicable.

## Why persistence matters

Only the current upper layer is force-configured from the `xattr_permissions` option. Lower layers are loaded independently and detect their `StatOverrideMode` by probing the root xattr.

Therefore the marker must survive beyond one process lifetime: an upper layer from mount A may become a lower layer in mount B. Its child override xattrs are meaningful only if mount B can identify the layer's override encoding from the root.

## Existing-marker behavior

If a marker already exists, detection should continue to win rather than overwriting it blindly. Conflicting explicit `xattr_permissions` values should be rejected or resolved according to the old compatibility contract rather than silently changing interpretation.

## Tests

A non-mounted layer lifecycle test can cover the core contract:

1. fresh upper root, containers mode requested -> root marker created;
2. create child with logical override metadata;
3. destroy first DirectAccess/mount state;
4. load same directory as a lower layer without forcing its mode;
5. root probe detects Containers mode;
6. child stat applies its logical override.

Negative control: remove root marker while leaving child override -> later lower load detects None and cannot interpret the child metadata.

Also test startup failure if the requested marker cannot be written.

No upstream contact is authorized or made.
