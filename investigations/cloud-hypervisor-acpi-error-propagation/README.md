# Cloud Hypervisor #8666 — ACPI error propagation review notes

Updated: 2026-08-10

Canonical issue: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8666
Fieldwork issue: https://github.com/teamleaderleo/linux-fieldwork/issues/444
Controlled fork draft PR: https://github.com/teamleaderleo/cloud-hypervisor/pull/3
Validated product carrier: `0a2f55acbd23b7f44899a69132a4236ef9240027`
Validated product patch: `linux-fieldwork/acpi-errors/candidate.patch` in the controlled Cloud Hypervisor fork

## One-sentence version

Cloud Hypervisor's ACPI construction path already uses fallible operations, but several runtime failures are terminated with `unwrap()` / `expect()`; the #8666 candidate gives the private `vmm::acpi` module its own typed error boundary and propagates those failures into the VM's existing `Result` path.

## Mental model

Cloud Hypervisor is building part of the virtual machine's hardware description for the guest. ACPI tables describe CPUs, interrupt/controller information, PCI-related data, NUMA information, power-related interfaces, and other machine properties.

During VM startup the code roughly does this:

```text
VM boot
  |
  +--> build ACPI tables
          |
          +--> create individual tables
          +--> calculate where each table lives in guest address space
          +--> inspect / lock required VMM state
          +--> optionally deliver tables through fw_cfg
          +--> otherwise write generated ACPI bytes into guest memory
```

The issue is about failure behavior inside that process.

Before:

```text
                          +-- checked_add -> unwrap -> PANIC
                          |
                          +-- allocator lock -> unwrap -> PANIC
                          |
VM boot -> ACPI builder --+-- interrupt lock -> unwrap -> PANIC
                          |
                          +-- fw_cfg missing -> expect -> PANIC
                          |
                          +-- fw_cfg lock -> unwrap -> PANIC
                          |
                          +-- guest write -> expect -> PANIC
```

After:

```text
checked address overflow ---------+
allocator poisoned ---------------+
interrupt lock poisoned ----------+
fw_cfg absent --------------------+
fw_cfg lock poisoned -------------+--> acpi::Error
fw_cfg I/O failure ---------------+        |
guest-memory write failure -------+        v
                                 vm::Error::CreatingAcpiTables
                                           |
                                           v
                                       Vm::boot()
                                           |
                                           v
                                  ordinary failed operation
```

The successful ACPI-generation behavior stays the same. The patch changes how genuine runtime failures leave the subsystem.

## Rust vocabulary used by the patch

`Result<T, Error>` means an operation returns either a successful `T` or an error.

`?` means: use the success value, or immediately return the error to the caller.

`.map_err(Error::Variant)?` means: take a lower-level error, classify/wrap it as the local error variant, then return it upward.

`#[source]` is `thiserror`'s way of preserving the lower-level cause, so callers can see a chain such as:

```text
Error creating ACPI tables
  caused by: Failed to write ACPI data to guest memory
  caused by: <vm_memory::GuestMemoryError details>
```

This is established Cloud Hypervisor style. The repository already uses `thiserror`, source errors, and local `Result` aliases throughout VMM code.

## Patch walkthrough

### 1. Imports and local error ownership

The patch adds:

```rust
use std::sync::PoisonError;
use std::{io, result};
use thiserror::Error;
```

and removes the old conditional `use crate::vm` import from `acpi.rs`.

Why:

- `thiserror::Error` is the project's normal typed-error mechanism.
- `io` is needed because fw_cfg's ACPI-delivery API returns `io::Error`.
- `result` supports the local alias `pub type Result<T> = result::Result<T, Error>`.
- `acpi.rs` should own ACPI failures. It should not manufacture `vm::Error` values itself.

The VM layer then owns the interpretation: an `acpi::Error` during VM creation becomes `vm::Error::CreatingAcpiTables`.

