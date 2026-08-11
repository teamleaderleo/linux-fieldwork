# Cloud Hypervisor — CPU hotplug notification failure and retry

Updated: 2026-08-11
State: SCOPING / SOURCE BOUNDARY MAPPED
Owning issue: #594
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; none occurred

## TL;DR

CPU resize commits host-side vCPU insertion/removal state before the fallible ACPI notification. A same-size retry uses committed CPU-manager state as its “nothing changed” predicate, so it can skip the notification that failed on the first attempt.

Growth can then update config and report success without replaying notification. Shrink can instead be blocked by its pending-removal marker.

## Explain like I'm five

Cloud Hypervisor adds the CPU first and rings the guest’s doorbell second. If the doorbell fails, trying again sees “CPU already added” and does not ring the doorbell again.

## Why care

Host vCPU count, guest ACPI awareness, and VM config must converge. Retry should complete an interrupted hotplug, not merely make config match the VMM’s partial state.

## Source boundary

`Vm::resize()`:

```text
if cpu_manager.resize(desired)? {
    notify_hotplug(CPU_DEVICES_CHANGED)?
}
config.cpus.boot_vcpus = desired
```

Growth `CpuManager::resize()` creates/configures/activates new vCPU threads and sets inserting state before returning `true`.

Shrink marks CPUs for removal before returning `true`.

Same-size growth retry returns `false` because `present_vcpus()` already equals the target. Shrink retry can fail early because pending removal already exists.

## First probe

Fault-inject CPU hotplug notification once.

Growth:

```text
X -> Y
first: Err, present=Y, config=X, notify count=1
retry Y: current source predicts Ok, config=Y, notify count still=1
```

Shrink:

```text
X -> Y
first: Err, removal pending, config=X
retry Y: capture pending-removal error and whether notify is replayed
```

Successful notification is the no-op retry control.

## Candidate boundary

The completion predicate must mean guest-visible hotplug completed, not merely host thread count/removal markers.

Compare pending-notification replay, staged transaction state, rollback, and explicit reconciliation. Growth and shrink rollback are not symmetric.

## Relation to #592

#592 is the analogous ACPI RAM progress-marker defect. Keep candidates separate because CPU insertion/ejection state differs from memory/device DMA publication.

## Evidence boundary

Source-proven ordering and retry predicates. Execution/fault injection, guest observation, candidate, and CI gates remain pending.

## Stop condition

Narrow if another owner automatically replays failed CPU hotplug notification or the guest reliably discovers the change without it in the tested configuration.

## Authority

Internal Linux Fieldwork only. No upstream interaction is authorized or performed.
