# Cloud Hypervisor — AArch64 cacheinfo index portability

Updated: 2026-08-10
State: ACTIVE BASELINE / DESIGN BOUNDARY MAPPED
Owning issue: #541
Canonical Cloud Hypervisor source: `a1fcb9f790616ac615f66de73be540b0b20844b1`
Controlled carrier: `teamleaderleo/cloud-hypervisor#7`
External-contact state: `false; none occurred`

## TL;DR

Cloud Hypervisor currently identifies AArch64 host caches by fixed sysfs directory number: `index0=L1D`, `index1=L1I`, `index2=L2`, `index3=L3`. Linux ARM64 assigns those indices by **cache leaf discovery order**, not by architectural level number. A split cache level contributes Data then Instruction leaves; a unified level contributes one leaf; firmware-described external levels can add more unified leaves.

The fixed mapping therefore works for the common split-L1 plus unified-L2/L3 topology but can label valid host cache bytes as the wrong guest cache level/type on unified-L1 or split-higher-level layouts.

The current Cloud Hypervisor guest representation is itself narrower: both AArch64 FDT and PPTT assume split L1 Data/Instruction and unified L2/L3. The preferred first correction is therefore identity-aware discovery plus **cache-topology omission for valid layouts the current guest model cannot faithfully represent**, rather than merely replacing fixed indices with `(level,type)` lookup and forcing unsupported leaves into the existing fields.

## Explain like I'm five

Linux gives each discovered cache leaf the next `indexN` number. Two separate L1 caches consume two numbers; one unified L1 consumes one. Cloud Hypervisor currently treats the number itself as the cache name.

So on one host, `index1` can mean L1 Instruction. On another valid host, `index1` can mean L2 Unified. Current Cloud Hypervisor would still put the second host's `index1` bytes into its `l1_i_*` fields.

## Why care

This is a wrong-topology failure. The values can be perfectly valid and readable while their identity is wrong. FDT or PPTT can then describe host L2 bytes as guest L1I, or host L2 Instruction bytes as guest L3.

Cache topology is optional today: both consumers already have cache-less behavior. That gives a bounded correctness option for unsupported valid layouts—omit optional cache topology instead of fabricating a representable-looking but incorrect hierarchy.

## Exact source ownership

Cloud Hypervisor:

- `arch/src/aarch64/cache.rs` — fixed `CacheLevel` to `indexN` lookup and `CacheTopologyInfo` fields;
- `arch/src/aarch64/fdt.rs` — guest device-tree cache nodes; split L1 instruction/data, unified L2/L3;
- `vmm/src/cpu.rs` — ACPI PPTT cache nodes; L1 Data/Instruction and L2/L3 Unified.

The saturated #8097 candidate in #499 deliberately preserved fixed index identity while repairing runtime error propagation. This investigation is a separate successor.

Linux source reviewed at `torvalds/linux` commit `db2ddb87143519e20a95aa36c60b36107b736a58`:

- `arch/arm64/kernel/cacheinfo.c` walks architectural cache levels and advances a leaf index;
- `CACHE_TYPE_SEPARATE` contributes Data then Instruction leaves;
- other cache types contribute one leaf;
- firmware-described external levels may add unified leaves.

That is the source contract that defeats a universal fixed-index mapping.

## Historical intent evidence

Cloud Hypervisor PR #5505 introduced AArch64 cache passthrough in 2023. Its review contains an Ampere Altra host example with `index0`, `index1`, and `index2`, matching a split-L1 plus L2 control layout. The fixed mapping persisted through later cache-sharing and PPTT refactors.

The history establishes a real happy-path host. It does not establish an ARM64 rule that index number encodes level/type.

## First distinguishing probe

Controlled fork PR `teamleaderleo/cloud-hypervisor#7` stacks the exact validated #8666 and #8097 candidates, commits those prerequisites locally, and injects test-only identity fixtures into `arch/src/aarch64/cache.rs`.

### Control

```text
index0: level=1 type=Data
index1: level=1 type=Instruction
index2: level=2 type=Unified
index3: level=3 type=Unified
```

Expected: current fixed mapping agrees with sysfs identity.

### Unified-L1 counterexample

```text
index0: level=1 type=Unified
index1: level=2 type=Unified
index2: level=3 type=Unified
```

Current mechanism predicts:

- `l1_i_cache_size` receives index1 bytes whose sysfs identity says L2 Unified;
- `l2_cache_size` receives index2 bytes whose identity says L3 Unified;
- `l3_cache_size` is empty.

### Split-L2 counterexample

```text
index0: level=1 type=Data
index1: level=1 type=Instruction
index2: level=2 type=Data
index3: level=2 type=Instruction
index4: level=3 type=Unified
```

Current mechanism predicts:

- `l2_cache_size` receives L2 Data bytes while the guest model labels L2 Unified;
- `l3_cache_size` receives L2 Instruction bytes;
- actual L3 at index4 is ignored.

A passing counterexample test records the mismatch; it is not a fix.

## Preferred first product boundary after baseline

Discover cache leaves from sysfs `level` and `type`, then classify whether the host layout is representable by the current guest model.

### Representable

Map exactly the identities the current FDT/PPTT code knows how to describe:

- one L1 Data leaf;
- one L1 Instruction leaf;
- zero or one L2 Unified leaf;
- zero or one L3 Unified leaf.

Additional levels above L3 can be ignored after identity-aware discovery because they no longer shift L1-L3 identity.

For recognized leaves, retain #8097's property policy: missing optional scalar values stay zero/false; malformed-present values remain errors.

### Valid but unrepresentable

Examples include:

- L1 Unified;
- split L2;
- split L3;
- duplicate/ambiguous represented identities.

Return the existing cache-less result and emit one high-signal warning. This prevents incorrect guest cache identity while preserving boot.

## Why start with omission

A fully generic cache-leaf model would require coordinated changes to `CacheTopologyInfo`, FDT node generation and links, PPTT cache node types/hierarchy, sharing representation, and guest-visible topology tests. That is a larger enhancement.

The first correctness patch can preserve current behavior byte-for-field on the known representable layout and replace incorrect topology with omitted optional topology on other valid layouts.

## Candidate discriminators after baseline

1. split-L1/unified-L2/L3 control remains equivalent;
2. unified L1 becomes cache-less rather than mislabelled;
3. split L2 becomes cache-less rather than mislabelled;
4. representable L1-L3 plus L4 keeps correct L1-L3 identity and ignores L4;
5. malformed `level` and malformed property data remain typed errors;
6. verify Linux visibility guarantees for `level` and `type` before deciding the missing-identity policy;
7. immediate clean fixture rerun.

## Evidence boundary

Source ownership and Linux enumeration semantics are established. The controlled test-only baseline carrier exists and has been repaired to format injected probe code with nightly rustfmt before its independent formatting check. The current exact execution receipt should be taken from the latest carrier run before promoting a product patch.

## Reopen / widen triggers

Move to a generic guest cache graph only if a concrete requirement demands faithful unified-L1/split-higher-level passthrough, or omission causes a demonstrated regression worse than the current wrong description.

## External-contact state

`false; none occurred`.
