# #8666 refinement status

The internal Cloud Hypervisor carrier keeps the previously validated `candidate.patch` and applies a tiny `comment.patch` immediately afterward. The refinement restores concise context beside the compile-time SRAT byte-size assertions:

```rust
// ACPI requires these SRAT structures to have fixed byte sizes.
const _: () = assert!(size_of::<MemoryAffinity>() == 40);
const _: () = assert!(size_of::<GenericInitiatorAffinity>() == 32);
```

Focused run `31359076345` validates the combined product. Formatting, the focused address helper test, Clippy, x86_64 KVM/MSHV, fw_cfg, TDX, and AArch64 KVM/MSHV compilation all pass.

For human upstream preparation, the two internal patch layers are intended to become one logical `vmm` commit. Cloud Hypervisor requires a `Signed-off-by` footer and recommends squashing review/refinement commits into the corresponding logical commit before submission.
