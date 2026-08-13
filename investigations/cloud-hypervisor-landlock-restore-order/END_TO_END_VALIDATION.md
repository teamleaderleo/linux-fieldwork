# End-to-end Landlock snapshot-restore differential

Updated: 2026-08-13

Parent: `investigations/cloud-hypervisor-landlock-restore-order/README.md`
Candidate evolution: `CANDIDATE_EVOLUTION.md`
Generic mechanism: `PREOPEN_PROBE.md`
QCOW mechanism: `QCOW_ORDER_PROBE.md`
Exact upstream base: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: **disabled / no upstream contact performed**

## Current status

**HOLD — repair and re-unify the validator before claiming an end-to-end differential.**

The product mechanism remains supported by the already-executed generic pre-open and QCOW backing-chain probes, but the current candidate/baseline integration carriers are not yet a valid byte-identical runtime pair.

Product candidate:

```text
teamleaderleo/cloud-hypervisor#33
branch: linux-fieldwork/landlock-restore-order-v4
head: f0d19b3c3f85f06d0987f188156f97552d01f61d
product tree: 037b3e9a3376a5f67048047ec262bdab03ee7f14
```

Candidate validator:

```text
teamleaderleo/cloud-hypervisor#34
branch: linux-fieldwork/landlock-restore-order-v4-validation
head: e1b95da99ad772f0eff815ebe20932d6e40346f8
integration.rs blob: f50510cb98340142063e82758b94f4e64f2ac834
```

Baseline validator:

```text
teamleaderleo/cloud-hypervisor#35
branch: linux-fieldwork/landlock-restore-order-baseline-validation
head: b41f490483f2804f5047ef43ff7ce99494d44000
integration.rs blob: 662b0e72917cd006c7d8ac239de2ad8bda455195
```

Those blobs differ because #34 received a later serde-json import cleanup while #35 retained the earlier spelling. More importantly, both current variants still construct the raw backing path with the same compile-broken expression:

```text
Path::new(guest.disk_config.disk(DiskType::OperatingSystem).unwrap())
```

`disk(...)` returns an owned `String`; `Path::new()` needs a borrowed path-like value. The x86 integration compile therefore fails before the intended restore matrix executes.

## Required validator rebuild

The next valid differential must satisfy all of these before runtime interpretation:

1. repair the path construction once;
2. choose one serde-json spelling and one complete test implementation;
3. apply the **exact same repaired `cloud-hypervisor/tests/integration.rs` blob** to candidate #34 and baseline #35;
4. compile both through the same x86 integration route;
5. verify the two validator blob hashes are identical;
6. only then execute and compare the restore outcomes.

Do not compare a repaired candidate validator against an unrepaired or textually different baseline validator.

## Fixture

The validator boots one VM without Landlock using:

```text
raw Ubuntu OS image
       ↓ qemu-img backing reference
QCOW2 overlay configured as the VM OS disk
```

The configured QCOW overlay receives the normal exact disk Landlock rule. The raw backing file is a separate path and is deliberately omitted unless the positive control adds an explicit read rule.

The source VM snapshots once with Landlock disabled. After stopping the source process, the validator changes only `snapshot/config.json` between restore attempts:

```text
landlock_enable = true
landlock_rules = null | [{ exact backing path, access = "r" }]
```

Snapshot memory/state, overlay bytes, backing bytes, and guest disk contents remain unchanged.

## Intended candidate matrix

### 1. Denied backing

Saved policy:

```text
landlock_enable = true
no explicit raw-backing rule
```

On the selected v4 product, restore should apply the saved policy plus exact restore-only rules before QCOW construction. The raw backing open should fail with `PermissionDenied` for the exact backing path, and the restore process should exit.

The validator requires:

- exit within 15 seconds;
- `Permission denied` in output;
- exact raw backing path in the error chain.

### 2. Explicit backing allow

Saved policy includes the exact raw backing read rule. Eager restore should reach the exact `restored` event and answer API `info` while the VM remains paused.

### 3. On-demand restore

The same explicitly allowed snapshot plus `memory_restore_mode=ondemand` should:

- reach `restored`;
- answer API `info`;
- log `UFFD restore: demand-paged restore enabled`.

This exercises the two restore-only resources selected by v4: `source_url/memory-ranges` and conditional `/dev/userfaultfd` access.

## Intended baseline negative control

The exact same repaired validator blob must be applied directly to upstream base `1af93ac...` with no product change.

Expected old ordering:

```text
Vmm::vm_restore
  -> Vm::new(snapshot)
       QCOW overlay + raw backing open before Landlock
  -> apply Landlock afterward
  -> already-open raw backing FD remains usable
```

The first denied-backing attempt should therefore remain alive instead of satisfying `denied_exited == true`. That expected test failure is the negative control proving the validator distinguishes the old ordering.

## Already established mechanism evidence

The end-to-end lane is blocked on validator correctness, not on the underlying file-descriptor premise.

Generic pre-open probe:

```text
run/job: 31547742820 / 93963728979
result: PASS
```

It proved that after restriction a new unlisted open is denied while an already-open descriptor for that same file remains usable.

QCOW backing-chain probe:

```text
run/job: 31548103949 / 93964786948
result: PASS
```

It proved the same ordering distinction through Cloud Hypervisor's real `QcowDisk::new()` path and backing-file reader.

The probe PRs are now archival/completed evidence; #33/#34/#35 own the remaining product-level decision.

## Stop rule

Promote #33 only after one repaired, byte-identical validator produces the intended differential:

```text
baseline identical test -> FAILS because denied backing remains usable
v4 identical test       -> PASSES denied + explicit allow + UFFD controls
```

If either side fails before that comparison, classify the first owner before changing product code:

- validator compile/test harness;
- fixture path/policy;
- runner/KVM capability;
- snapshot payload rule;
- `/dev/userfaultfd` capability;
- actual product ordering.

Do not widen the product patch until the validator itself is clean and identical on both sides.
