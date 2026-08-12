# Cloud Hypervisor TDVF TDX-init host-range panic

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590M
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: STAGED

## Narrow question

When `init_tdx_memory()` processes a TDVF section whose declared guest range is not fully backed by one guest-memory region, does exact-current Cloud Hypervisor panic at `get_host_address_range(...).unwrap()`? Can the minimum VMM-side repair preserve the valid host pointer while returning a typed error for the unbacked/cross-region range before any TDX hypervisor call?

## Exact source owner

Current `Vm::init_tdx_memory()` obtains the guest-memory map and for every TDVF section executes:

```rust
let size = section.size.try_into().unwrap();
self.vm.tdx_init_memory_region(
    virtio_devices::get_host_address_range(
        &*mem,
        GuestAddress(section.address),
        size,
    )
    .unwrap(),
    section.address,
    size,
    section.attributes == 1,
)
```

On x86_64 the `u64 -> usize` conversion is not the controlling edge. The meaningful boundary is `get_host_address_range(...).unwrap()`.

`virtio_devices::get_host_address_range()` explicitly returns `None` if the requested range is out of bounds, spans multiple regions, or has zero size at an unmapped GPA. The VMM currently turns that ordinary invalid-range result into a panic.

## Baseline discriminator

Use a single 4 KiB `GuestMemoryMmap` at GPA `0`:

- valid control: address `0x800`, size `0x100` -> helper returns `Some(host_ptr)`;
- ignored witness: address `0xf80`, size `0x100` crosses the end of the only region -> helper returns `None`, current `.unwrap()` panics;
- normal expected-red invariant: same invalid range must not panic.

This exercises the exact range helper and unwrap contract without requiring TDX hardware.

## Minimum candidate

1. add typed `Error::InvalidTdxMemoryRange { address: u64, size: usize }`;
2. add a tiny production helper wrapping `get_host_address_range()` and converting `None` to that error;
3. call the helper with `?` from `init_tdx_memory()` before `tdx_init_memory_region()`;
4. focused regression proves invalid cross-boundary range returns the typed error and the valid range returns the same host pointer as the underlying helper.

The candidate does not add parser-level layout policy, change guest-memory allocation, alter TDVF section semantics, or call the hypervisor in the focused test.

## Gates

- exact source pin and clean tree;
- baseline valid host-range control green;
- baseline invalid-range panic witness green;
- baseline no-panic invariant expected red;
- restore exact source before candidate;
- candidate typed invalid-range + valid pointer control green;
- full `vmm` library tests with `tdx,kvm` and `/dev/kvm` permissions repaired when present;
- Clippy with warnings denied except already identified exact-current unrelated baseline classes;
- nightly rustfmt and `git diff --check`;
- complete candidate-only diff review and SHA-256 receipt.

## Split boundaries

Keep separate:

- BFV/CFV source-file ranges and short reads;
- BFV/CFV or PayloadParam copy/write errors;
- Payload section header/body I/O;
- parser type/GUID/section-table validity;
- section-overlap/cardinality policy.