An earlier candidate used fully qualified `std::result::Result`; focused Clippy rejected that under Cloud Hypervisor's denied `clippy::absolute_paths`. The final code follows project style with `use std::{io, result};`.

### 2. `acpi::Error`

The candidate adds a private-subsystem error enum:

```rust
#[derive(Debug, Error)]
pub enum Error {
    #[error("ACPI table address overflow")]
    AddressOverflow,

    #[error("ACPI table delivery requires fw_cfg")]
    MissingFwCfg,

    #[error("ACPI {0} mutex is poisoned")]
    PoisonedLock(&'static str),

    #[error("Failed to write ACPI data to guest memory")]
    GuestMemory(#[source] vm_memory::GuestMemoryError),

    #[error("Failed to add ACPI data to fw_cfg")]
    FwCfg(#[source] io::Error),
}
```

Why these variants:

- `AddressOverflow`: `checked_add()` returns `None`, so there is no lower-level error object to preserve.
- `MissingFwCfg`: the fw_cfg accessor returns an `Option`; absence is represented directly.
- `PoisonedLock`: mutex locking returns a poison error after a panic occurred while the protected state was locked. The useful ACPI-level diagnostic is which resource was poisoned.
- `GuestMemory`: preserves the existing `vm_memory::GuestMemoryError` from `write_slice()`.
- `FwCfg`: preserves the existing `io::Error` from fw_cfg's `add_acpi()` operation.

`acpi` remains a private module under `vmm`; `pub enum Error` allows sibling crate code such as `vm.rs` to name the type without making `vmm::acpi` a public external API.

### 3. Local `Result` alias

```rust
pub type Result<T> = result::Result<T, Error>;
```

This gives ACPI functions concise signatures such as `Result<Sdt>` and `Result<GuestAddress>`. It matches common style already used elsewhere in Cloud Hypervisor.

### 4. Poisoned-lock helper

```rust
fn poisoned_lock<T>(_: PoisonError<T>, resource: &'static str) -> Error {
    Error::PoisonedLock(resource)
}
```

The generic `PoisonError<T>` itself is awkward to store because its guard type varies and can carry lifetimes. The important diagnostic here is the affected VMM resource, so the helper converts the generic poison error into an ACPI-owned error containing a static resource name.

Current call sites use fixed strings such as:

- `"allocator"`
- `"interrupt controller"`
- `"fw_cfg"`

### 5. `next_table_address()` helper

```rust
fn next_table_address(address: GuestAddress, length: u64) -> Result<GuestAddress> {
    address.checked_add(length).ok_or(Error::AddressOverflow)
}
```

This replaces repeated code of the form:

```rust
previous_address.checked_add(table_length).unwrap()
```

The original code was already using checked arithmetic, which means overflow had explicitly been considered. `unwrap()` then converted the checked failure into a process panic.

The helper keeps the exact checked arithmetic and gives every ACPI table-address calculation the same failure behavior.

It is used for the address transitions involving FACP, MADT, PPTT, GTDT, MCFG, SPCR, DBG2, TPM2, SRAT, SLIT, IORT, VIOT, XSDT, and the initial DSDT placement.

There is no table-format redesign here. The table sequence and successful addresses stay unchanged.

### 6. Fixed-size ACPI assertions move to compile time

Existing `create_srat_table()` performed runtime assertions that two Rust structs have the byte sizes required by the ACPI specification:

```rust
assert_eq!(size_of::<MemoryAffinity>(), 40);
assert_eq!(size_of::<GenericInitiatorAffinity>(), 32);
```

The candidate moves these to compile-time assertions:

```rust
const _: () = assert!(size_of::<MemoryAffinity>() == 40);
const _: () = assert!(size_of::<GenericInitiatorAffinity>() == 32);
```

These sizes are properties of the compiled program. A particular VM runtime cannot reasonably recover from the program's own ACPI struct definition having the wrong fixed size.

This is a key boundary in #8666:

```text
program / layout invariant -> keep as invariant, preferably compile time
runtime environmental failure -> return an error
```

