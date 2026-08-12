# End-to-end Landlock snapshot-restore differential

Updated: 2026-08-12

Parent: `investigations/cloud-hypervisor-landlock-restore-order/README.md`
Candidate evolution: `CANDIDATE_EVOLUTION.md`
Generic mechanism: `PREOPEN_PROBE.md`
QCOW mechanism: `QCOW_ORDER_PROBE.md`
Exact upstream base: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: **disabled / no upstream contact performed**

## TL;DR

The final product-level discriminator is materialized with **byte-identical test code** on baseline and candidate.

Product candidate:

```text
teamleaderleo/cloud-hypervisor#33
branch: linux-fieldwork/landlock-restore-order-v4
head: f0d19b3c3f85f06d0987f188156f97552d01f61d
product tree: 037b3e9a3376a5f67048047ec262bdab03ee7f14
```

Candidate validation:

```text
PR: teamleaderleo/cloud-hypervisor#34
head: 2c841b719b118f0f640a82249a3b9b5c3f21260f
parent: f0d19b3c3f85f06d0987f188156f97552d01f61d
```

Baseline validation:

```text
PR: teamleaderleo/cloud-hypervisor#35
head: b41f490483f2804f5047ef43ff7ce99494d44000
parent: 1af93ac7035cda77cd87b0c18b1134ebb0928052
```

Both validation branches use the exact same `cloud-hypervisor/tests/integration.rs` blob:

```text
662b0e72917cd006c7d8ac239de2ad8bda455195
```

Therefore the only candidate/control product difference is the four-file v4 Landlock restore-order patch.

Runtime result is still pending while the `garm-jammy-16` integration pool is queued. The fixture, branches, run routes, and expected discriminator are already pinned below.

## Fixture

The test boots one VM without Landlock using:

```text
raw Ubuntu OS image
       ↓ qemu-img backing reference
QCOW2 overlay configured as the VM OS disk
```

The QCOW overlay is a configured `DiskConfig` path and therefore receives an exact automatic Landlock rule. The raw backing file is a different file and does not receive that rule.

Source review confirms `DiskConfig::apply_landlock()` grants the exact configured path, not its parent directory. Keeping overlay and backing below the same disposable test root therefore does not accidentally authorize the backing file.

The source VM boots and snapshots once. Landlock is disabled while the snapshot is produced.

After the source process is stopped, the test mutates **only** `snapshot/config.json`:

```text
landlock_enable = true
landlock_rules = null | [{ exact backing path, access = "r" }]
```

The snapshot memory file, VM state bytes, QCOW overlay, raw backing file, and guest disk contents remain unchanged across restore attempts.

## Three candidate restore attempts

### 1. Denied backing control

Saved policy:

```text
landlock_enable = true
no explicit raw-backing rule
```

Expected on selected v4 candidate:

```text
Vm::new(snapshot)
  -> apply saved VM policy + exact restore-only rules
  -> QCOW constructor opens configured overlay
  -> QCOW constructor attempts raw backing open
  -> PermissionDenied for the exact backing path
  -> restore process exits
```

The test requires all of:

- restore exits within 15 seconds;
- output contains `Permission denied`;
- output contains the exact raw backing path.

### 2. Explicit backing allow control

Saved policy:

```text
landlock_enable = true
landlock_rules = [{ exact backing path, access = "r" }]
```

Expected on v4:

- restore reaches exact `restored` event;
- HTTP API `info` answers while the restored VM remains paused.

The guest is deliberately not resumed. This keeps disk bytes unchanged for the next restore attempt.

### 3. On-demand UFFD control

Same explicitly allowed snapshot config plus:

```text
memory_restore_mode=ondemand
```

Expected on v4:

- restore reaches exact `restored` event;
- HTTP API `info` answers;
- logs contain `UFFD restore: demand-paged restore enabled`.

This covers both restore-only Landlock resources selected by v4:

- exact `source_url/memory-ranges` read rule;
- exact `/dev/userfaultfd` rw rule when on-demand mode selects that existing device node, while preserving syscall fallback when the node is absent.

## Baseline negative control

The exact same integration blob is applied directly to upstream base `1af93ac...` with no product change.

Expected baseline behavior:

```text
Vmm::vm_restore
  -> Vm::new(snapshot)
       QCOW overlay + raw backing open before Landlock
  -> apply Landlock afterward
  -> already-open raw backing FD remains usable
```

Therefore the first denied-backing restore remains alive instead of exiting, and the identical test fails this assertion:

```text
denied_exited == true
```

That baseline failure is the desired negative control. It proves the validator can distinguish the old ordering rather than merely confirming a candidate-specific happy path.

## Runtime routes

### Primary focused GARM pair

Candidate runtime branch:

```text
linux-fieldwork/landlock-restore-candidate-runtime
workflow head: cc03bc3756d0e364eabfc92b1c27fb5d9d26c4b3
run: 31550451772
runner: garm-jammy-16
```

Baseline runtime branch:

```text
linux-fieldwork/landlock-restore-baseline-runtime
workflow head: 5a41aa1892bc81c5a241a2c437c6eb588a478d70
run: 31550464041
runner: garm-jammy-16
```

Both workflows execute:

```text
scripts/dev_cli.sh tests --integration --libc gnu -- \
  --test-filter test_snapshot_restore_landlock_qcow_backing
```

At the time of this record, both jobs are queued with no runner assigned. The upstream-style #33 `integration-x86-64-pr` job is also queued on the same `garm-jammy-16` pool, so this is a runner-capacity boundary rather than a product result.

### GitHub-hosted capability fallback

Candidate branch/run:

```text
linux-fieldwork/landlock-restore-candidate-hosted
head: ab529b4ff7bd24b6c8142f01d360da22481492ab
run: 31550666770
runner: ubuntu-24.04
```

Baseline branch uses the exact same workflow bytes on an Ubuntu 24.04 hosted runner.

The hosted path checks `/dev/kvm` before installing dependencies. If nested KVM is absent, it exits immediately with:

```text
HOSTED_CAPABILITY_MISSING: /dev/kvm is absent
```

Such a result is classified as environment capability, not product or fixture behavior.

## Product quality boundary

Selected product PR #33 uses exact head:

```text
f0d19b3c3f85f06d0987f188156f97552d01f61d
```

Its CI run is:

```text
31549736699
```

Already green:

- gitlint;
- DCO;
- rustfmt for x86_64 and AArch64;
- REUSE;
- package consistency;
- typos;
- lychee;
- preflight;
- stable/beta/nightly x86 Clippy/build lanes;
- AArch64 Clippy;
- RISC-V builds;
- fuzz build;
- musl build families;
- several feature/backend builds.

The workflow remains open because downstream integration/virtio jobs are still queued or running.

## Stop rule

Promote the v4 product candidate only after the runtime pair distinguishes the two exact product states:

```text
baseline identical test -> FAILS because denied backing remains usable
v4 identical test       -> PASSES denied + explicit allow + UFFD controls
```

If candidate fails for a different reason, classify the first owner before changing product code:

- fixture path/policy;
- integration harness;
- runner capability;
- snapshot format/payload rule;
- `/dev/userfaultfd` capability;
- actual product ordering.

Do not widen the product patch until the first distinguishing owner is known.
