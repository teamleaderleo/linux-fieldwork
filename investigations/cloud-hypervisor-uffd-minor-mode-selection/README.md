# Cloud Hypervisor UFFD minor-mode selection after UFFDIO_CONTINUE

Updated: 2026-08-11

Upstream issue/fix context: https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8663
Canonical source: `cloud-hypervisor/cloud-hypervisor` `main` @ `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Current state: **source-reviewed negative result; no mixed-zone defect promoted**
Upstream-contact state: **disabled / no contact performed**

## TL;DR

The recent shared-backing postcopy fix replaced `UFFDIO_WAKE`-only resolution with `UFFDIO_CONTINUE` and added minor-fault registration/feature checks. A plausible adjacent concern was that one `shared_backing` boolean controls the whole socket-backed UFFD source even though a VM can have several memory zones.

Current source closes the obvious mixed-zone failure path:

- receive sets `shared_backing` only when memory FDs were actually delivered before configuration;
- sender sends memory FDs only for `local` migration;
- `local` migration is rejected unless `VmConfig::backed_by_shared_memory()` is true;
- for zoned memory, that predicate returns true only when **every** zone is either `shared` or hugepage-backed;
- a shared socket source requests MISSING+MINOR registration, requests the corresponding SHMEM/HUGETLB minor features for the configured zone set, verifies that `UFFDIO_CONTINUE` is present in the registered-range ioctl mask, and then uses CONTINUE for both demand faults and background prefault.

So a VM with one shared zone plus one ordinary anonymous zone does not enter the shared-memory-FD local/postcopy path. It is rejected before migration ownership transfer.

This pass retains the hypothesis as a negative result. Reopen if a sender can produce a **partial** MemoryFd set that survives receive configuration, or if a future migration mode marks `shared_backing` independently of actual FD handoff.

## Explain like I'm five

`UFFDIO_CONTINUE` only works when the guest page already exists in shared backing memory. Cloud Hypervisor therefore needs to know whether the page is arriving through shared memory or inside the migration socket.

The code uses one switch for that choice.

The risky scenario would be:

```text
zone A = shared memory
zone B = ordinary anonymous memory
one global switch = "shared"
```

Then zone B would be handled with the wrong UFFD operation.

Current local migration admission prevents that combination from reaching this path: with memory zones, every zone must have shared/hugepage backing before local migration is accepted.

## Why care

Issue 8663 was a cross-layer fault-resolution bug: bytes existed in backing memory, but the kernel had never been told to map them. Its repair introduces a new mode distinction—COPY for inline bytes versus CONTINUE for already-populated shared backing.

Mode-selection bugs near this boundary can look like guest resets, repeat faults, or restore hangs. Recording the negative result keeps future work aimed at configurations that can actually violate the mode contract.

## Exact current-source observations

### UFFD source selects COPY versus CONTINUE

`vmm/src/uffd.rs` has two source families:

- `FileUffdMemorySource` reads bytes locally and resolves with `UFFDIO_COPY`; it reports `requires_uffd_minor_mode() == false`.
- `SocketUffdMemorySource` receives either inline bytes or a shared-backing acknowledgement.
  - `shared_backing == false`: response length must equal the page size, bytes are read from the socket, then `UFFDIO_COPY` resolves the page.
  - `shared_backing == true`: response length must be zero because the peer populated shared memory directly, then `UFFDIO_CONTINUE` maps the existing page.

The shared socket source reports `requires_uffd_minor_mode() == self.shared_backing`.

`UFFDIO_WAKE` remains only as an `EEXIST` cleanup path after COPY/CONTINUE says another resolver already installed the page.

### Registration follows the source requirement

`MemoryManager::prepare_uffd()` passes `source.requires_uffd_minor_mode()` into registration.

When minor mode is required, registration requests:

```text
UFFDIO_REGISTER_MODE_MISSING | UFFDIO_REGISTER_MODE_MINOR
```

and the returned range ioctl mask must contain the basic COPY/WAKE ioctls plus CONTINUE.

The UFFD API feature request also adds the relevant minor-fault feature:

- `UFFD_FEATURE_MINOR_SHMEM` when zones use shared/shmem-style backing;
- `UFFD_FEATURE_MINOR_HUGETLBFS` when zones use hugepages.

So the fix does not merely issue CONTINUE and hope the kernel supports it; setup fails before guest execution if the needed feature/ioctl contract is absent.

### Receive-side `shared_backing` comes from FD handoff

During receive configuration:

```text
shared_backing = !memory_files.is_empty()
```

The receive state machine only gains memory files through `Command::MemoryFd` before `Command::Config`.

A receive with no memory FDs therefore uses the inline/COPY socket source even if the VM configuration itself contains a `shared` flag.

### Sender only sends memory FDs for local migration

The send path calls `vm.send_memory_fds()` only when the migration request has `local = true`, and only over a Unix socket.

Before VM ownership is handed to the migration worker, local migration is rejected unless `VmConfig::backed_by_shared_memory()` is true.

Current predicate:

```text
base memory: shared || hugepages -> true
zoned memory (size == 0):
    if any zone is neither shared nor hugepages -> false
    otherwise -> true
