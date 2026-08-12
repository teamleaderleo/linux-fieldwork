# fuse-overlayfs Rust rewrite rejects Linux xattr byte names

Date: 2026-08-12

## TL;DR

The current Rust implementation imposes a UTF-8 requirement on Linux extended-attribute names even though the Linux xattr ABI does not.

At exact reviewed head `containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117`:

- FUSE `setxattr`, `getxattr`, and `removexattr` convert `&OsStr` names with `to_str()` and return `EINVAL` for non-UTF-8 names;
- `filter_xattr_list()` calls `std::str::from_utf8()` and silently skips undecodable names, so `listxattr` hides them;
- `copy_xattr()` does the same `filter_map(from_utf8)` and silently omits such attributes during copy-up;
- the DataSource/syscall xattr APIs take `&str`, so the UTF-8 restriction is embedded below the FUSE handler too.

Linux's syscall layer treats an xattr name as a bounded NUL-terminated byte string. `fs/xattr.c::import_xattr_name()` uses `strncpy_from_user()` and checks only length/error; it performs no Unicode validation.

A local ordinary-file control successfully set, got, listed, and removed the raw name `b"user.\xff"`.

The pre-Rust C implementation accepted xattr names as `const char *`, iterated the raw NUL-separated `flistxattr()` buffer, and passed those names through its encode/decode and get/set paths without UTF-8 conversion. The UTF-8 requirement is present from the May 2026 Rust rewrite, so this is a rewrite regression.

No upstream contact is authorized or has been made.

## Current direct-operation failures

Current `setxattr()` starts with:

```rust
let name_str = match name.to_str() {
    Some(n) => n,
    None => {
        reply.error(Errno::EINVAL);
        return;
    }
};
```

`getxattr()` and `removexattr()` use the same gate.

The FUSE API already supplies the name as `&OsStr`, which can represent Linux byte names. The loss is introduced locally when converting to `&str`.

## Current list failure

`filter_xattr_list()` splits the kernel's NUL-separated byte buffer, then does:

```rust
let name = match std::str::from_utf8(name_bytes) {
    Ok(s) => s,
    Err(_) => continue,
};
```

So the list operation reports a successful filtered list that simply omits a valid attribute whose name is not UTF-8.

## Current copy-up failure

`copy_xattr()` similarly builds its list of names with:

```rust
.filter_map(|s| std::str::from_utf8(s).ok())
```

A lower-layer `user.\xff` attribute is therefore not copied to the upper object when copy-up occurs.

That creates an especially important asymmetry: the lower filesystem can hold the metadata, but modifying the file through fuse-overlayfs can silently remove it from the overlay-visible upper version.

## Syscall-wrapper restriction

Current `src/sys/xattr.rs` defines get/set/remove helpers with `name: &str` and converts them with a string CString helper. The project already has `cstr_bytes()` for byte paths, so the syscall layer can be made byte-safe without introducing unsafe string handling.

`DataSource::getxattr()` likewise uses `name: &str`, carrying the restriction above the syscall layer.

## Linux ABI control

Current Linux `fs/xattr.c::import_xattr_name()`:

```c
int error = strncpy_from_user(kname->name, name, sizeof(kname->name));
if (error == 0 || error == sizeof(kname->name))
    return -ERANGE;
if (error < 0)
    return error;
return 0;
```

No UTF-8 validation is performed. The relevant representation constraints are C-string/NUL termination and the xattr name-length bound.

## Local byte-name control

Tracked `repro.py` uses Python's byte-oriented xattr APIs on a temporary regular file:

```text
current Rust gate: EINVAL / omitted
linux setxattr bytes: OK
linux getxattr bytes: b'fieldwork'
linux listxattr raw contains name: True
linux removexattr bytes: OK
```

Python may display the byte through surrogateescape when listing, but re-encoding recovers the original `b"user.\xff"` name.

This establishes that the tested local Linux filesystem accepts the metadata form the Rust layer rejects.

## Pre-Rust control

The old C FUSE xattr handlers received names as `const char *` directly from libfuse. The old copy-up code iterated the `flistxattr()` byte buffer using NUL termination:

```c
for (it = buf; it - buf < xattr_len; it += strlen(it) + 1) {
    const char *decoded_name = decode_xattr_name(sl, it);
    ...
}
```

Its namespace encode/decode logic operated on C byte strings and did not impose a Unicode encoding requirement.

## Introduction boundary

The Rust rewrite commit `71269043450580a03751a72fc8e0b2b827f865b3` already defines xattr namespace/filter helpers in terms of `&str` and uses `from_utf8()` in list filtering. The current direct handler/syscall API follows the same design.

This makes the Rust rewrite the demonstrated compatibility boundary.

## Candidate design

See `CANDIDATE.md`.

The coherent repair is to treat xattr names as bytes through the whole stack:

- FUSE `OsStr::as_bytes()`;
- byte-prefix namespace filtering/encoding;
- DataSource byte names;
- syscall wrappers using `cstr_bytes()`;
- list and copy-up logic operating on raw NUL-separated byte slices.

The reserved overlay prefixes are ASCII, so all existing namespace policy can be expressed as byte-prefix comparisons without Unicode.

## Test gap and suggested regression

Current tests exercise normal UTF-8 xattr names but no non-UTF-8 name.

A useful regression should cover:

1. direct set/get/list/remove of `b"user.\xff"` through a mounted filesystem;
2. lower-layer `b"user.\xff"` visible through list/get;
3. trigger regular-file copy-up and verify upper backing file preserves name and value;
4. reserved internal-prefix controls remain hidden;
5. interior NUL remains rejected as `EINVAL`.

## Duplicate search

Open and closed upstream issue searches for xattr UTF-8 / non-UTF-8 byte-name behavior returned no matching report during this pass.

## Evidence boundary

Demonstrated:

- current direct FUSE operations reject undecodable `OsStr` xattr names;
- current list filter silently drops undecodable names;
- current copy-up silently drops undecodable names;
- current DataSource/syscall wrappers require `&str`;
- Linux syscall import imposes no UTF-8 validation;
- local Linux filesystem successfully round-trips `user.\xff`;
- old C path operated on byte C strings without Unicode conversion;
- UTF-8 filtering is present at Rust rewrite introduction;
- no matching upstream issue was found.

Not yet demonstrated:

- exact-head mounted integration because no owned/compiled fuse-overlayfs runtime is available in this local container;
- behavior on every backing filesystem (the Linux ABI permits the name, while individual filesystem namespace constraints may vary);
- compile-tested final shape of the API-wide byte conversion.

## Cleanup

The local control used a temporary regular file, added and removed one `user.*` xattr, and deleted the file. No mount, namespace, device, or persistent state remained.

## Current disposition

State: `EXECUTING`

Next safe actions:

1. seek owned CI/fork integration for a real mounted byte-name round-trip;
2. audit symlink/special-file copy-up metadata preservation, where current Rust paths visibly differ from regular-file handling;
3. keep byte-name repair separate from xattr value-size/error handling unless a distinct discriminator promotes.

External-contact state: no upstream interaction authorized or made.
