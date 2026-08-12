# fuse-overlayfs Rust rewrite requires UTF-8 command-line paths

Date: 2026-08-12

## TL;DR

The current Rust implementation cannot safely accept arbitrary Linux path bytes on its command line.

At exact reviewed head `containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117`, `main()` starts with:

```rust
let args: Vec<String> = std::env::args().collect();
```

Rust's standard library implements `env::args()` by converting each OS argument with `into_string().unwrap()` and explicitly documents that iteration panics if any process argument is not valid Unicode.

`OverlayConfig` then stores `lowerdir`, `upperdir`, `workdir`, and `mountpoint` as `Option<String>`, and its parser operates entirely on `String`/`str`.

Linux pathnames are byte strings, not UTF-8 strings. A local filesystem control successfully created, statted, listed, and removed a directory whose final component contained raw byte `0xff`.

The pre-Rust C implementation received ordinary `char **argv` and path option values as C byte strings; it did not impose a Unicode validity gate. The `env::args()` / String-only config is present in the May 2026 Rust rewrite, making this a rewrite compatibility regression and a direct conflict with the repository's rule that the FUSE daemon must never panic.

No upstream contact is authorized or has been made.

## Exact current boundary

Current `src/main.rs`:

```rust
fn main() {
    let args: Vec<String> = std::env::args().collect();
    let config = config::parse_args(&args) ...;
```

The panic occurs while collecting arguments, before fuse-overlayfs has a chance to return its own parse error or mount diagnostic.

Current `OverlayConfig` path fields are:

```rust
pub lowerdir: Option<String>,
pub upperdir: Option<String>,
pub workdir: Option<String>,
pub mountpoint: Option<String>,
```

and `parse_args(args: &[String])` / `parse_option_string(&str, ...)` require Unicode throughout the CLI grammar.

## Rust standard-library control

Current Rust std `env::Args` has:

```rust
fn next(&mut self) -> Option<String> {
    self.inner.next().map(|s| s.into_string().unwrap())
}
```

with a source comment stating that `env::args` promises to panic during iteration if any process argument is not valid Unicode.

`env::args_os()` is the non-panicking OS-native alternative.

## Linux path control

Tracked `repro.py` creates a directory with final component `b"\xff-layer"` and verifies raw-byte `mkdir`, `stat`, and `listdir` succeed.

Representative result:

```text
linux mkdir raw path: OK b'/tmp/.../\xff-layer'
linux stat raw path inode: <valid inode>
linux list raw: [b'\xff-layer']
current Rust argv gate: std::env::args String conversion would panic during iteration
```

This is ordinary pathname behavior, not malformed filesystem metadata.

## Pre-Rust control

The old implementation was a C program with `int main(int argc, char **argv)` and libfuse/fuse-opt parsing over `char *` option strings. Pathnames such as lowerdir/upperdir/workdir/mountpoint therefore remained byte C strings subject to the normal Linux NUL/path-length rules, not Unicode validation.

## Introduction boundary

Rust rewrite commit:

`71269043450580a03751a72fc8e0b2b827f865b3` — `fuse-overlayfs: rewrite in Rust`

Its initial `main.rs` already does:

```rust
let args: Vec<String> = std::env::args().collect();
```

and uses String-valued paths. The regression is therefore introduced by the rewrite itself.

## Secondary lossy conversion

Even after fixing the CLI entry point, current `sys::fs::realpath()` does:

```rust
CStr::from_ptr(real).to_string_lossy().into_owned()
```

and `DirectAccess.resolved_path` is a `String`.

That is a second byte-loss boundary for resolved layer paths (used at least for NFS file-handle probing). It should be repaired alongside or immediately after the CLI representation so byte-safe arguments are not later rewritten through replacement characters.

## Candidate design

See `CANDIDATE.md`.

Core repair:

- `env::args_os()`;
- OS-native path fields (`OsString`/`PathBuf`);
- byte-oriented ASCII parsing for `-o` so path values embedded in option strings stay raw;
- convert only genuinely textual/numeric option values to UTF-8;
- path-taking syscall/open helpers accept OS paths or byte slices;
- `realpath()` returns an OS-native/path representation rather than lossy String.

## Test design

On Unix, spawn fuse-overlayfs with raw byte `0xff` in each path class:

1. mountpoint;
2. lowerdir;
3. upperdir;
4. workdir.

The first regression gate is simply “does not panic during argv iteration.” A full integration should then mount and verify a file can be reached through those byte-named directories.

Keep normal UTF-8 controls and malformed textual/numeric option controls to ensure path byte-safety does not weaken option validation.

## Duplicate search

Open and closed upstream issue searches for non-UTF8/raw-byte CLI path behavior returned no matching report during this pass.

## Evidence boundary

Demonstrated:

- exact current entry point uses `env::args()` / `Vec<String>`;
- Rust std source shows invalid Unicode arguments panic during iteration;
- current config path representation is String-only;
- local Linux filesystem accepts a raw-byte `0xff` directory name;
- initial Rust rewrite already contains the String argv design;
- pre-Rust C path handling did not impose Unicode;
- current realpath has a second lossy Unicode conversion;
- no matching upstream issue was found.

Not yet demonstrated:

- exact-head spawned binary with a raw-byte argv in this local environment (no Rust build available);
- mounted integration using non-UTF8 lower/upper/work/mount paths;
- every helper/API change needed for a compile-tested byte-safe refactor.

## Cleanup

The local control created and removed one temporary byte-named directory. No mount, namespace, device, or persistent state remained.

## Current disposition

State: `EXECUTING`

Next safe actions:

1. compile/spawn the exact binary in owned CI if available with an `OsString` raw-byte argument;
2. audit environment-variable path handling (`FUSE_OVERLAYFS_DEBUG_LOG`) separately;
3. inspect all path helpers for lossy `to_str`/`to_string_lossy` conversions after config parsing.

External-contact state: no upstream interaction authorized or made.
