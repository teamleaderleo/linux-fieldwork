# Cloud Hypervisor migration table aligned-capacity review

Updated: 2026-08-12
State: EXECUTED — PANIC PROVEN; FALLIBLE ALLOCATION CONTAINMENT VERIFIED
Variant: LF-R637
Canonical issue: #637
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Internal #604 candidate head: `a9ff8e0ca603f72e6fb718fc023b679201ce04c5`
External-contact state: false; upstream remained read-only

## Baseline result

A syntactically aligned peer-provided `MemoryRangeTable` length can panic the receiver during vector capacity construction, both on exact current source and after the narrow #604 unaligned-length candidate.

Authoritative workflow:
- run: `31587683649`
- exact-current job: `94085212407`
- #604 candidate job: `94085212446`

The discriminator used `length = u64::MAX - 15 = 0xfffffffffffffff0`, divisible by the 16-byte `MemoryRange` record size. The value trips Rust's vector capacity guard before a giant allocation is attempted, so this is not an intentional OOM stress fixture.

Exact current:

```text
capacity overflow
ALIGNED_CAPACITY panic="capacity overflow" length=0xfffffffffffffff0
```

Artifact: `9137809923`
Digest: `sha256:b266bc17c0b2ae666a8dc27f4e16f4f9b26ffe9e4d18f3849c47598dbf76a67d`

Internal #604 candidate:

```text
capacity overflow
ALIGNED_CAPACITY_R604 panic="capacity overflow" length=0xfffffffffffffff0
```

Artifact: `9137807947`
Digest: `sha256:ae54ab57bff6429aac94c5338e794bfb93e15760d5fe3b5801a9b95b7e249d21`

## Fallible allocation containment

Run `31588477334`, job `94087705360` starts from clean #604 candidate `a9ff8e0c...` and replaces infallible vector construction with `try_reserve_exact(entries)` followed by resize.

Focused result:

```text
ALIGNED_CAPACITY_CONTAINED error=MigrateReceive(
  invalid memory range table length: cannot allocate 1152921504606846975 entries:
  memory allocation failed because the computed capacity exceeded the collection's maximum
) length=0xfffffffffffffff0
```

Gates:

```text
aligned capacity containment test        1 passed, 0 failed
#604 unaligned-length regression          PASS
cargo test --locked -p vm-migration      22 passed, 0 failed
cargo clippy --locked -p vm-migration --all-targets -- -D warnings  PASS
cargo fmt --all -- --check                PASS
git diff --check                          PASS
```

Artifact: `9138146113`
Digest: `sha256:6a0feefa9b90128a3426a2151547f01846942014bf80b99291d1100ba43f1883`

## Interpretation

#604 correctly converts malformed unaligned framing into `MigratableError::MigrateReceive`. Fallible reservation also converts impossible capacity/allocation requests into an ordinary migration error without panicking.

That is verified **panic containment**, not yet a complete resource policy. A syntactically valid and technically representable but merely huge table can still ask the receiver to reserve substantial memory before payload read.

Current repair layers:

1. alignment / integer conversion validation — verified;
2. fallible allocation — verified containment;
3. semantic maximum table size — unresolved.

## Next design question

Find the narrowest trustworthy upper bound. Prefer one derived from destination memory/protocol state over an arbitrary constant. If `MemoryRangeTable::read_from()` cannot know that state, keep generic fallible allocation in the parser and enforce the semantic bound at the receive caller before allocation.

Current sender review matters here: the multi-connection path partitions transfer payloads, but the single-connection path can send the full table directly, so a fixed per-chunk table bound cannot be assumed without changing current sender semantics.