### 7. `create_facp_table()` becomes fallible

Before:

```rust
fn create_facp_table(...) -> Sdt
```

After:

```rust
fn create_facp_table(...) -> Result<Sdt>
```

The reason is the allocator mutex used while reserving legacy PM1a I/O ports.

Before:

```rust
let mut allocator = device_manager.allocator().lock().unwrap();
```

After:

```rust
let mut allocator = device_manager
    .allocator()
    .lock()
    .map_err(|e| poisoned_lock(e, "allocator"))?;
```

Successful FACP construction is otherwise unchanged; the function now returns `Ok(facp)`.

### 8. `create_acpi_tables_internal()` becomes fallible

Before:

```rust
fn create_acpi_tables_internal(...) -> (Rsdp, Vec<u8>, Vec<u64>)
```

After:

```rust
fn create_acpi_tables_internal(...) -> Result<(Rsdp, Vec<u8>, Vec<u64>)>
```

This is the central internal propagation boundary. If a required child operation fails, there is no honest local recovery that can produce the same valid ACPI table set, so the error travels upward.

The now-fallible FACP call gets `?`, every table-address `checked_add(...).unwrap()` moves through `next_table_address(...)?`, and successful completion returns `Ok((rsdp, tables_bytes, xsdt_table_pointers))`.

### 9. AArch64 interrupt-controller lock

Existing AArch64 code is roughly:

```rust
device_manager
    .get_interrupt_controller()
    .unwrap()
    .lock()
    .unwrap()
    .get_vgic()
    .unwrap();
```

The candidate changes the mutex lock to:

```rust
.lock()
.map_err(|e| poisoned_lock(e, "interrupt controller"))?
```

while retaining the controller-presence and VGIC-presence `unwrap()` calls.

That is deliberate. Source review classified controller/VGIC presence at this point as an initialization invariant for the supported AArch64 ACPI path. A poisoned lock is a runtime lock-acquisition failure. Missing required initialized devices indicate an inconsistent VMM state/programming problem.

### 10. IORT / fixed programming invariants remain explicit

The patch leaves existing assertions in the AArch64 IORT builder for things such as required header size, 8-byte alignment, and the validated PCI-segment encoding bound.

Those checks describe assumptions enforced by Cloud Hypervisor's own table construction and supported device-ID scheme. They are distinct from runtime resources failing to read, write, lock, or allocate.

The patch therefore avoids a broad “replace every panic” rewrite.

### 11. fw_cfg ACPI delivery now returns `acpi::Error`

Before:

```rust
pub fn create_acpi_tables_for_fw_cfg(...) -> Result<(), vm::Error>
```

After:

```rust
pub fn create_acpi_tables_for_fw_cfg(...) -> Result<()>
```

where the local `Result` carries `acpi::Error`.

Changes inside the function:

```text
internal ACPI generation failure -> `?`
missing fw_cfg -> `MissingFwCfg`
poisoned fw_cfg mutex -> `PoisonedLock("fw_cfg")`
fw_cfg `add_acpi()` I/O error -> `FwCfg(io::Error)`
```

This removes lower-layer knowledge of `vm::Error`. The VM caller performs the VM-level wrapping.

### 12. fw_cfg table-pointer bookkeeping is intentionally retained

The fw_cfg path indexes the XSDT table-pointer vector. That was reviewed separately because index operations can panic.

The internal generator always emits core tables and pushes the required table pointers before successfully returning, and the offsets are produced from the same checked address chain. Under a successful return from `create_acpi_tables_internal()`, the required entries are present.

This was therefore retained as an internal construction invariant rather than expanded into another runtime error family.

### 13. Direct guest-memory ACPI creation becomes fallible

Before:

```rust
pub fn create_acpi_tables(...) -> GuestAddress
```

After:

```rust
pub fn create_acpi_tables(...) -> Result<GuestAddress>
```

