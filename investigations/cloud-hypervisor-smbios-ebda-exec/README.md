# Cloud Hypervisor x86 SMBIOS EBDA boundary execution

Updated: 2026-08-12
Owning issue: #600
Worker/variant: LF-R600E
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Retained candidate origin: Fieldwork `ad8e174673fbe0526bf232942833323a46976a50`
External-contact state: false; Cloud Hypervisor upstream remains read-only

## Question

Can an accepted x86 SMBIOS configuration exceed the 64 KiB region between `SMBIOS_START=0xf0000` and `HIGH_RAM_START=0x100000`, physically overwrite bytes in high RAM, and still return success from `setup_smbios()`?

## Baseline discriminator

The probe allocates guest memory spanning the SMBIOS region plus 128 KiB of high RAM and writes a 64-byte `0xfe` sentinel at `HIGH_RAM_START`.

It then supplies a 70 KiB ordinary system-manufacturer string through `SmbiosConfig` and calls the real `setup_smbios()` encoder.

The ignored witness requires all of these current-source observations:

```text
setup_smbios() returns Ok
encoded size > HIGH_RAM_START - SMBIOS_START
high-RAM sentinel bytes changed
```

A paired ordinary invariant requires the same long payload to return an error while leaving the sentinel untouched. That invariant is expected to lose on baseline and turn green under the candidate.

The negative control uses the same memory/sentinel arrangement with a short ordinary manufacturer string. It must succeed below the EBDA boundary and leave high RAM unchanged on both baseline and candidate.

## Candidate

The retained one-file candidate is applied exactly from the earlier #600 checkpoint:

- import `HIGH_RAM_START`;
- add typed `Error::SmbiosTooLarge`;
- make `write_and_incr<T>()` compute the complete write end before writing;
- reject writes whose end exceeds `HIGH_RAM_START`;
- retain legal writes ending exactly at `HIGH_RAM_START`;
- strings inherit the check because every byte and terminator passes through `write_and_incr()`;
- leave MP-table behavior unchanged.

The candidate also carries its focused typed-error/sentinel regression in the existing SMBIOS test module.

## Execution gates

```text
exact current source pin
nightly rustfmt of injected fixture
focused test discovery
small-payload control on baseline
ignored baseline physical-overwrite witness
paired safety invariant expected red on baseline
apply exact retained candidate
paired invariant green
small-payload control green
candidate typed-error test green
cargo test --locked -p arch
cargo clippy --locked -p arch --all-targets -- -D warnings
cargo +nightly fmt --all -- --check
git diff --check
complete candidate-only diff + digest
```

Canonical source already contains the Type-11 count hardening represented by `Error::TooManyStrings`, satisfying the #593 side of the earlier composability requirement. #595 embedded-NUL candidate composability will be checked after the primary #600 execution if its retained bytes are still current-applicable.

## Evidence boundary

This is an encoder-level guest-memory correctness proof; no KVM guest is needed to demonstrate bytes crossing `HIGH_RAM_START`. The boot-order claim remains source/history evidence: VM payload loading precedes x86 system-table configuration on the current boot path.

No exploitability or security-boundary claim is made here.
