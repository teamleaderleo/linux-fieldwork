# KVM dirty-log dependency contract

Updated: 2026-08-12
Owning issue: #617
Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Pinned `kvm-ioctls`: `0.25.0`
External-contact state: `false; none occurred`

## Why this check exists

Repair v2 rejects a backend dirty bitmap whose `Vec<u64>` word count differs from the exact count required to cover the registered memory region at the reported byte granularity. That check must agree with `kvm-ioctls::VmFd::get_dirty_log()` or it would reject a valid KVM result.

## `kvm-ioctls 0.25.0`

The pinned implementation obtains `_SC_PAGESIZE`, treats `-1` as an error, converts the page size to `usize`, and allocates:

```text
bitmap_size = memory_size.div_ceil(page_size * 64)
bitmap = vec![0u64; bitmap_size]
```

It then issues `KVM_GET_DIRTY_LOG` into that buffer and returns the vector unchanged.

For a Cloud Hypervisor RAM mapping whose size is aligned to the dirty-log page granularity, repair v2 computes:

```text
page_count = memory_size / bytes_per_bit
expected_words = ceil(page_count / 64)
```

With `bytes_per_bit == page_size`, these formulas are equivalent:

```text
ceil(memory_size / (page_size * 64))
== ceil((memory_size / page_size) / 64)
```

Therefore exact word-count equality is compatible with the pinned KVM userspace API. It catches VMM/backend coverage drift without narrowing the valid `kvm-ioctls` bitmap format.

The dependency implementation also reinforces repair v2's checked page-size policy: `_SC_PAGESIZE == -1` is an error condition and should never be converted to an unsigned page size.

## Review consequence

Keep the exact backend/VMM word-count check in repair v2. If Cloud Hypervisor later upgrades `kvm-ioctls` and its bitmap cardinality contract changes, refresh this record and the corresponding unit discriminator before carrying the invariant forward.