The initial DSDT address uses `next_table_address()` and internal generation uses `?`.

The two guest-memory writes change from:

```rust
.write_slice(...).expect(...)
```

to:

```rust
.write_slice(...).map_err(Error::GuestMemory)?
```

This directly preserves the error already returned by the `vm-memory` API.

Successful completion returns `Ok(rsdp_addr)`.

### 14. TDX ACPI table generation becomes fallible

Before:

```rust
create_acpi_tables_tdx(...) -> Vec<Sdt>
```

After:

```rust
create_acpi_tables_tdx(...) -> Result<Vec<Sdt>>
```

TDX calls the now-fallible FACP builder, so it must propagate that error. No new TDX-specific ACPI error is invented because the failure belongs to ACPI construction.

### 15. Focused address-overflow test

The patch adds a deterministic unit test for `next_table_address()`:

```text
0x1000 + 0x20 -> 0x1020
u64::MAX + 1 -> Error::AddressOverflow
```

This tests both the successful helper behavior and the exact failure classification.

A broader injected runtime fixture for every lock/write failure would require much more test scaffolding. The current decision is to retain this natural deterministic failure test unless another clean production-level failure fixture appears.

## VM-level changes

### 16. `vm::Error::CreatingAcpiTables` now wraps `acpi::Error`

Before:

```rust
#[cfg(feature = "fw_cfg")]
#[error("Error creating acpi tables")]
CreatingAcpiTables(#[source] io::Error),
```

After:

```rust
#[error("Error creating ACPI tables")]
CreatingAcpiTables(#[source] acpi::Error),
```

Why:

- ACPI creation now has multiple failure sources besides fw_cfg I/O.
- The VM needs one high-level classification: ACPI creation failed.
- `acpi::Error` retains the specific underlying reason and source chain.
- The variant can no longer be gated only on `fw_cfg`, because direct guest-memory ACPI construction can now fail too.

This follows the same layering pattern used elsewhere in the VM error enum: a VM operation variant wraps the lower subsystem's typed error.

### 17. VM `create_acpi_tables()` becomes `Result<Option<GuestAddress>>`

Before:

```rust
fn create_acpi_tables(&self) -> Option<GuestAddress>
```

After:

```rust
fn create_acpi_tables(&self) -> Result<Option<GuestAddress>>
```

The distinction is useful:

```text
Ok(Some(address)) = ACPI created here and RSDP has an address
Ok(None)          = ACPI deliberately comes from another path, such as TDX
Err(error)        = ACPI creation failed
```

The previous `None` behavior for TDX becomes `Ok(None)`. Actual ACPI errors are wrapped with `Error::CreatingAcpiTables`.

### 18. Callers add `?` at the VM boundary

The x86, AArch64, fw_cfg, and TDX callers now use `?` / `map_err(Error::CreatingAcpiTables)?` as appropriate.

This means a failure stops the current VM boot/create operation and returns through the already existing `Vm::boot() -> Result<()>` path.

Architecture-specific ordering remains unchanged. For example, AArch64 still creates ACPI only after vCPU configuration because ACPI needs the vCPU MPIDR values.

## What the patch deliberately does not do

This is not a VMM-wide “remove every unwrap” project.

Many `Mutex::lock().unwrap()` calls remain elsewhere in `vm.rs`, device management, and other subsystems. #8666 is bounded around ACPI construction and its children.

It also does not:

- redesign ACPI tables;
- change successful table contents;
- change the table ordering;
- alter architecture boot ordering;
- silently omit required tables;
- add recovery for internal program/layout invariants;
- refactor every mutex in the VMM;
- change the separate AArch64 cache-topology semantics tracked under #8097 / the cache-index successor.

## Why this is relatively bounded

Most of the diff is mechanical after the error ownership decision is made:

```text
fallible child
    -> parent returns Result
    -> caller uses ?
    -> ACPI error reaches VM boundary
    -> VM wraps as CreatingAcpiTables
```

