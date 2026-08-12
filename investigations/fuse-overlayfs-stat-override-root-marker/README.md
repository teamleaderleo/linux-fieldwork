# fuse-overlayfs Rust rewrite no longer persists the stat-override root marker

Date: 2026-08-12

## TL;DR

The current Rust implementation can force stat-override mode for the **current upper layer** from `xattr_permissions`, but unlike the pre-Rust C implementation it does not persist that mode as an override xattr on the upper root.

That matters across layer reuse. Current lower layers are not force-configured from `xattr_permissions`; `DirectAccess::load_data_source()` detects `StatOverrideMode` by probing override xattrs on the layer root. If a directory that was an upper layer in one mount is later consumed as a lower layer, child `user.containers.override_stat` / related metadata can be present while the root has no marker, so the later mount detects `StatOverrideMode::None` and does not interpret those child overrides.

The old C startup path explicitly wrote a default logical stat marker (`0:0:0555`) to the upper root when the selected override xattr was missing. Failure to create that marker aborted startup.

This is a durability/interoperability regression distinct from #626's per-child create-time override omission: even after child writes are restored, a durable root marker is required for a produced layer to remain self-describing when reused later.

No upstream contact is authorized or has been made.

## Current upper initialization

Current `layer::init_layers()` loads the upper DataSource, then:

```rust
if ds.stat_override_mode() == StatOverrideMode::None {
    match xattr_permissions {
        1 => ds.set_stat_override(StatOverrideMode::Privileged),
        2 => ds.set_stat_override(StatOverrideMode::Containers),
        _ => {}
    }
}
```

`DirectAccess::set_stat_override()` only assigns:

```rust
self.stat_override = mode;
```

No xattr is written to the upper root by this operation.

## Current lower detection

`DirectAccess::load_data_source()` detects mode by probing the layer root:

1. privileged override xattr -> `Privileged`;
2. `user.containers.override_stat` -> `Containers`;
3. legacy user override -> `User`;
4. otherwise -> `None`.

`layer::init_layers()` only force-applies the configured `xattr_permissions` value to the upper DataSource. Lower DataSources retain whatever mode their root probe detected.

Therefore the in-memory override setting is not enough to make a layer self-describing for later reuse.

## Pre-Rust C control

The old startup code selected the override mode and xattr name from `xattr_permissions`, probed the upper root, and if the selected marker was missing performed:

```c
/* If the mode is missing, set a standard value. */
ret = write_permission_xattr(&lo,
                             get_upper_layer(&lo)->fd,
                             get_upper_layer(&lo)->path,
                             0, 0, 0555);
if (ret < 0)
    error(EXIT_FAILURE, errno, "write xattr `%s` to upperdir", name);
```

For containers mode it also had compatibility logic around the legacy user override marker before deciding the marker was absent.

The old marker therefore had two roles:

- initialize the upper layer's logical root stat metadata;
- durably identify the override encoding for future consumers of that layer.

## Reduced layer-reuse discriminator

Tracked `repro.py` creates a temporary directory with a child carrying:

```text
user.containers.override_stat = 12345:12345:600
```

With no root marker:

```text
child override present: b'12345:12345:600'
mode detected without root marker: None
current later-lower interpretation: backing stat; child override not consulted
```

After adding the historical-style root marker:

```text
user.containers.override_stat = 0:0:555
mode detected with old-style root marker: Containers
old/candidate later-lower interpretation: child logical override eligible
```

The probe models current `DirectAccess` detection using ordinary Linux xattrs. It does not require a FUSE mount to establish the persistence contract.

## Interaction with #626

#626 tracks the current failure to write logical uid/gid/mode overrides on newly created children.

This investigation is independent in time:

- #626 is about **producing correct child metadata during one mount**;
- this carrier is about **making the produced layer self-describing to later mounts**.

Fixing only #626 without the root marker would create valid child override xattrs that can still be ignored when the directory is later used as a lower layer.

## Candidate design

See `CANDIDATE.md`.

When explicit `xattr_permissions` activates an override mode on a fresh upper layer, initialize the corresponding root marker before accepting the mount. Existing valid markers continue to drive detection; conflicts need an explicit compatibility decision rather than silent reinterpretation.

## Duplicate/test search

Open and closed upstream issue searches for xattr-permissions root-marker/layer-reuse behavior returned no matching report during this pass.

Current source tests exercise stat-override parsing/detection but this investigation has not found a two-mount lifecycle test where an upper layer from one run is later consumed as a lower layer.

## Evidence boundary

Demonstrated:

- current explicit `xattr_permissions` changes only the upper DataSource's in-memory mode;
- current lower layers detect override mode solely from root xattrs;
- current setter does not persist a marker;
- old C startup wrote a default root marker when missing and treated write failure as fatal;
- ordinary xattr model shows child override metadata alone is insufficient for the current root-probe detector;
- no matching upstream issue was found.

Not yet demonstrated:

- two exact-head mounted fuse-overlayfs sessions reusing the same directory;
- every historical compatibility rule for legacy vs containers root markers;
- a compile-tested Rust startup implementation.

## Cleanup

The reduced model used a temporary directory/file and user xattrs and removed them with the temporary directory. No mount, namespace, or device state was created.

## Current disposition

State: `EXECUTING`

Next safe actions:

1. owned two-lifecycle integration: mount A produces override metadata, mount B reuses its upper as lower;
2. reconstruct exact legacy/containers root-marker conflict rules from the C startup path;
3. continue audit of other persistent layer metadata initialized by C but only kept in memory by the Rust rewrite.

External-contact state: no upstream interaction authorized or made.
