# Cloud Hypervisor TDVF TDX-init host-range panic

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590M
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: PROVEN

## Result

Exact-current `Vm::init_tdx_memory()` panics when a TDVF section names a guest range that is not fully backed by one guest-memory region. The controlling boundary is the unconditional `unwrap()` on `virtio_devices::get_host_address_range()`.

A one-region 4 KiB fixture proved:

```text
valid: address=0x800 size=0x100 -> host pointer returned
invalid: address=0xf80 size=0x100 -> get_host_address_range() returns None
baseline: unwrap(None) panics
```

Hosted baseline witness:

```text
called `Option::unwrap()` on a `None` value
TDVF_INIT_HOST_RANGE_BASELINE panicked=true
```

The paired normal invariant lost with exit code 101, as expected.

## Minimum validated candidate

The candidate changes only the VMM error boundary:

1. add `Error::InvalidTdxMemoryRange { address, size }`;
2. add `Vm::tdx_host_address_range()` to convert the existing helper's `None` into that typed error;
3. replace only the production `get_host_address_range(...).unwrap()` with the helper + `?`;
4. retain the same host pointer for a valid range.

Focused result:

```text
TDVF_INIT_HOST_RANGE_CANDIDATE invalid_result=InvalidTdxMemoryRange { address: 3968, size: 256 }
TDVF_INIT_HOST_RANGE_CANDIDATE control expected=<ptr> actual=<same ptr>
```

No parser policy, memory-allocation policy, TDVF section semantics, or hypervisor API behavior is changed.

## Validation receipt

Fieldwork tested head:

`2b0a437e55413b49f6ae0b0ab4c7c6758b52ea79`

Hosted Actions:

- run: `31595790732`
- job: `94110847428`
- conclusion: success
- artifact: `9141025898`
- artifact digest: `sha256:7e5c61f961f6e42fe4142af0eee0a74dc1bdeb6a4452bdcf1355198238f395c5`

Candidate-only diff SHA-256:

`664af6fee4c247a9d4b09c07ae960367c9088f251d5fd243622993b78f7007f3`

All gates passed:

- exact source pin / clean tree;
- valid host-range baseline control;
- baseline cross-region panic witness;
- baseline no-panic invariant expected red;
- exact-source restoration;
- candidate typed error + valid-pointer focused regression;
- full `vmm` `tdx,kvm`: **105 passed / 0 failed**;
- Clippy with warnings denied except previously identified exact-current baseline classes;
- nightly rustfmt;
- `git diff --check`;
- complete candidate-only diff review.

## Remaining adjacent owners

Keep separate:

- BFV/CFV exact-read/short-source behavior;
- the earlier start-only boot-RAM allocation decision (`address_in_range` versus whole-range backing);
- Payload header/body I/O and payload guest-memory destination failures;
- parser and section-cardinality policy.

The record-only commit after this tested head is not a substitute for the tested carrier.
