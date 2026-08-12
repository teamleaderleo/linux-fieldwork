# Candidate design: restore special-file stat override semantics

This regression has two independent repair gates: creation must write the logical override metadata, and stat must be willing to consume it for special files.

## 1. mknod backing mode

Honor the request umask first. For default `xattr_permissions=0`, use the masked requested mode directly.

When `xattr_permissions != 0`, retaining a permissive backing mode can be intentional, but it must be paired with a logical override xattr exactly as the C implementation did.

## 2. serialize extended stat override during creation

When stat override mode is active, mknod should encode the logical uid/gid/mode plus object type using the existing 4-field format already understood by `parse_and_apply_override()`:

- FIFO: `uid:gid:mode:pipe`
- socket: `uid:gid:mode:socket`
- block device: `uid:gid:mode:blockMAJ:MIN`
- char device: `uid:gid:mode:charMAJ:MIN`

The uid/gid/mode values must be the logical mapped/requested values, not the widened backing permissions.

The target xattr name follows the layer's `StatOverrideMode` (`security.fuseoverlayfs.override_stat`, `user.containers.override_stat`, etc.). Failure to store required override metadata must abort/clean up creation rather than publishing a special file whose visible mode/identity is wrong.

## 3. stat reader

Remove the current production gate that returns early for every non-regular/non-directory object:

```rust
if file_type != S_IFDIR && file_type != S_IFREG {
    return Ok(());
}
```

`parse_and_apply_override()` already has explicit code and unit tests for symlink, FIFO, socket, block, and char types. Let the xattr parser decide the object type when the extended fourth field is present.

For a legacy three-field override, preserve the backing object's existing `S_IFMT` bits.

## 4. keep default-path behavior separate

When `xattr_permissions=0`, do not manufacture override metadata. The object should simply be created with the caller-masked requested mode.

## 5. tests

Add tests through the real `override_mode()` wrapper, not only the parser:

- backing FIFO 0755 + override `0:0:600:pipe` -> stat mode FIFO 0600;
- backing char device + `...:char1:3` -> type/rdev/mode restored;
- backing block device + `...:block8:0` -> type/rdev/mode restored;
- regular and directory existing controls;
- missing override -> backing stat unchanged.

Creation integration under `xattr_permissions` should create a FIFO/device with a restrictive mode and verify getattr reports that logical mode even though backing permissions are widened.

No upstream contact is authorized or made.
