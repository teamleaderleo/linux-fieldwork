# Cloud Hypervisor vDPA hot-unplug after the historical remove panic

## TL;DR

The canonical vDPA hot-unplug panic from Cloud Hypervisor issue 7785 is source-fixed on current `main`. The original crash was a classification mistake in `DeviceManager::remove_device()`: a vDPA NIC reports the virtio network device type, but its configuration lives in `VmConfig.vdpa`; v51.1 and v52.0 entered the ordinary `VirtioDeviceType::Net` cleanup arm and unconditionally unwrapped `config.net`.

Commit `5b53f4202d183c2f890d651b6281b66c1e6cd9fe` later made ordinary-net FD cleanup optional while moving authoritative device-config removal into `DeviceManager::remove_device()`. Current `VmConfig::remove_device()` explicitly removes matching IDs from `vdpa`, and current `eject_device()` has the generic virtio DMA/IOMMU/BAR/bus/shutdown cleanup needed after guest ejection.

No new source candidate is justified from the historical panic. One real vDPA current-main run remains the useful discriminator.

Tracking issue: [linux-fieldwork #571](https://github.com/teamleaderleo/linux-fieldwork/issues/571)  
Canonical report: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/7785

## Explain like I'm five

Cloud Hypervisor has two ways to get a network-looking virtio device here:

```text
ordinary virtio-net -> config.net
vDPA network       -> config.vdpa
```

The old removal code asked the device what virtio type it was. A vDPA NIC answered “network.” The code then assumed its configuration must live in `config.net` and unwrapped that list. A VM whose network device came from vDPA could therefore crash before ejection even started.

Current code treats the ordinary-net FD cleanup as optional and then asks `VmConfig` to remove the ID from the configuration list that actually owns it.

## Why care

The canonical issue remains open even though current source has outgrown the exact crash. A fresh patch against the old unwrap would duplicate an already-landed source correction. The useful remaining question is whether current generic virtio teardown works end to end on real vDPA hardware.

## Current state

- State: `SOURCE-FIXED / RUNTIME VERIFICATION PENDING`
- Exact canonical head inspected: `a658c9f9fd0c4e0363004361d73ac8733fa24fd0`
- Current `vmm/src/device_manager.rs` blob: `f980b44158461518b40bbd1ea209cdf7268b7d2e`
- Current `virtio-devices/src/vdpa.rs` blob: `f8644f820284682c94e7834882a70d3d8ee80317`
- Historical affected releases inspected: `v51.1`, `v52.0`
- Fixing commit for the exact unwrap path: `5b53f4202d183c2f890d651b6281b66c1e6cd9fe`
- Candidate source commit: none
- Cleanup state: no runtime state
- Next safe action: execute one current-main vDPA hot-unplug on real hardware and inspect teardown/repeat behavior
- External-contact state: `false; none occurred`

## Source boundary

Project: `cloud-hypervisor/cloud-hypervisor`

Current head:
`a658c9f9fd0c4e0363004361d73ac8733fa24fd0`

Primary paths:

- `vmm/src/device_manager.rs`
- `vmm/src/config.rs`
- `virtio-devices/src/vdpa.rs`

## Canonical report

Issue 7785 reports Cloud Hypervisor v51.1 with a Mellanox-backed vDPA device. Hot-add succeeds. `vm.remove-device` returns an error and the process then dies after an `Option::unwrap()` panic in `device_manager.rs`, followed by mutex-poison fallout.

The reporter's intended contract is ordinary hot-unplug:

```text
named vDPA device
      ↓
vm.remove-device
      ↓
guest eject / backend cleanup
      ↓
VMM stays alive
```

## Exact historical source failure

At v51.1, the remove path obtains the underlying virtio device type. A network vDPA backend reports the virtio network device type, so the path enters the ordinary network arm.

The arm then did:

```rust
let mut config = self.config.lock().unwrap();
let nets = config.net.as_deref_mut().unwrap();
let net_dev_cfg = nets
    .iter_mut()
    .find(|net| net.id.as_deref() == Some(id))
    .unwrap();
```

The operation owner is wrong for vDPA. Its configuration sits in `VmConfig.vdpa`, so neither the presence of `config.net` nor a matching `NetConfig` follows from `VirtioDeviceType::Net`.

The first unwrap is enough to reproduce the source mechanism from the report. v52.0 still carries the same assumption.

## Where the assumption came from

Commit:
https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/a6426e3615ae2cfa10f4c20e13546bf1e28726c6

`devices: gracefully close preserved FDs on device remove` added early cleanup for externally supplied ordinary virtio-net FDs. Before that commit, `VirtioDeviceType::Net` shared the generic allowed-removal arm with block, pmem, fs, and vsock.

The new net-specific cleanup assumed all network-typed virtio devices were represented by `NetConfig`. vDPA made that assumption false.

## Source-side resolution

Commit:
https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/commit/5b53f4202d183c2f890d651b6281b66c1e6cd9fe

Its stated purpose is rejecting removal of an already-removed device. As part of that work, ordinary-net preserved-FD cleanup changed from unconditional unwraps to this logical form:

```text
config.net
    -> maybe present
    -> maybe contains this ID
    -> maybe contains preserved FDs
```

A vDPA NIC can therefore traverse the `VirtioDeviceType::Net` allowlist without requiring a `NetConfig`.

The same commit moved config removal into `DeviceManager::remove_device()` and requires it to succeed before the PCI-down bitmap is set.

Current `VmConfig::remove_device()` explicitly includes:

```text
self.vdpa
  -> retain entries whose PCI-common ID differs
  -> mark removed when length changes
```

This gives the vDPA config the correct operation owner.

## Current ejection path

After config removal and guest PCI ejection, current `eject_device()` handles a virtio PCI device generically.

For the vDPA-relevant path it:

1. unregisters virtio ioevents;
2. calls the virtio DMA handler to unmap every guest-memory region when the device is outside the virtual IOMMU;
3. removes external virtual-IOMMU mapping state;
4. removes DMA mapping handlers from virtio-mem when required;
5. frees BAR allocations;
6. removes the PCI device from PCI, I/O, and MMIO buses;
7. removes DeviceManager bus references;
8. removes userspace mappings exposed by the virtio device;
9. calls `shutdown()` on the underlying virtio device;
10. removes the virtio device from the DeviceManager list;
11. emits `device-removed`.

The current vDPA DMA unmap helper also uses checked range arithmetic. Recent generic eject work has tightened other resource-lifetime paths as well.

## Cross-context review

### Ordinary virtio-net

The optional net lookup must still find and close preserved externally supplied FDs for an ordinary NetConfig. The current path keeps that behavior when the matching NetConfig exists.

### vDPA network

The ordinary net lookup produces `None`, which is the correct result because vDPA has no ordinary TAP FD entry there. Authoritative removal then lands in `VmConfig.vdpa`.

### Repeated remove

The fixing commit's primary purpose ensures a second remove request cannot reuse the stale PCI tree node after the configuration entry has already gone away.

### IOMMU-attached vDPA

When the virtio PCI device is IOMMU-attached, direct guest-memory DMA unmap is skipped and external mapping removal is routed through the virtual-IOMMU state. This is a distinct runtime control worth including on capable hardware if the canonical deployment uses IOMMU.

### Backend/device shutdown

Source shows the generic `VirtioDevice::shutdown()` call. The vDPA backend's real response to disable/unmap/reset remains hardware/backend evidence rather than a source-only claim.

## Result

### Demonstrated source behavior

The exact `config.net.unwrap()` panic described by issue 7785 is absent from current `main`.

### Demonstrated history

The source assumption was introduced by ordinary virtio-net preserved-FD cleanup and removed by a later accepted commit whose main purpose was repeated-remove correctness.

### Current source continuation

vDPA IDs are removed from `VmConfig.vdpa`, and the remaining eject path has generic virtio DMA and lifecycle cleanup.

### Open question

A real current-main vDPA hot-unplug has not been executed by Linux Fieldwork in this pass.

## Runtime discriminator

On a vDPA-capable host:

1. run exact current `main` and record the commit;
2. add/boot with a named vDPA NIC;
3. prove the guest sees and can use the device;
4. issue `vm.remove-device <id>`;
5. wait for the exact `device-removed` event;
6. prove API/VMM responsiveness after removal;
7. prove guest absence of the device;
8. inspect backend ownership/mappings after removal;
9. cleanly shut down;
10. repeat once.

If preserving the historical distinction is worth the setup cost, run v51.1 or v52.0 on the same backend as a negative control and retain the panic receipt.

## Promotion / stop signal

A clean current-main hardware result closes this investigation as a source-fixed historical defect.

A current-main failure after the old unwrap site creates a successor question owned by the first failing operation: DMA unmap, IOMMU cleanup, backend reset/shutdown, guest ejection, resource release, or repeated use.

Do not recreate the obsolete NetConfig unwrap fix.

## Evidence boundary

- Source/history inspection is exact to the commits and blobs above.
- The real canonical crash comes from the upstream report.
- No vDPA-capable hardware was available to this Fieldwork continuation.
- No claim is made that every backend/driver combination performs hot-unplug correctly on current main.
- No upstream interaction occurred.

## Authority

External-contact state: `false; none occurred`.
