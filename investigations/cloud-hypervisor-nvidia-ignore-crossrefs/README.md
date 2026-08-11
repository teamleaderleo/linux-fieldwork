# Cloud Hypervisor NVIDIA flaky-test issue cross-references

Updated: 2026-08-11

Fieldwork issue: `teamleaderleo/linux-fieldwork#601`
Canonical source: `cloud-hypervisor/cloud-hypervisor` `main` @ `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Introducing commit: `595a24d27004ce4ef4789cabf8e91b6cdc8f84e8`
Current state: **source/history confirmed test-metadata defect; two-line correction ready**
Upstream-contact state: **disabled / no contact performed**

## TL;DR

The two ignored iommufd/NVIDIA tests point at each other's tracking issue.

Current source:

```rust
#[ignore = "See #8548"]
fn test_iommufd_nvidia_card_pci_hotplug() { ... }

#[ignore = "See #8549"]
fn test_iommufd_nvidia_card_x_exclude_mmap_bars() { ... }
```

Current issue titles:

```text
#8548 = Flaky test_iommufd_nvidia_card_x_exclude_mmap_bars
#8549 = Flaky test_iommufd_nvidia_card_pci_hotplug
```

The correct annotations are therefore the reverse of current source.

This is a test-routing defect only. It says nothing about the underlying NVIDIA/iommufd failures.

## Why care

An ignored test's annotation is the first breadcrumb a developer sees when deciding why a gate is disabled and where to resume investigation. These two breadcrumbs currently route each test to the other failure report.

That also obscures useful history: the PCI-hotplug report and the exclude-mmap-bars report contain different failure contexts.

## Source/history proof

Commit `595a24d27004ce4ef4789cabf8e91b6cdc8f84e8` made the VFIO runner required again and skipped the two flaky tests. Its commit message says the failures are tracked in #8548 and #8549, while the diff applies:

```text
PCI hotplug        -> See #8548
x-exclude mmap BAR -> See #8549
```

The issue titles establish the intended association is:

```text
PCI hotplug        -> #8549
x-exclude mmap BAR -> #8548
```

Current main still carries the swapped annotations.

## Adjacent readiness result

The historical PCI-hotplug test originally used:

```text
sleep(10s)
check_nvidia_gpu()
```

Current main has improved this to:

```rust
assert!(wait_until(Duration::from_secs(10), || guest.check_nvidia_gpu()));
```

Current `check_nvidia_gpu()` returns a boolean and prints guest dmesg + `nvidia-smi` diagnostics on failure.

So the annotation swap is independent from the readiness behavior. Keep #8549 open as its own hardware/test-flake question until current VFIO hardware evidence selects a root cause.

## Candidate

```diff
-    #[ignore = "See #8548"]
+    #[ignore = "See #8549"]
     fn test_iommufd_nvidia_card_pci_hotplug() {

-    #[ignore = "See #8549"]
+    #[ignore = "See #8548"]
     fn test_iommufd_nvidia_card_x_exclude_mmap_bars() {
```

No product code, helper behavior, timeout, or test enablement changes.

## Evidence boundary

Established:

- exact current annotations;
- exact current issue titles;
- introducing commit and patch;
- current helper uses bounded polling for PCI hotplug.

No runtime test is required to prove which issue number names which test. A compile-only or ordinary integration-test build is sufficient for a local candidate because the change only edits ignored-test metadata.

## Next action

Keep the two-line correction ready inside Fieldwork. If a human later authorizes an upstream packet, refresh current main and issue disposition first, then submit only the annotation swap unless one of the flaky issues has already been closed/renumbered.
