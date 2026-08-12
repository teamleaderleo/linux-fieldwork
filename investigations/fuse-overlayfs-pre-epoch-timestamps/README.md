# fuse-overlayfs Rust rewrite breaks pre-epoch timestamps

Date: 2026-08-12

## TL;DR

The current Rust implementation of fuse-overlayfs does not preserve valid POSIX timestamps before 1970.

At exact reviewed head `containers/fuse-overlayfs@67f5c128a94e93a41799d3fe6f624e6cb2522117`, there are two independent failure directions in `src/overlay.rs`:

1. **stat -> FUSE attributes can panic the daemon.** `stat_to_attr()` casts signed `st_atime`, `st_mtime`, and `st_ctime` seconds to `u64`, then computes `UNIX_EPOCH + Duration`. A value such as `-1` becomes `u64::MAX`. Rust's Unix `SystemTime` uses a signed `i64`-second timespec, and `SystemTime + Duration` panics when `checked_add()` cannot represent the result.
2. **FUSE setattr -> timespec silently rewrites pre-epoch times to the Unix epoch.** `TimeOrNow::SpecificTime(t)` calls `t.duration_since(UNIX_EPOCH).unwrap_or_default()`. For every `SystemTime` before the epoch, `duration_since()` returns `Err`, so the default duration is zero and `futimens()`/`utimensat()` receives `(0, 0)`.

The pre-Rust C implementation preserved signed timespecs directly in both directions. Both bad Rust conversions are present in the May 2026 rewrite commit, making this a Rust rewrite regression rather than an inherited limitation.

The repository's own `AGENTS.md` says the daemon must never panic and errors must not be handled via `unwrap()`, `expect()`, or `panic!()` in request processing. The read-side behavior therefore violates an explicit project reliability rule as well as timestamp semantics.

No upstream contact is authorized or has been made.

## Source boundary

Project: `containers/fuse-overlayfs`

Current reviewed head:

`67f5c128a94e93a41799d3fe6f624e6cb2522117`

Rust rewrite introduction:

`71269043450580a03751a72fc8e0b2b827f865b3` — `fuse-overlayfs: rewrite in Rust`

Pre-rewrite C control:

`1f6081548c8023cbbd3f85bf1038d8f73208369f`

## Read-side crash path

Current `stat_to_attr()` contains:

```rust
atime: UNIX_EPOCH + Duration::new(st.st_atime as u64, st.st_atime_nsec as u32),
mtime: UNIX_EPOCH + Duration::new(st.st_mtime as u64, st.st_mtime_nsec as u32),
ctime: UNIX_EPOCH + Duration::new(st.st_ctime as u64, st.st_ctime_nsec as u32),
```

For a normalized POSIX timestamp one second before the epoch:

```text
tv_sec = -1
(-1_i64 as u64) = 18446744073709551615
```

Rust's Unix `SystemTime` representation stores a signed `i64` second field. The standard library implementation of `Add<Duration> for SystemTime` is:

```rust
self.checked_add(dur)
    .expect("overflow when adding duration to `SystemTime`")
```

So adding `u64::MAX` seconds to the epoch cannot be represented and takes the panic path.

This helper is reached by ordinary filesystem operations, including lookup and getattr, as well as attribute generation for directory entries/readdir-plus and newly created entries. It is therefore request-path availability impact, not startup-only code.

## Setter corruption path

Current setattr conversion contains the same logic for atime and mtime:

```rust
TimeOrNow::SpecificTime(t) => {
    let d = t.duration_since(UNIX_EPOCH).unwrap_or_default();
    times[N] = libc::timespec {
        tv_sec: d.as_secs() as _,
        tv_nsec: d.subsec_nanos() as _,
    };
}
```

For a pre-epoch `SystemTime`, `duration_since(UNIX_EPOCH)` returns an error containing the magnitude before the epoch. `unwrap_or_default()` throws that magnitude away and substitutes `Duration::ZERO`, so every such request becomes:

```text
tv_sec = 0
tv_nsec = 0
```

This affects both atime and mtime.

## Pre-Rust control

The old C implementation did not convert signed timestamps through an unsigned epoch duration.

For copy/metadata preservation it copied the native values directly:

```c
times[0] = st.st_atim;
times[1] = st.st_mtim;
```

For setattr it likewise assigned the FUSE-provided signed timespec directly:

```c
if (to_set & FUSE_SET_ATTR_ATIME)
    times[0] = attr->st_atim;
...
if (to_set & FUSE_SET_ATTR_MTIME)
    times[1] = attr->st_mtim;
```

The C request/reply path used `struct stat`, whose timespec seconds remain signed.

## Introduction boundary

The Rust rewrite commit `71269043450580a03751a72fc8e0b2b827f865b3` already contains both current defects:

- `stat_to_attr()` casts signed stat seconds to `u64` before adding them to `UNIX_EPOCH`;
- `setattr()` uses `duration_since(UNIX_EPOCH).unwrap_or_default()` for specific atime/mtime.

