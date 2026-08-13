# Cloud Hypervisor migration table aligned-capacity review

Updated: 2026-08-13
State: EXECUTED — PANIC PROVEN; FINAL PARSER BOUNDARY RESOLVED
Variant: LF-R637
Canonical issue: #637
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Internal #604 candidate head: `a9ff8e0ca603f72e6fb718fc023b679201ce04c5`
External-contact state: false; upstream remained read-only

## Result

A syntactically aligned peer-provided `MemoryRangeTable` length can panic the receiver during vector capacity construction, both on exact current source and after the narrow #604 unaligned-length candidate. The parser-local repair is now bounded: keep #604's checked integer/alignment validation and add fallible vector reservation. Do **not** add an arbitrary table-size cap to `MemoryRangeTable::read_from()`.

## Baseline result

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

## Final parser boundary

The parser should do exactly four things before reading the table bytes:

```text
checked u64 -> usize length
-> reject non-MemoryRange-aligned length with MigrateReceive
-> compute entry count
-> fallibly reserve that many MemoryRange entries
```

After a successful reservation it may resize the vector and keep the existing `read_exact()` behavior.

This closes the demonstrated panic classes at this parser boundary:

1. integer conversion failure;
2. malformed record alignment;
3. impossible vector capacity/allocation.

## Why there is no parser magic limit

Current migration protocol does not define a maximum `MemoryRangeTable` count. `Request::memory(length)` carries a `u64` payload length, and `MemoryRangeTable::read_from()` receives only that byte length plus a reader. It does not know guest RAM size, migration mode, connection count, or another semantic bound that would justify a universal limit.

The sender's multi-connection implementation uses a 64 MiB memory-content chunk size, but that is a VMM transport/backpressure choice. The single-connection path can send a full range table directly. Reusing 64 MiB as a parser table limit would therefore turn one implementation detail into a new protocol restriction without evidence.

A large but representable peer request can still consume memory before payload read. That is a separate resource-policy question. If Cloud Hypervisor wants such a policy, enforce it where the receiver has enough VM/protocol context to derive a real bound; do not guess one inside the generic table parser.

## Recommended source packet

Fold this containment into the existing #604 one-file candidate rather than create a second source patch. Final scope remains:

```text
vm-migration/src/protocol.rs
```

Regression set:

- `length = 1` returns `MigrateReceive` rather than panicking;
- aligned impossible capacity returns `MigrateReceive` rather than panicking;
- zero length remains valid;
- one complete record round-trips normally.

Disposition: **NARROWED / READY TO REBUILD WITH #604**.
