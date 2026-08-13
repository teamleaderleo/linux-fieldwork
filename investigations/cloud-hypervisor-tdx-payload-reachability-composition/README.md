# Cloud Hypervisor TDX direct-kernel + TDVF Payload destination composition

Updated: 2026-08-13
Owning issues: #654 (configuration regression) + #590 (TDVF Payload consumer)
Fieldwork base: `fee128d20bbcdc99bb62e75b3575247356d64a16`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Tested Fieldwork head: `4aada13523c840556bbe96453d6e83f354eca4be`
External-contact state: false; upstream remains read-only
State: **COMPOSITION PROVEN**

## Result

The immutable #654 TDX-aware payload-validation repair and the immutable #590 TDVF `Payload` guest-memory-destination repair compose cleanly on exact source.

The composition proves the reachability bridge that the earlier isolated Payload lane lacked:

1. the documented TDX `firmware + kernel + cmdline` configuration validates after the #654 repair;
2. TDX cmdline remains present;
3. ordinary non-TDX firmware rules remain unchanged;
4. the now-supported-reachable TDVF `Payload` guest-memory failure returns a typed `LoadPayloadMemory(InvalidGuestAddress(...))` rather than panicking;
5. a valid Payload copy preserves the exact 16 bytes and copy count.

This does not merge ownership. #654 remains the configuration-regression owner; #590 remains the TDVF consumer-robustness owner.

## Immutable layers

### #654 validation layer

Materializer source: tested final carrier `921b7ecd5ee25889000d1fcaabbcc578a4cbbc69`

Expected and reverified product-only diff SHA-256:

`0af9d875fd2b82099fe15f7f6a910d9500293990846bda6d677da1ea16b0da5e`

Touches only:

```text
vmm/src/config.rs
vmm/src/vm_config.rs
```

### #590 Payload destination layer

Materializer source: tested carrier `3b671c290a675d86f3c606f99185c5c94488fe77`

Expected and reverified `vmm/src/vm.rs` candidate-only diff SHA-256:

`298ac3ea1ce3062f3967880098d1ed142487a38bc90c64729ae6682289e13772`

It adds only a payload-specific guest-memory error and helper around the existing non-exact Payload body copy. It does not own payload-header I/O or successful short-read semantics.

The two layers are file-disjoint.

## Authoritative execution

Hosted run:

- run `31665621908`
- job `94339438732`
- tested Fieldwork head `4aada13523c840556bbe96453d6e83f354eca4be`
- artifact `9167838191`
- artifact digest `sha256:9aacd153a09759039127b80647145113cb01db16bdff8dd51de893c34ba67225`
- combined stacked product diff SHA-256 `4fc25c98a076ac4273657d25e1c33b2b09cd361641a29d5e01caccee44a51c45`

Combined product stat:

```text
3 files changed, 79 insertions(+), 12 deletions(-)
```

Product files:

```text
vmm/src/config.rs
vmm/src/vm_config.rs
vmm/src/vm.rs
```

## Focused matrix

The workflow first materialized each immutable layer independently and failed closed unless its exact expected hash matched.

Then the stacked tests proved:

```text
TDX firmware + kernel validation: success
TDX cmdline preserved: Some("console=hvc0 root=/dev/vda")
non-TDX firmware + kernel: still FirmwarePlusOtherPayloads
non-TDX firmware + cmdline: still cleared
Payload invalid destination: LoadPayloadMemory(InvalidGuestAddress(GuestAddress(8192)))
Payload valid copy: copied=16 with exact 0x6b bytes
```

## Broad and quality gates

```text
full VMM tdx,kvm: 109 passed, 0 failed, 2 intentionally ignored baseline witnesses
Clippy: success
nightly rustfmt: success
git diff --check: success
```

The complete stacked product diff was reviewed. It contains exactly the already-tested #654 configuration semantics plus the already-tested #590 Payload guest-memory propagation semantics. No cross-layer semantic drift was found.

## Disposition

**COMPOSITION PROVEN.** The #654 validation repair restores the supported TDX direct-kernel path, and the separate #590 Payload destination repair remains valid and necessary once that path is reachable.

The earlier isolated R590Q record remains valid as historical evidence: exact-current configuration made the branch unreachable. This composition is the required bridge showing reachability and repair after #654 is applied; do not rewrite the old run as if it had proven supported reachability on unmodified source.

## Next independent owner

TDX `Payload` setup-header I/O remains separate. After the #654 layer restores `self.kernel`, an ordinary directory used as the kernel path can be opened and sought, then return a volatile read error that current source unwraps. That read-error propagation should be executed independently before any exact-read/short-header change.