This makes the rewrite commit the exact demonstrated introduction boundary for the regression.

## Ordinary filesystem control

A local disposable filesystem probe succeeded in storing and reading negative timestamps on an ordinary temporary file:

```text
atime_ns -500000000 mtime_ns -500000000
atime_ns2 -1000000000 mtime_ns2 -1000000000
```

So the trigger does not require malformed metadata. A lower layer can legally contain a file whose timestamp is before 1970.

The tracked `repro.py` repeats this control and models both current conversion boundaries.

## fuser precedent

The `fuser` library used by fuse-overlayfs has its own internal signed time utilities. Current `fuser/src/time.rs` explicitly:

- converts `SystemTime` before the epoch to negative `(seconds, nanoseconds)` timespec form;
- converts negative timespec seconds back to `SystemTime`;
- tests negative fractional values such as `(-1, 500_000_000)` and round-trips values down to the `i64::MIN` boundary.

Those helpers are crate-private, so fuse-overlayfs cannot simply call them, but they provide a strong semantic reference for the candidate.

## Candidate

Tracked candidate: `candidate.patch`.

It adds signed conversion helpers equivalent to POSIX/fuser timespec semantics:

- stat seconds >= 0: epoch plus duration;
- negative whole seconds: epoch minus magnitude;
- negative fractional times: account for normalized timespec representation (`-1, 500ms` means `-0.5s`, not `-1.5s`);
- SystemTime -> timespec preserves the magnitude returned by `SystemTimeError` instead of replacing it with zero.

It then uses those helpers for atime/mtime/ctime output and atime/mtime setattr input.

The candidate is intentionally local to timestamp conversion. It does not change copy-up policy, caching, uid/gid mapping, or FUSE timeout behavior.

## Reduced discriminator

`repro.py` models the key boundaries and performs a real temporary-file negative-timestamp control.

Representative expectations:

```text
read (-1,0): as_u64=18446744073709551615 fits_unix_SystemTime_i64=False
set  (-1,0): current=(0, 0)
read (-1,500000000): as_u64=18446744073709551615 fits_unix_SystemTime_i64=False
set  (-1,500000000): current=(0, 0)
candidate -0.5s normalized: (-1, 500000000)
candidate -1.2s normalized: (-2, 800000000)
filesystem control -0.5s: -500000000 -500000000
filesystem control -1s: -1000000000 -1000000000
```

The local environment does not have `rustc`, so this pass does not claim an exact-head compiled panic reproduction. The panic boundary instead rests on current fuse-overlayfs source plus Rust standard-library source showing Unix `SystemTime` uses signed seconds and `Add<Duration>` panics on unrepresentable addition.

## Test gap

Current repository search found no test covering `1969`, negative timestamps, pre-epoch times, or equivalent negative `utime` behavior.

A focused regression should cover at least:

1. lower-layer mtime/atime `-1s` and `-0.5s`, then stat through mounted fuse-overlayfs without daemon termination;
2. setattr/`touch` of a mounted file to `-1s` and `-0.5s`, then verify the upper backing file preserves the same normalized timespec;
3. a positive timestamp control;
4. negative fractional round-trip because `(-1, 500_000_000)` is exactly half a second before the epoch.

## Duplicate search

Open and closed upstream issue searches for combinations of negative timestamp, pre-epoch, 1969, Rust, and panic returned no matching report during this pass.

## Evidence boundary

Demonstrated:

- exact current read conversion casts signed stat seconds to u64;
- Rust Unix `SystemTime` is signed-i64 timespec based and `Add<Duration>` panics when checked addition fails;
- `stat_to_attr()` is reached from normal lookup/getattr and other request paths;
- exact current setter converts all pre-epoch specific times to zero duration;
- both bad conversions are already present in the May 2026 Rust rewrite;
- pre-rewrite C preserved signed timespecs directly;
- ordinary local filesystem metadata supports negative timestamps;
- fuser's own time utility defines and tests the correct signed semantics;
- no matching upstream issue or current negative-time test was found.

Not yet demonstrated:

- exact-head compiled fuse-overlayfs daemon panic in this environment (Rust compiler unavailable locally);
- full mounted integration with the candidate;
- behavior on platforms whose `SystemTime` range differs from Linux/Unix. The project under investigation is Linux-oriented and current Rust Unix representation was checked.

## Cleanup

The local prevalence probe created only a temporary regular file under `/tmp`, changed its atime/mtime, statted it, and removed it. No mount, namespace, device, or persistent host state remained.

## Current disposition

State: `EXECUTING`

Next safe actions:

1. look for an owned fuse-overlayfs fork or a way to compile the exact source through connected CI without contacting upstream;
2. inspect adjacent Rust-rewrite signedness conversions (`off_t`, device IDs, timestamps in copy-up/statx) for similar C-to-Rust semantic drift;
3. retain the no-panic rule as a strong review gate, but do not promote impossible/test-only unwraps.

External-contact state: no upstream interaction authorized or made.
