# fuse-overlayfs Rust rewrite turns readdir errors into EOF

Date: 2026-08-12

## TL;DR

The current Rust directory iterator cannot distinguish end-of-directory from a `readdir()` error.

At exact reviewed head `containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117`:

- `src/sys/dir.rs::DirStream::next_entry()` calls libc `readdir()` and returns `None` whenever it gets NULL, without clearing or checking errno;
- `datasource::DirIterator` exposes only `Option<DirEntry>`, so there is no error channel at all;
- `OverlayInner::load_dir_impl()` consumes `while let Some(entry) = dir.next_entry()`, then unconditionally calls `mark_loaded()`;
- `DirState::loaded=true` is explicitly documented as meaning the child map is exhaustive;
- once loaded, `do_lookup_file()` does not perform lazy backing lookup for a missing child.

Therefore a backing `readdir()` error after some entries can be converted into successful completion of a partial scan, cached as an exhaustive directory, and later missing names can become false ENOENT results rather than retrying the backing filesystem.

The pre-Rust C implementation explicitly cleared errno before `readdir()` and returned failure when NULL arrived with nonzero errno. The error/EOF collapse is present in the May 2026 Rust rewrite, making it a rewrite regression.

No upstream contact is authorized or has been made.

## Source boundary

Current reviewed head:

`containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117`

Rust rewrite introduction:

`71269043450580a03751a72fc8e0b2b827f865b3`

Pre-Rust C control:

`1f6081548c8023cbbd3f85bf1038d8f73208369f`

## Lowest-level loss

Current `src/sys/dir.rs`:

```rust
pub fn next_entry(&mut self) -> Option<RawDirEntry> {
    let entry = unsafe { libc::readdir(self.dir) };
    if entry.is_null() {
        return None;
    }
    ...
}
```

POSIX `readdir()` uses NULL for both EOF and error. Callers distinguish them by setting errno to zero before the call and checking errno after NULL.

Current code does neither.

## Abstraction-level loss

`src/datasource.rs` defines:

```rust
pub trait DirIterator: Send {
    /// Returns the next directory entry, or None when exhausted.
    fn next_entry(&mut self) -> Option<DirEntry>;
}
```

Even if `DirStream` started checking errno internally, this API cannot carry the resulting error to overlay code. The repair must therefore change the iterator contract, not just add a local check.

`DirectDirIterator` currently adapts the Option directly:

```rust
fn next_entry(&mut self) -> Option<DirEntry> {
    let raw = self.stream.next_entry()?;
    Some(...)
}
```

## Cached partial-directory consequence

`load_dir_impl()` opens each layer and loops:

```rust
while let Some(entry) = dir.next_entry() {
    ...
}
```

After all layer loops, regardless of why iteration stopped, it does:

```rust
if let Some(n) = self.nodes.get_mut(&parent_id) {
    n.mark_loaded();
}
```

`DirState` documents `loaded=true` as meaning the children map is exhaustive/fully scanned.

Later `do_lookup_file()` checks the cache first. If a name is not present:

```rust
if !loaded {
    self.do_lazy_lookup(...)
} else {
    None
}
```

So a hidden scan error changes future lookup semantics: names that were never reached can be treated as conclusively absent.

`reload_dir()` also returns `true` after calling the void `load_dir_impl()`, so its boolean result currently cannot represent a scan error either.

## Pre-Rust control

The old C implementation repeatedly used the correct distinction:

```c
errno = 0;
dent = readdir(dp);
if (dent == NULL) {
    if (errno)
        return -1;
    break;
}
```

The same pattern appears in multiple pre-Rust directory loops, including data-source iteration.

That establishes a prior error-ownership contract: EOF was success, directory-read failure was not.

## Introduction boundary

The Rust rewrite commit already contains:

- `DirStream::next_entry() -> Option<RawDirEntry>` with NULL -> None;
- `DirIterator::next_entry() -> Option<DirEntry>`.

The regression therefore enters with the May 2026 rewrite rather than a later rustix/Android change.

## Reduced discriminator

Tracked `repro.py` models a directory containing `a`, `b`, `c` where iteration returns `a` and then EIO before reaching `b`.

Current state machine:

```text
cached = [a]
iterator error -> None
scan loop ends
mark_loaded()
lookup b -> cached miss + loaded=true -> ENOENT
```

Candidate state machine:

```text
cached = [a]
iterator error -> Err(EIO)
parent remains loaded=false
operation reports/retries error
later lookup b remains eligible for backing lookup
```

The model does not claim to inject EIO into the exact binary; it isolates the cache/error ownership consequence that current type signatures make unavoidable when libc `readdir()` fails.

## Candidate design

See `CANDIDATE.md`.

Key contract changes:

1. `DirStream::next_entry() -> FsResult<Option<RawDirEntry>>`;
2. clear/read errno around libc `readdir()`;
3. `DirIterator::next_entry() -> FsResult<Option<DirEntry>>`;
4. propagate iterator failures through exhaustive directory scans;
5. never call `mark_loaded()` after a failed scan;
6. return the backing error from FUSE operations that required the exhaustive scan.

The fix should preserve already discovered entries but keep the node retryable/unloaded after failure.

## Test design

A fake iterator/DataSource is preferable to real disk failure injection:

- entry `a`;
- `Err(EIO)`;
- potential entry `b` on a later retry.

Required assertions:

- EIO is not translated to EOF;
- directory remains unloaded after the failed scan;
- true EOF still marks it loaded;
- missing `b` is not permanently cached as absent;
- direct helper paths such as `empty_upper_dir()` propagate iteration errors too.

## Duplicate/test search

Open and closed upstream issue searches for readdir error/partial directory/EIO behavior returned no matching report during this pass.

Current source search found ordinary readdir tests but no injected-error test covering NULL+errno or partial-scan cache state.

## Evidence boundary

Demonstrated:

- exact current `DirStream` collapses NULL into None without errno handling;
- DataSource iterator has no error representation;
- exhaustive overlay scan marks the directory loaded after Option iteration ends;
- loaded state disables lazy lookup on cache misses;
- pre-Rust C distinguished EOF from errno-backed failure;
- the bad API and sys wrapper are present at Rust rewrite introduction;
- no matching upstream issue/test was found.

Not yet demonstrated:

- exact-head mounted integration with injected `readdir()` EIO;
- frequency of real directory-read errors on ordinary local filesystems;
- the final compile-tested shape of the API-wide repair.

## Cleanup

No filesystem, mount, namespace, or device state was changed for this investigation.

## Current disposition

State: `EXECUTING`

Next safe actions:

1. build a fake DataSource test in an owned fork/CI if available;
2. inspect other Rust rewrite APIs whose `Option` return may have collapsed C errno-bearing results;
3. audit directory `opendir` failures that are currently ignored/continued in multi-layer scans separately from mid-stream `readdir` errors.

External-contact state: no upstream interaction authorized or made.
