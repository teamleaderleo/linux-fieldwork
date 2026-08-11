# Cloud Hypervisor — ACPI memory hotplug partial publication and retry

Updated: 2026-08-11
State: SCOPING / SOURCE BOUNDARY MAPPED
Owning issue: #592
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; none occurred

## TL;DR

ACPI RAM hotplug commits MemoryManager state before publishing the new region to devices and notifying the guest. If a later publication phase fails, a retry to the same requested size sees `current_ram` already advanced, returns no new region, and skips the unfinished phases. The retry can then update config and report success while live-state publication remains incomplete.

## Explain like I'm five

The resize operation checks off “new memory added” too early. If telling the devices or guest about that memory fails, trying the same resize again sees the early checkmark and says “nothing left to do,” even though the important notifications never finished.

## Why care

Memory size exists simultaneously in KVM mappings, MemoryManager bookkeeping, device DMA/memory tables, ACPI hotplug slots, guest notifications, and VM config. Retry must reconcile those representations rather than turn a partial failure into apparent success.

## Source boundary

For ACPI mode, `MemoryManager::resize()` calls `hotplug_ram_region()`, then sets `current_ram = desired_ram`, and returns the new region.

`hotplug_ram_region()` has already created the region, associated it with the memory zone, allocated its range, marked the hotplug slot active/inserting, and advanced the slot index.

Only afterward `Vm::resize()` calls `DeviceManager::update_memory(new_region)` and ACPI `notify_hotplug()`. Config is updated after those calls.

`DeviceManager::update_memory()` is itself sequential and fallible across virtio memory-region updates, DMA mappings, VFIO, and vfio-user consumers.

## Broken retry

```text
X -> request Y
MemoryManager commits region/current_ram=Y
update_memory or notify fails
API returns Err; config still X

retry Y
MemoryManager sees Y == current_ram -> returns None
Vm skips update_memory + notification
config becomes Y
API can return Ok
unfinished first-attempt publication remains
```

## First probe

Use deterministic fake/fault-injection consumers:

- fail first/middle/last memory consumer after region creation;
- record MemoryManager state, config, per-consumer mappings, notification calls;
- issue the same resize again;
- assert whether failed publication is replayed.

Add a notification-only failure control after device updates succeed.

## Candidate boundary

Keep the progress marker behind the durable/retryable publication boundary. Compare full rollback, staged pending-hotplug state, delayed `current_ram` commit, and idempotent reconciliation.

Any solution must handle partial DeviceManager success; changing only `current_ram` cannot unmap already-updated devices safely.

## Adjacent contexts

- `hotplug_ram_region()` has its own internal partial-mutation possibilities before allocator/slot completion;
- CPU hotplug has a similar resize-before-notification ordering but may need a separate carrier;
- virtio-mem has a different owner/state model and is a negative scope control;
- config-on-reboot intent does not prove live publication completed.

## Evidence boundary

Source-proven: region/current-size commit precedes two fallible publication phases; same-size retry skips those phases; DeviceManager update is sequential with no rollback.

Execution pending: fake consumer matrix, notification failure, API double-resize observation, candidate and CI gates.

## Stop condition

Narrow if an outer error handler demonstrably reconciles the live resize after `Vm::resize()` fails. Split nested DeviceManager partial mapping only if it requires an independent repair.

## Authority

Internal Linux Fieldwork only. No upstream interaction is authorized or performed.
