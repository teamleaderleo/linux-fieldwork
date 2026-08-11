# Cloud Hypervisor — partial VM pause failure

Updated: 2026-08-11
State: SCOPING / SOURCE BOUNDARY MAPPED
Owning issue: #589
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; none occurred

## TL;DR

`Vm::pause()` parks vCPUs before several later fallible operations, but changes `VmState` from Running to Paused only after every substep succeeds. A later pause error can therefore return while the stored state still says Running and the vCPUs are already paused.

The bounded cross-context pass rejected the initial disconnected-vhost-user trigger because `DeviceManager::pause()` deliberately swallows `DeviceDisconnected`. The stronger current trigger is vDPA: its `pause()` rejects ordinary pause outside live migration, and DeviceManager propagates that error after CPU pause has already completed.

Because `Vm::resume()` validates the stored state before resuming components, the split state can also reject the obvious recovery operation as an invalid Running-to-Running transition.

## Explain like I'm five

Pausing a VM is several switches, not one switch. Cloud Hypervisor turns off the CPU switch first, then tries some other switches, and only at the very end changes the label from “Running” to “Paused.”

If one of the later switches fails, it returns an error but leaves the CPU switch off and the label saying “Running.” Then “resume” looks at the label, thinks the VM is already running, and can refuse to turn the CPU switch back on.

## Why care

Status and recovery must describe the real execution state. A pause error should not strand a VM in a state that is neither truly Running nor normally resumable.

## Source boundary

Current `Vm::pause()` ordering:

```text
validate Running -> Paused
activate_virtio_devices()?
cpu_manager.pause()?
saved_clock = capture_guest_clock()?
device_manager.pause()?
hypervisor_vm.pause()?
self.state = Paused
```

The state assignment is last. CPU pause is therefore committed before three later failure boundaries.

Current `Vdpa::pause()` returns an error unless the device is already in a migration context. Current `DeviceManager::pause()` propagates that ordinary error.

Current `Vm::resume()` validates `self.state -> Running` before restoring clock / hypervisor / device / CPU execution. The VM state-machine tests reject Running -> Running.

## First probe

Use a current vDPA-backed VM:

1. prove Running plus guest progress;
2. call ordinary `vm.pause` with no migration active;
3. capture the vDPA pause error;
4. query `vm.info`;
5. independently check guest progress;
6. call `vm.resume` and capture its result.

Expected discriminator:

```text
before: state=Running, guest progressing
pause: vDPA outside-migration error
after: state=Running, guest/vCPUs parked
resume: rejected before CPU resume
```

Controls:

- ordinary VM without vDPA: pause -> Paused, resume -> Running;
- disconnected vhost-user: DeviceManager explicitly skips `DeviceDisconnected` and continues;
- vDPA while a valid migration is active: its migration-only pause path returns Ok.

## Adjacent contexts

### Clock capture failure

`capture_guest_clock()` is fallible after vCPU pause. A test-double failure would prove the same VM-level transaction gap without a device dependency.

### DeviceManager aggregation

DeviceManager pauses child migratables sequentially. One ordinary child error can follow earlier successful device pauses. Check whether a VM-level `device_manager.resume()` unwind is enough or whether the device layer needs its own transaction handling.

### Hypervisor pause failure

This is the latest failure boundary: CPU and device pause already succeeded. A controlled backend error here would test full reverse-order unwind.

### Negative result: disconnected vhost-user

`VhostUserCommon::pause()` can return `DeviceDisconnected`, but DeviceManager catches exactly that variant, logs a skip, and proceeds. This path cannot currently be used as the propagated pause error and should remain a negative control.

### Coredump

Fieldwork #587 is distinct: coredump fails after a *successful* pause and forgets to restore an originally Running VM. This lane covers `pause()` itself returning an error after partial mutation.

## Candidate boundary

Do not merely set `VmState::Paused` earlier. That would make the opposite lie possible: stored Paused while later subcomponents are still Running.

Required property:

> a failed `Vm::pause()` either restores all committed subcomponents to the original Running state or returns a deliberately recoverable state that reflects the partial transition.

Compare preflighting pause capability with reverse-order rollback. vDPA's migration-only pause policy suggests an operation/mode capability check may avoid this specific mutation, while clock/hypervisor races still require a general rollback story.

## Evidence boundary

Source-proven:

- state assignment occurs only at successful pause completion;
- CPUs pause before later fallible work;
- vDPA ordinary pause is rejected outside migration;
- DeviceManager propagates that vDPA error;
- disconnected vhost-user is explicitly skipped and is a negative result;
- there is no VM-level unwind;
- ordinary resume validates state first and Running -> Running is invalid.

Execution pending:

- exact current vDPA ordinary-pause sequence;
- API state and guest-progress mismatch;
- resume rejection;
- candidate preflight/rollback and regression gates.

## Stop condition

Close or narrow if an outer API/config owner blocks ordinary pause on vDPA before CPU pause, or exact-current execution reveals an unseen unwind owner before the API error returns. Split nested DeviceManager rollback only if it materially changes the repair boundary.

## Authority

Internal Linux Fieldwork only. No upstream issue, pull request, comment, review, email, reaction, or other interaction is authorized or performed.
