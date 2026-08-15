# Cloud Hypervisor PCI BAR relocation outcome protocol

Updated: 2026-08-15

Fieldwork issue: `teamleaderleo/linux-fieldwork#680`
Exact upstream source generation: `69d4c0a82ef15b2660906013bd87ae32668e7998`
External-contact state: false

## Problem

The PCI config-space callers currently interpret every `DeviceRelocation::move_bar()` error as if the old Bus mapping survived:

```text
move_bar() -> Err
-> restore BAR config register to OLD
```

That assumption is unsafe for a relocation implementation that can publish NEW-side mapping state and then fail later.

A deterministic current-main baseline proves the caller mismatch directly: a synthetic relocation stores its mapping at NEW and then returns `Err`; `PciConfigMmio` restores config to OLD, leaving config and mapping inconsistent.

Baseline receipt:

- run/job `31898817653` / `95046144743`
- artifact `9250527463`
- digest `sha256:6bb78ca1e522fa2c97c2d33d1f4db5964b3a1ce53964c17549a8bda127b39297`
- expected losing status `LATE_MOVE_BASELINE_RC=101`

Source review shows the real `AddressManager::move_bar()` has the same late-error shape: PIO/MMIO `Bus::update_range()` can succeed before later DeviceTree, ioeventfd, memslot, shared-memory, or device-local work returns an error.

## Candidate protocol

The first executed repair changes the implicit `io::Result<()>` error meaning into an explicit relocation outcome.

Experimental names:

```text
OldMappingIntact(error)
NewMappingPublished(error)
```

Caller behavior:

```text
OldMappingIntact
-> restore BAR config to OLD

NewMappingPublished
-> retain BAR config at NEW
```

`AddressManager` keeps a local commit-point bit. It starts false and flips true immediately after the PIO/MMIO Bus `update_range()` succeeds. Any later propagated error is classified as having published the new Bus mapping.

This is deliberately a **truthful outcome** repair, not a claim that the entire cross-registry operation becomes failure-atomic.

## Authoritative semantic execution

The first full semantic execution used the then-clean #599 successor base `cae581234681a45d2d7abe13c97ee3ae5d1d431e`.

Run/job:

`31900036797` / `95049222035`

Artifact:

`9250860912`

Artifact digest:

`sha256:703571b6c51c053b35ac79a69d3e0b3d9382fadc77391b9d90b6643259a8abd0`

Results:

```text
published-NEW error -> config stays NEW                 PASS
rejected / old-Bus-intact error -> config restores OLD  PASS
ordinary PCI library suite                              PASS
vm-device successor controls                            PASS
all device_manager unit tests                           PASS
complete KVM-flavoured VMM compile --no-run             PASS
stable project-shaped workspace Clippy                  PASS
nightly rustfmt / diff check                            PASS
```

Several earlier runs are harness-only history:

- inline YAML parse rejection;
- source-marker mismatch before candidate execution;
- test-only absolute-path Clippy warnings;
- a cleanup script that accidentally rewrote a real module import before product execution.

The authoritative semantic/quality result above excludes those harness defects.

## Naming refinement before a clean carrier

The experimental names are too broad.

`OldMappingIntact` could be read as promising allocator/KVM/device state is fully intact. The caller only needs to know whether restoring the **Bus-visible BAR mapping/config relation** to OLD is truthful.

Before a final clean carrier, prefer names/docs such as:

```text
OldBusMappingIntact
NewBusMappingPublished
```

or an equivalent explicit enum that states the exact commit surface.

Also add a `PciConfigIo` sibling-mode control because both IO and MMIO config callers use the same outcome decision.

## Successor-base correction

Fresh self-review later corrected the generic Bus candidate to preserve the baseline's in-flight strong device lifetime. The corrected Bus clean commit is:

`d0ed124cc80e9d22c60cdc19adb3f935517fb9e3`

Therefore this #680 protocol result is retained as **semantic evidence**, while any final #680 clean carrier must be rebased onto the corrected #599 successor after its recomposition completes.

Do not publish a #680 carrier from `cae581...`.

## Why this boundary is attractive

`DeviceRelocation` has a small production surface:

- one real relocation owner: `AddressManager`;
- two config callers: `PciConfigIo` and `PciConfigMmio`;
- a few test mocks.

That makes a truthful result protocol comparatively bounded. It avoids immediately requiring complete compensating rollback for every DeviceTree, ioeventfd, memslot, SHM, VFIO, and device-local stage just to stop the caller from making a partial state worse.

## Evidence boundary

Proven:

- an undifferentiated relocation error is insufficient for the caller;
- a commit-point-aware result can keep config aligned with the known Bus mapping state in deterministic tests;
- the protocol compiles and passes the clean successor's tested package/workspace gates.

Still separate:

- whether every late NEW-side partial state should later be rolled back to OLD;
- cleanup/retry of allocator quarantine from #599;
- target-native KVM failures after Bus publication;
- SHM/VFIO family-specific recovery;
- PIO semantics beyond the Bus-mapping outcome itself.

## Next action

After corrected #599 v2 is stable:

1. rebase the explicit-outcome protocol onto the corrected clean successor;
2. narrow the outcome names/docs to the Bus mapping contract;
3. add PciConfigIo and PciConfigMmio controls for both outcome variants;
4. rerun PCI, vm-device, device-manager, complete KVM-flavoured compile, stable workspace Clippy, rustfmt, and diff checks;
5. only then decide whether the result protocol deserves its own clean review carrier or should remain an internal prerequisite for a broader relocation transaction.
