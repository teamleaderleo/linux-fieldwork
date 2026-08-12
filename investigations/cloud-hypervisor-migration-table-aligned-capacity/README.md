# Cloud Hypervisor migration table aligned-capacity review

Updated: 2026-08-12
State: EXECUTED — PROVEN DISTINCT FROM #604
Variant: LF-R637
Canonical issue: #637
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Internal #604 candidate head: `a9ff8e0ca603f72e6fb718fc023b679201ce04c5`
External-contact state: false; upstream remained read-only

## Result

A syntactically aligned peer-provided `MemoryRangeTable` length can still panic the receiver during vector capacity construction, both on exact current source and after the narrow #604 unaligned-length candidate.

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

## Interpretation

#604 correctly converts malformed unaligned framing into `MigratableError::MigrateReceive`, but it does not make the same peer-controlled parser boundary panic-free for aligned impossible sizes.

A complete resource-bound review has two layers:

1. impossible capacity/allocation requests must be handled fallibly rather than panic/abort;
2. a semantic receiver/protocol upper bound should prevent a peer from requesting unreasonable pre-payload memory even when allocation is technically representable.

`Vec::try_reserve` alone is therefore useful containment but not obviously the full input-policy repair.

## Next design question

Find the narrowest trustworthy upper bound. Prefer one derived from destination memory/protocol state over an arbitrary constant. If `MemoryRangeTable::read_from()` cannot know that state, keep generic fallible allocation in the parser and enforce the semantic bound at the receive caller before allocation.
