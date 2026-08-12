# Cloud Hypervisor TDVF BFV/CFV exact-read follow-up

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590X
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: STAGED — workflow intentionally held until current #590 queue drains

## Narrow question

After BFV/CFV source metadata has been accepted, can the firmware source become shorter than the requested `section.data_size` at copy time and make exact-current `read_volatile_from()` return a short byte count that `Vm::populate_tdx_sections()` silently ignores?

This is a distinct runtime/exact-read owner from:

- LF-R590E, which validates BFV/CFV source range against firmware length at parse time;
- LF-R590D, which converts BFV/CFV guest-destination `GuestMemoryError` from panic to `FirmwareLoad`.

A source file can still be shortened or otherwise yield EOF between parse-time validation and the later copy. Even without a race, the current copy API itself is non-exact and reports the completed byte count rather than treating a short source as an error.

## Dependency contract

Exact Cloud Hypervisor pins `vm-memory = 0.18.0`.

In that dependency:

```rust
fn read_volatile_from(...) -> Result<usize, GuestMemoryError>
```

returns the completed byte count, including a short successful copy.

The same trait provides:

```rust
fn read_exact_volatile_from(...) -> Result<(), GuestMemoryError>
```

which turns `completed != expected` into `GuestMemoryError::PartialBuffer { expected, completed }`.

That gives this lane a native exact-read repair path; no new generic I/O error is required.

## Isolation from LF-R590D

R590X should execute as a stacked discriminator:

1. start from exact Cloud Hypervisor source;
2. prove exact-current `read_volatile_from(...).unwrap()` returns e.g. `8` when 16 bytes are requested from an 8-byte ordinary file and that the current caller has no count check;
3. restore exact source;
4. materialize the already-proven LF-R590D destination-propagation candidate as the base layer;
5. record the R590D-only diff/hash;
6. apply the R590X delta only: change the firmware-copy helper from non-exact `read_volatile_from() -> Result<usize>` to `read_exact_volatile_from() -> Result<()>` while retaining `map_err(Error::FirmwareLoad)`;
7. record the X-only diff against the D layer.

This keeps R590D ownership intact: destination failures are already proven there. R590X owns only the remaining successful-short-copy case after the D error path is in place.

## Intended discriminator

Ordinary 4 KiB guest memory, valid guest address, ordinary source files:

- control: 16-byte file, request 16 -> all 16 bytes copied;
- baseline short source: 8-byte file, request 16 -> current API returns `8` without error and the first 8 guest bytes change;
- no-short-success invariant: expected-red on exact-current source;
- D-layer control: invalid guest address still returns `FirmwareLoad(InvalidGuestAddress(...))`;
- X candidate: 8-byte source / 16-byte request returns `FirmwareLoad(PartialBuffer { expected: 16, completed: 8 })`;
- X valid control: 16/16 remains green.

## Candidate shape

Stacked on LF-R590D only:

```rust
fn copy_tdx_firmware_section(
    mem: &GuestMemoryMmap,
    firmware_file: &mut File,
    address: u64,
    size: usize,
) -> Result<()> {
    mem.read_exact_volatile_from(GuestAddress(address), firmware_file, size)
        .map_err(Error::FirmwareLoad)
}
```

The BFV/CFV call site remains `...?;` and no byte count is returned to ignore.

## Stop/split conditions

Do not broaden R590X into:

- parse-time BFV/CFV source range validation (R590E);
- destination error propagation (R590D);
- Payload file reads, which use a separate file/source path;
- firmware-file locking or TOCTOU policy beyond exact-read detection;
- TDVF parser/cardinality/HOB semantics.

## Queue policy

The execution workflow is intentionally not created yet. R590G and the selected VMM composition are already waiting for the limited hosted Actions slots, and unrelated Fieldwork workers are active. This branch therefore advances the next owner without adding runner pressure. When execution is opened, the staging/readme commits should remain `[skip ci]`; only the workflow-bearing execution commit should trigger Actions.