The product change is limited to `vmm/src/acpi.rs` and `vmm/src/vm.rs` and is 98 insertions / 53 deletions. Much of that is `Result` plumbing and replacing repeated address arithmetic with one helper.

The important review work is deciding which failures are runtime conditions versus program invariants.

## Validation performed on the exact candidate bytes

Validated carrier head: `0a2f55acbd23b7f44899a69132a4236ef9240027`

Focused run/job: `31349013458` / `93336246241` — success

Artifact: `9048345416`

Stored/generated patch SHA-256:

`4d65cdbcb01a72eb09ae3b905a5d4e46b8e140c4cec8d3e1f00380ac5476628d`

The focused gate passed:

- exact guarded source blob verification;
- `git apply --check`;
- exact two-file product scope;
- `git diff --check`;
- nightly rustfmt using the repository's actual formatting behavior;
- focused Clippy with warnings denied;
- execution of the exact `acpi::tests::test_next_table_address` test;
- x86_64 KVM compile;
- x86_64 MSHV compile;
- fw_cfg compile;
- TDX compile;
- AArch64 KVM cross-compile;
- AArch64 MSHV cross-compile;
- regeneration of the product diff;
- byte-for-byte `cmp` of generated diff against the stored candidate patch;
- matching SHA-256 receipts.

The CI evidence therefore applies to the exact patch under review rather than a nearby working-tree state.

## Review checklist / questions an upstream maintainer can reasonably ask

### Does the issue exist in current source?

Yes. The current reviewed source contains runtime `checked_add(...).unwrap()`, allocator / interrupt / fw_cfg lock unwraps, fw_cfg presence `expect()`, and guest-memory write `expect()` calls in ACPI construction.

### Is the error mechanism idiomatic for this repository?

Yes. `thiserror`, `#[source]`, subsystem-local error enums, local `Result` aliases, `map_err`, and VM-level wrappers are all existing Cloud Hypervisor patterns.

### Are lower-level source errors preserved?

Yes where an underlying error exists: `vm_memory::GuestMemoryError` and `io::Error` are retained with `#[source]`. Address overflow and missing fw_cfg originate as `None`, so they receive direct named variants.

### Is successful behavior changed?

The candidate is intended to be success-path equivalent. It changes failure handling and moves two fixed-size assertions to compile time.

### Were all panics converted?

No. The candidate converts runtime failures owned by ACPI construction. Program / validated initialization invariants remain explicit.

### Is the patch tested beyond one unit test?

Yes. The one deterministic runtime unit test exercises the new address helper. The exact product bytes were also compiled/linted/formatted across the relevant architecture/backend/feature surfaces listed above.

### Why one `vm::Error::CreatingAcpiTables` variant instead of many VM variants?

The detailed failures belong to the ACPI subsystem. The VM only needs to know that its ACPI-creation operation failed; the source chain carries the detailed cause.

## Short version for discussion

The candidate does three things:

1. Gives ACPI construction an error type using existing Cloud Hypervisor conventions.
2. Converts genuine runtime failure sites in that call chain from panic/expect behavior into those typed errors, while retaining program invariants.
3. Threads the resulting `acpi::Error` through the existing VM `Result` path as `CreatingAcpiTables`.

The address helper is mostly deduplication: all of the table-specific `checked_add(...).unwrap()` sites represent the same operation and the same overflow failure, so they share `next_table_address()`.

The main design claim is therefore small:

> If ACPI construction encounters a possible runtime failure, fail the VM operation with a typed error instead of panicking the VMM process.

## Evidence boundary

The candidate has strong source review, deterministic address-overflow execution, exact-patch identity, lint/format checks, and compile coverage across KVM/MSHV, x86_64/AArch64, fw_cfg, and TDX surfaces.

A live KVM run injecting every individual ACPI failure mode was not added because no clean natural fixture emerged for those cases. The call propagation is source- and compile-proven; the address-overflow behavior is execution-proven.
