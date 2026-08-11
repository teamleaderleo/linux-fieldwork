# Cloud Hypervisor — partial VM pause failure

Updated: 2026-08-11
State: SCOPING / SOURCE BOUNDARY MAPPED
Owning issue: #589
Exact upstream source: `cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; none occurred

## TL;DR

`Vm::pause()` parks vCPUs before several later fallible operations, but changes `VmState` from Running to Paused only after every substep succeeds. A later pause error can therefore return while the stored state still says Running and the vCPUs are already paused.

A disconnected vhost-user backend is a concrete current failure owner after CPU pause: `VhostUserCommon::pause()` returns `DeviceDisconnected`. Because `Vm::resume()` validates the stored state before resuming components, the split state can also reject the obvious recovery operation as an invalid Running-to-Running transition.

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

Current vhost-user common pause returns `MigratableError::DeviceDisconnected` when the backend is marked disconnected, supplying a real device-layer failure after CPU pause.

Current `Vm::resume()` validates `self.state -> Running` before restoring clock / hypervisor / device / CPU execution. The VM state-machine tests reject Running -> Running.

## First probe

Use a disposable vhost-user-backed VM:

1. prove Running plus guest progress;
2. disconnect the backend;
3. call `vm.pause`;
4. capture the pause error;
5. query `vm.info`;
6. independently check guest progress;
7. call `vm.resume` and capture its result.

Expected discriminator:

```text
before: state=Running, guest progressing
pause: error
after: state=Running, guest stopped
resume: rejected before CPU resume
```

Controls:

- healthy backend: pause -> Paused, resume -> Running;
- failure before CPU pause: no split CPU state;
- already-Paused VM: pause rejected before mutation.

## Adjacent contexts

### Clock capture failure

`capture_guest_clock()` is fallible after vCPU pause. A test-double failure would prove the same VM-level transaction gap without a device dependency.

### DeviceManager aggregation

DeviceManager itself pauses child migratables sequentially. One child can fail after earlier children committed. Check whether a VM-level `device_manager.resume()` unwind is enough or whether the device layer needs its own transaction handling.

### Hypervisor pause failure

This is the latest failure boundary: CPU and device pause already succeeded. A controlled backend error here would test full reverse-order unwind.

### Coredump

Fieldwork #587 is distinct: coredump fails after a *successful* pause and forgets to restore an originally Running VM. This lane covers `pause()` itself returning an error after partial mutation.

## Candidate boundary

Do not merely set `VmState::Paused` earlier. That would make the opposite lie possible: stored Paused while later subcomponents are still Running.

Required property:

> a failed `Vm::pause()` either restores all committed subcomponents to the original Running state or returns a deliberately recoverable state that reflects the partial transition.

Prefer reverse-order rollback or a two-phase/preflight structure where possible. Keep error precedence explicit if rollback also fails.

## Evidence boundary

Source-proven:

- state assignment occurs only at successful pause completion;
- CPUs pause before later fallible work;
- disconnected vhost-user pause is a concrete later error;
- there is no VM-level unwind;
- ordinary resume validates state first and Running -> Running is invalid.

Execution pending:

- exact current backend-disconnect sequence;
- API state and guest-progress mismatch;
- resume rejection;
- candidate rollback and regression gates.

## Stop condition

Close or narrow if exact-current execution reveals an unseen unwind owner before the API error returns. Split nested DeviceManager rollback only if it materially changes the repair boundary.

## Authority

Internal Linux Fieldwork only. No upstream issue, pull request, comment, review, email, reaction, or other interaction is authorized or performed.
