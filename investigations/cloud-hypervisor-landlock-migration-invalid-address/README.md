# Cloud Hypervisor Landlock migration log: expected denial vs rare invalid queue address

## TL;DR

Canonical issue 7248 combines an expected Landlock denial with a later rare virtio-block address failure. The denied `add-disk ~/workloads/blk.img` is part of the accepted test contract: the source and destination intentionally attempt a path outside the granted Landlock rules and require that API call to fail.

The later block-worker invalid guest address is the only unresolved defect signal in that report. Current upstream now exercises successfully hot-added secondary block devices across multiple live-migration and snapshot/restore paths, which gives stronger adjacent negative evidence against a broad migrated-block-state defect. Linux Fieldwork has no current-main reproduction of the rare address failure, so this remains triage rather than a source candidate.

Tracking issue: [linux-fieldwork #575](https://github.com/teamleaderleo/linux-fieldwork/issues/575)  
Canonical report: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/7248

## Explain like I'm five

The test has a deliberate red light:

```text
unknown disk path + Landlock -> denied
```

That red light proves the sandbox traveled with the VM.

The interesting event comes later:

```text
migrated VM -> block worker -> nonsense guest address
```

Those need separate explanations.

## Why care

A noisy permission error near a later crash can make an investigation chase the wrong subsystem. The accepted test explicitly wants the permission error. Changing Landlock policy to suppress it would remove a negative control while leaving the rare block/queue event unexplained.

## Current state

- State: `RETAINED TRIAGE / NO SOURCE CANDIDATE`
- Current canonical head inspected: `a658c9f9fd0c4e0363004361d73ac8733fa24fd0`
- Historical Landlock migration test introduction: `8452edfcc7543454b0c74ac556c34f35a9627ffa`
- Current adjacent migrated-disk expansion: `05ba440cae6418ade01b82d963f3c955e57011dd`
- Candidate source commit: none
- Cleanup state: no runtime state
- External-contact state: `false; none occurred`

## Original test contract

The accepted Landlock migration test explicitly defines six checks:

1. source VM is functional;
2. source rejects hotplug of a disk whose path is outside its granted Landlock paths;
3. migration succeeds;
4. source exits successfully;
5. destination is functional;
6. destination rejects the same unknown disk path, proving Landlock policy remained active.

The test grants `rw` only to the guest's per-test temporary directory. Its negative-control disk is `~/workloads/blk.img`, deliberately outside that grant.

The source assertion is:

```text
assert add-disk(...) == false
```

Current test comments retain the same source/destination denial contract.

## Canonical issue log

Issue 7248 shows the expected source-side hotplug denial first:

```text
Cannot open disk path
Permission denied
```

Migration later reaches the destination. A virtio-block worker then reports an invalid guest address far outside the configured physical-address range, and the destination eventually becomes unavailable.

An upstream maintainer noted that the rare address event was difficult to attribute specifically to live migration and resembled another infrequent virtqueue-address problem seen elsewhere.

## Current adjacent evidence

Commit `05ba440cae6418ade01b82d963f3c955e57011dd` strengthens migration/restore block-device coverage.

It adds per-test `add_test_disk` and `remove_test_disk` helpers that:

- create a 16 MiB raw disk under the guest temporary directory;
- hot-add it with stable ID `test0`;
- wait until the guest sees the device;
- migrate or snapshot/restore;
- verify the device remains visible on the destination/restored VM;
- hot-remove it and wait for guest disappearance.

That control is used across several current migration/restore variants. It proves current upstream routinely exercises a real hot-added block device through restored/migrated device state.

This narrows issue 7248. It does not prove a rare timing-dependent queue-address failure can never recur.

## Useful competing explanations

### A. Landlock policy corruption

Prediction: the intentional rejected open changes behavior or causes an immediate state error tied to sandbox application.

Control: run the Landlock negative probe without migration; it should be denied while existing VM I/O remains healthy.

### B. Generic virtqueue restore defect

Prediction: the invalid address can reproduce without Landlock under matching queue activity/migration timing.

Control: same VM/device workload with Landlock disabled.

### C. Block-specific request state

Prediction: failure depends on block queue activity or an in-flight request at pause/state transfer.

Control: idle queue versus deliberate I/O load around migration.

### D. Historical source-generation bug

Prediction: current source does not reproduce under repeated exact current tests, while an old source generation does.

Control: retain exact old/current heads and compare raw worker traces before inferring mechanism.

## Next useful execution

If a suitable KVM runner is available:

1. run current `test_live_migration_with_landlock` repeatedly and preserve destination logs;
2. record the expected source and destination denied hotplug probes separately from worker failures;
3. repeat the migration path without Landlock;
4. add deliberate block activity near migration pause/state transfer;
5. use the current successful hot-added-disk migration helper as an adjacent control;
6. stop when the first current-main divergence names an operation owner.

## Promotion signal

Promote into source work only when current source produces a repeatable invalid-address failure with a distinguishing owner: queue serialization/restore, block request state, guest-memory translation, backend address translation, or another concrete operation.

## Stop signal

Retain as a historical intermittent result if repeated current-main tests stay clean and no source invariant can be made to lose.

Do not alter the intentional Landlock denial simply to make the transcript quieter.

## Evidence boundary

- Expected Landlock denial is demonstrated from accepted historical and current test intent.
- Stronger current migrated-block coverage is demonstrated from accepted current test code.
- Linux Fieldwork did not reproduce issue 7248 on current main in this pass.
- No claim is made that the rare invalid-address event is conclusively fixed.
- No upstream interaction occurred.

## Authority

External-contact state: `false; none occurred`.
