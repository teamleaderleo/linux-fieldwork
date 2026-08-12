# Candidate design: preserve readdir errors through the iterator stack

This investigation does not carry a pretend one-line patch because the current abstraction itself loses the error. A correct repair should change the contract at each layer.

## 1. sys::dir::DirStream

Change:

```rust
pub fn next_entry(&mut self) -> Option<RawDirEntry>
```

to:

```rust
pub fn next_entry(&mut self) -> FsResult<Option<RawDirEntry>>
```

Before calling libc `readdir()`, clear errno. If `readdir()` returns NULL:

- errno == 0 -> `Ok(None)` (real end-of-directory)
- errno != 0 -> `Err(FsError(errno))`

Using the portable `errno` crate is preferable to direct glibc-only `__errno_location()` access because fuse-overlayfs currently supports Linux libc variants including Android/bionic. The `errno` package is already present transitively in the dependency graph; making it a direct dependency would make this use explicit.

## 2. datasource::DirIterator

Change:

```rust
fn next_entry(&mut self) -> Option<DirEntry>;
```

to:

```rust
fn next_entry(&mut self) -> FsResult<Option<DirEntry>>;
```

This is the key semantic repair: EOF and error must be different values in the abstraction.

## 3. DirectDirIterator

Map the inner result rather than using `?` on an Option:

```rust
fn next_entry(&mut self) -> FsResult<Option<DirEntry>> {
    Ok(self.stream.next_entry()?.map(|raw| DirEntry {
        name: raw.name,
        ino: raw.ino,
        dtype: raw.dtype,
    }))
}
```

## 4. overlay directory loading

`load_dir_impl()` currently has no error return and unconditionally calls `mark_loaded()` after its layer loops. It should return an `FsResult` (or an equivalent status that preserves errno).

On iterator error:

- stop the scan;
- do **not** mark the parent directory loaded;
- propagate the error to the operation that required the exhaustive scan.

This matters because `DirState::loaded=true` is explicitly documented as meaning the children map is exhaustive. Keeping it false leaves missing names eligible for later lazy lookup/retry.

## 5. direct `empty_upper_dir()` use

That helper already returns `FsResult<()>`, so its direct `DirStream` loop can simply propagate `next_entry()?` errors rather than treating them as completion.

## 6. FUSE operation boundary

Operations that require an exhaustive directory image (readdir/readdirplus, emptiness checks, rename/rmdir preparation as applicable) should surface the backing scan error rather than emit a partial success.

Lazy single-name lookup can remain separate; the important invariant is that a failed exhaustive scan never flips `loaded=true`.

## Suggested tests

A deterministic unit/fake DataSource test is preferable to relying on real disk EIO:

1. fake iterator returns entry `a`;
2. next call returns `Err(EIO)`;
3. a later backing lookup can provide entry `b`.

Assertions:

- scan returns EIO;
- parent remains unloaded;
- `b` is not cached as permanent ENOENT;
- retry/lazy lookup can discover `b`.

Also test true EOF (`Ok(None)`) still marks the directory loaded.

No upstream contact is authorized or made.
