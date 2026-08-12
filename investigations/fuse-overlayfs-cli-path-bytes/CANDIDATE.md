# Candidate design: keep command-line filesystem paths as OS bytes

The current configuration representation uses `String` for Linux filesystem paths and begins with `std::env::args()`. A correct repair must avoid converting path-bearing arguments to Unicode.

## Entry point

Use:

```rust
let args: Vec<OsString> = std::env::args_os().collect();
```

instead of `std::env::args()`.

Rust's own standard library documents/implements `env::args()` by converting each `OsString` with `into_string().unwrap()`, so switching only later parser fields is not sufficient.

## Configuration representation

Represent filesystem paths as OS-native/path types:

- `lowerdir`, `upperdir`, `workdir`, `mountpoint`: `OsString` / `PathBuf` where possible;
- operations that need raw Linux bytes can use `std::os::unix::ffi::OsStrExt::as_bytes()`.

Options that are genuinely textual/numeric (`uidmapping`, `gidmapping`, booleans, timeout) may still validate UTF-8 explicitly and return a normal parse error if their grammar requires text.

## `-o` parsing

Because lower/upper/work paths are embedded inside the comma-separated `-o` option string, the option splitter itself should operate on bytes (ASCII delimiters `,`, `=`, `\\`, `"`, `:`) rather than first converting the whole argument to UTF-8.

A clean design is:

1. split option tokens by ASCII byte grammar;
2. identify ASCII option keys;
3. keep path values as raw byte vectors / OsString;
4. convert only explicitly textual values to `str` for numeric/enum parsing.

This preserves existing escaping semantics while keeping Linux path bytes lossless.

## Lower layers / open wrappers

`open_trusted`, layer initialization, and other path-taking helpers currently accept `&str`. They should gain `&OsStr`/`&Path` or byte-slice forms and use the project's existing `cstr_bytes()` path helper where raw libc paths are needed.

## Realpath adjacency

Current `sys::fs::realpath()` converts the libc result with `to_string_lossy().into_owned()`. That would still destroy bytes after fixing argv/config. It should instead return `OsString`/`PathBuf` (or `Vec<u8>`), constructing it from the returned C bytes without lossy Unicode conversion.

This matters at least for `DirectAccess.resolved_path` and NFS file-handle probing.

## Logging

Paths should be logged with `{:?}` / `Path::display()` as appropriate. Logging must not force a Unicode conversion that changes the operational path.

## Tests

On Unix, spawn the binary with raw-byte `OsString` arguments containing `0xff` in:

- mountpoint;
- lowerdir;
- upperdir;
- workdir.

At minimum, assert argument parsing/open reaches the normal filesystem operation rather than panicking. Mounted integration should use actual directories with those raw names and verify file access.

Keep a textual invalid option control to show non-path grammar errors still return ordinary diagnostics.

No upstream contact is authorized or made.