```

That is an all-zones gate for the configuration that could otherwise mix shared and ordinary anonymous memory.

## Hypothesis tested

> A VM with mixed shared and anonymous zones can receive a global `shared_backing=true`, causing CONTINUE to be used for an anonymous range that needs COPY.

Current source result: **the ordinary supported local-migration route blocks this configuration before migration starts.**

The hypothesis therefore loses as a current product defect.

## Remaining uncertainty: partial MemoryFd sequences

This pass did not execute a deliberately malformed migration sender that transmits only a subset of the expected memory FDs before Config.

The normal sender calls `vm.send_memory_fds()` as one local-migration phase after the all-zones admission check. A future or malformed peer that can construct a partial FD map is the remaining discriminator because receive currently defines `shared_backing` as `!memory_files.is_empty()` rather than proving completeness at that assignment point.

Do not promote that into a defect from source appearance alone. First show that receive configuration accepts a partial set for a VM whose memory manager then contains at least one range without the corresponding shared backing.

## Negative controls retained

1. Remote/postcopy with no MemoryFd commands -> socket carries full page bytes -> COPY.
2. Local/postcopy with shared memory FDs -> peer populates backing -> zero-length response -> CONTINUE.
3. Shared path missing minor features or CONTINUE ioctl -> setup error before resume.
4. Zoned VM with one ordinary anonymous zone -> local migration admission fails through `backed_by_shared_memory()`.

## Evidence boundary

Established from exact current source:

- source-specific COPY/CONTINUE selection;
- minor-mode and feature negotiation;
- range-ioctl verification;
- receive derives shared mode from actual MemoryFd presence;
- sender emits MemoryFd only for local migration;
- local migration's zoned-memory predicate requires every zone to be shared or hugepage-backed.

Still unexecuted here:

- issue 8663 runtime reproduction on the landed fix;
- malformed or partial MemoryFd protocol injection;
- old-kernel compatibility below the required minor-feature versions;
- mixed hugepage types across zones under real KVM.

## Stop condition

Keep this result closed unless one of these occurs:

- a partial MemoryFd set reaches a configured memory manager and produces mixed backing under `shared_backing=true`;
- a new transport derives `shared_backing` from configuration rather than FD handoff;
- a shared/hugepage zone type requires a different fault-resolution primitive than the current feature selection assumes;
- runtime evidence shows CONTINUE/COPY selection diverging from the source contract above.

## Next action

None for the mixed-zone hypothesis. If UFFD work resumes, use a synthetic malformed sender to test **MemoryFd completeness** directly instead of retesting the already-gated shared+anonymous zone combination.
