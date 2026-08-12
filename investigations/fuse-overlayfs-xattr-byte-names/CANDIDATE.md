# Candidate design: keep Linux xattr names as bytes

The current UTF-8 restriction spans FUSE handlers, namespace filtering, DataSource methods, syscall wrappers, list filtering, and copy-up. A correct repair should change the name representation coherently rather than adding lossy conversions at individual call sites.

## Required semantic boundary

Linux xattr names are bounded NUL-terminated byte strings. The overlay-specific prefixes used by fuse-overlayfs are ASCII byte prefixes, so namespace filtering does not require Unicode.

## Suggested contract changes

1. FUSE handlers should start from `name.as_bytes()` rather than `name.to_str()`.
2. `can_access_xattr`, `is_encoded_xattr_name`, `decode_xattr_name`, and `encode_xattr_name` should operate on `&[u8]` / `Vec<u8>` using byte-prefix checks such as `starts_with(b"user.fuseoverlayfs.")`.
3. `DataSource::getxattr` should accept an xattr name as bytes, not `&str`.
4. `sys::xattr` wrappers should accept `&[u8]` names and convert them with the existing `cstr_bytes()` helper. This preserves the only relevant string restriction: interior NUL is invalid because the kernel API is C-string based.
5. `filter_xattr_list()` should split the NUL-separated list into byte slices and apply byte-prefix encode/decode rules directly. It must not call `from_utf8()` or drop undecodable names.
6. `copy_xattr()` should carry raw listed names through get/set without `filter_map(from_utf8)`.
7. Logging of xattr names may use a lossless/debug byte representation or `OsStr` debug formatting; logging must not become the reason to reject the request.

## Compatibility controls

The byte-prefix implementation must preserve current overlay filtering for ASCII-reserved namespaces:

- `user.fuseoverlayfs.*` hidden;
- `trusted.overlay.*` hidden;
- `user.overlay.*` hidden;
- `security.*` hidden in Containers stat-override mode;
- `user.containers.override_` encode/decode behavior preserved.

Names such as `b"user.\xff"` do not overlap any internal ASCII prefix and should flow through unchanged.

## Suggested tests

Add byte-name tests at three layers:

1. xattr namespace/filter unit tests with `b"user.\xff"` and a reserved-prefix control;
2. syscall/DataSource tests that set/get/list/remove a non-UTF-8 user xattr on a temporary regular file;
3. mounted integration: lower file has `user.\xff=value`, verify list/get through fuse-overlayfs, trigger copy-up, then verify the upper file still has the raw byte-name/value.

Also test that an interior NUL byte still returns `EINVAL` because it cannot be represented by the Linux xattr syscall ABI.

No upstream contact is authorized or made.
