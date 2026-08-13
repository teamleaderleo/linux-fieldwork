# Cloud Hypervisor TDX direct-kernel + TDVF Payload destination composition

Updated: 2026-08-13
Owning issues: #654 (configuration regression) + #590 (TDVF Payload consumer)
Fieldwork base: `fee128d20bbcdc99bb62e75b3575247356d64a16`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: STAGED COMPOSITION

## Purpose

Issue #654 proved that current generic payload validation accidentally disables the documented TDX direct-kernel mode by rejecting `firmware + kernel` and deleting TDX cmdline. Its selected candidate restores that supported configuration while preserving non-TDX payload rules.

An earlier #590 lane independently proved that the TDVF `Payload` guest-memory copy panics on an invalid guest destination and that a tiny `LoadPayloadMemory(GuestMemoryError)` propagation candidate fixes the local consumer. That lane was originally recorded as negative for supported configuration because the #654 regression made `self.kernel` unreachable in validated TDX boot.

This composition answers the new question after #654 is repaired: do the immutable #654 validation candidate and the immutable #590 Payload destination candidate coexist cleanly, with the documented TDX configuration accepted and the now-reachable Payload guest-memory failure returning a typed error?

## Immutable layers

### #654 validation layer

Materializer source: tested final carrier `921b7ecd5ee25889000d1fcaabbcc578a4cbbc69`

Expected product-only diff SHA-256:

`0af9d875fd2b82099fe15f7f6a910d9500293990846bda6d677da1ea16b0da5e`

Touches only:

```text
vmm/src/config.rs
vmm/src/vm_config.rs
```

### #590 Payload destination layer

Materializer source: tested carrier `3b671c290a675d86f3c606f99185c5c94488fe77`

Expected `vmm/src/vm.rs` candidate-only diff SHA-256:

`298ac3ea1ce3062f3967880098d1ed142487a38bc90c64729ae6682289e13772`

It adds only a payload-specific guest-memory error and helper around the existing non-exact Payload body copy. It intentionally does not own payload header I/O or short-read semantics.

The layers are file-disjoint.

## Composition matrix

1. materialize #654 candidate and verify its exact two-file diff hash;
2. materialize #590 Payload destination candidate and verify its exact `vm.rs` diff hash;
3. apply the cleaned #654 validation probe;
4. prove TDX firmware+kernel validates and cmdline remains present;
5. prove non-TDX firmware+kernel remains rejected and non-TDX firmware+cmdline remains cleared;
6. run the #590 candidate's payload destination regression: invalid destination returns `LoadPayloadMemory(InvalidGuestAddress(...))`, valid 16-byte copy remains exact;
7. full VMM `tdx,kvm` library tests;
8. Clippy, nightly rustfmt, `git diff --check`;
9. capture complete stacked product diff plus separate immutable layer hashes.

## Stop condition

Do not reinterpret the old R590Q isolated run by itself as reachability proof. This stacked composition is the bridge from the proven #654 configuration repair to the separately proven #590 consumer repair.

Keep payload header exact-read/error handling as the next independent owner after this composition.
