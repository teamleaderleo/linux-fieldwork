# Sources — Cloud Hypervisor lifecycle scout

## Upstream source pin

Repository:
https://github.com/cloud-hypervisor/cloud-hypervisor

Exact `main` head inspected:

`a18a2b3f66f7a3cec7f62d07605945beda8eb5d3`

Primary current-source files:

- `virtio-devices/src/transport/pci_device.rs`
  - https://github.com/cloud-hypervisor/cloud-hypervisor/blob/a18a2b3f66f7a3cec7f62d07605945beda8eb5d3/virtio-devices/src/transport/pci_device.rs
- `vmm/src/device_manager.rs`
  - https://github.com/cloud-hypervisor/cloud-hypervisor/blob/a18a2b3f66f7a3cec7f62d07605945beda8eb5d3/vmm/src/device_manager.rs
- `virtio-devices/src/vdpa.rs`
  - https://github.com/cloud-hypervisor/cloud-hypervisor/blob/a18a2b3f66f7a3cec7f62d07605945beda8eb5d3/virtio-devices/src/vdpa.rs
- `cloud-hypervisor/tests/common/tests_wrappers.rs`
  - https://github.com/cloud-hypervisor/cloud-hypervisor/blob/a18a2b3f66f7a3cec7f62d07605945beda8eb5d3/cloud-hypervisor/tests/common/tests_wrappers.rs

## Upstream reports and review evidence

### Virtio-pci snapshot/restore panic

Issue:
https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8693

Closed fix attempt:
https://github.com/cloud-hypervisor/cloud-hypervisor/pull/8702

PR source boundary:

- base: `a1fcb9f790616ac615f66de73be540b0b20844b1`
- proposed head: `7a876a01c8bfbe33375fac2f55a29a9b8bf5e477`
- state observed: closed, unmerged

Important review evidence: maintainer Rob Bradford explicitly described the reported bug as genuine and said the needed product fix was simple, while rejecting the submitted patch package.

Evidence used from the proposed diff:

- the proposal guarded queue-index restore;
- it recognized the partially configured queue case;
- it changed repeated `used_idx()` reads into one read;
- it added tests whose guest RAM started away from address zero.

Selection in Fieldwork is based on current source semantics, not adoption of that closed patch.

### Hugepage-sensitive tests

Issue:
https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8620

Current source corroboration:

`_test_vdpa_block()` still passes:

`--memory size=512M,hugepages=on`

without an explicit hugepage size at the inspected head.

Issue-level environment claim retained for later execution: a host default hugepage size of 1 GiB makes 512 MiB fail alignment validation, while upstream CI's smaller default avoids the failure.

### vDPA hot-unplug

Issue:
https://github.com/cloud-hypervisor/cloud-hypervisor/issues/7785

Current source movement relevant to revalidation:

- `DeviceManager::remove_device()` resolves missing parent/BDF/device-handle state with typed errors;
- virtio removal checks an explicit `VirtioDeviceType` allowlist;
- vDPA exposes the backend's virtio device identifier through `device_type()`.

These facts make the historical panic report insufficient as current-main evidence without reproduction.

### ACPI error propagation

Upstream PR:
https://github.com/cloud-hypervisor/cloud-hypervisor/pull/8709

Observed upstream state on 2026-08-11:

- merged: yes
- upstream head: `e9c86bacee14a2fd6fe871dc678c6b3f1ac4012a`
- merge commit: `735d44f54e222475b2737ed9ca814f1769107cd9`
- merged at: 2026-08-10 15:41:12 UTC

Fieldwork record consulted:

`investigations/cloud-hypervisor-acpi-error-propagation/README.md`

Its disposition still said approved / CI / merge pending when this round began.

## Broader context inspected but not promoted

Open Cloud Hypervisor threads reviewed during orientation included:

- differential snapshots: https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8645
- external userfaultfd memory source: https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8554
- userfaultfd handoff to external manager: https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8644
- live migration with virtio-net FDs: https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8566
- first-class FD support: https://github.com/cloud-hypervisor/cloud-hypervisor/issues/7704
- vsock behavior after restore: https://github.com/cloud-hypervisor/cloud-hypervisor/issues/7263
- snapshot/restore and migration offload: https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8277
- guest memory range query/export APIs: https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8003

These are context, not findings proven by this round.

## Fieldwork process sources consulted

- `AGENTS.md`
- `README.md`
- `START_HERE.md`
- `ADAPTIVE_COORDINATION.md`
- `FIELD_GUIDE.md`
- `SOURCE_BRANCH_HYGIENE.md`
- `research/README.md`
- `notes/research-benders-need-discriminators-and-stop-rules.md`
- `CURRENT_FIELDWORK.md`
- existing Cloud Hypervisor ACPI and AArch64 cache investigations

## Evidence boundary

This round used repository source, issue state, PR state/diff/review, and Fieldwork records. It did not execute Cloud Hypervisor, create a product branch, run CI, or contact upstream.
