# Cloud Hypervisor x86 SMBIOS EBDA boundary execution

Updated: 2026-08-12
Owning issue: #600
Worker/variant: LF-R600E
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Final validated carrier head: `abf0a092e8c29a5c7632af42da2b09dc1b17042e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Retained candidate origin: Fieldwork `ad8e174673fbe0526bf232942833323a46976a50`
External-contact state: false; Cloud Hypervisor upstream remained read-only

## Disposition

**PROVEN / CANDIDATE READY FOR INDEPENDENT REVIEW.**

Exact current `setup_smbios()` accepts an oversized platform string, returns success with a payload larger than the reserved SMBIOS/EBDA region, and physically writes into high RAM. The retained complete-range guard prevents the overwrite and passes the full `arch` crate test/quality matrix.

## Exact baseline evidence

The probe maps the SMBIOS region plus 128 KiB of high RAM and writes a 64-byte `0xfe` sentinel at `HIGH_RAM_START=0x100000`.

A short manufacturer-string control on exact current source succeeds below the boundary:

```text
SMBIOS_EBDA_CONTROL encoded_size=120 ebda_tail=65536
```

The high-RAM sentinel remains unchanged.

The oversized fixture supplies a 70 KiB ordinary `SmbiosSystem.manufacturer` string through the real `setup_smbios()` encoder. Current source records:

```text
SMBIOS_EBDA_BASELINE encoded_size=71796 ebda_tail=65536 high_ram_prefix=[41, 41, 41, 41, 41, 41, 41, 41, 41, 41, 41, 41, 41, 41, 41, 41]
```

So the encoder returns `Ok(71796)` against a 65,536-byte region and overwrites bytes beginning at `0x100000` with ASCII `A` (`0x41`).

The paired safety invariant is red on baseline:

```text
SMBIOS_BASELINE_INVARIANT_RC=101
SMBIOS_EBDA_INVARIANT result=Ok(71796) high_ram_prefix=[41, 41, 41, 41, 41, 41, 41, 41, 41, 41, 41, 41, 41, 41, 41, 41]
oversized SMBIOS payload must be rejected
```

This is direct guest-memory execution evidence for the #600 overwrite claim.

## Candidate

The selected one-file candidate preserves the earlier #600 policy:

- import `HIGH_RAM_START`;
- add typed `Error::SmbiosTooLarge`;
- in `write_and_incr<T>()`, compute the complete write end with checked arithmetic before touching guest memory;
- reject `end > HIGH_RAM_START`;
- allow a legal write ending exactly at `HIGH_RAM_START`;
- leave MP-table placement behavior unchanged;
- add a typed-error/sentinel regression in the existing SMBIOS unit-test module.

Every variable-length string byte and terminator already flows through `write_and_incr()`, so the same boundary protects long strings without duplicating length arithmetic at every SMBIOS producer.

The historical stored `candidate.patch` from the earlier source-only checkpoint was malformed as a unified-diff artifact (`git apply` reported a corrupt hunk). The exact retained semantics were materialized against exact current source through a guarded script; the candidate policy itself did not change.

Candidate-only diff:

```text
arch/src/x86_64/smbios.rs
+38/-3
sha256:6db403d3108a5581ff1596ea08002c9aa710b3142abda3562b98a9e82f3dd396
```

The complete candidate-only diff was reviewed after formatting. It contains only the import, typed error, common write guard, and focused regression.

## Final execution receipt

Final run/job:

```text
31570779770 / 94032112362
```

Artifact:

```text
9131246556
sha256:97df56bfe714d397e461b14562fd304da7a43bf4c4a978c4c960ea8141625504
```

Toolchains:

```text
Rust 1.89.0
nightly rustfmt 1.99.0-nightly generation used by the run
```

Passed on exact candidate bytes:

```text
exact source pin
baseline short-payload control
ignored physical-overwrite baseline witness
paired baseline invariant expected red
candidate application
candidate oversized-payload invariant
candidate short-payload control
candidate typed SmbiosTooLarge regression
cargo test --locked -p arch
  -> 38 passed; 0 failed; 1 intentionally ignored baseline witness
cargo clippy --locked -p arch --all-targets --
  -D warnings -A unreachable-code -A unused-mut -A unused-variables
cargo +nightly fmt --all -- --check
git diff --check
complete candidate-only diff review
```

The three Clippy allowances are the exact current-source `arch/src/x86_64/regs.rs` uninhabited-register warning classes independently reproduced by the earlier SMBIOS #595 carrier: unreachable code, unused mutable binding, and unused variables. Candidate SMBIOS code introduces no additional warning allowance.

Exact upstream `main` was refreshed after the final run and remains `1af93ac7035cda77cd87b0c18b1134ebb0928052`.

## Adjacent SMBIOS composition

Current source already carries the Type-11 count hardening represented by `Error::TooManyStrings`, satisfying the #593 side of the earlier composition requirement.

The separate #595 embedded-NUL candidate touches the same error enum and `write_string()` while #600 touches the common write boundary. A dedicated stacked composition run is the next bounded check; its result should remain separate from the #600 product candidate.

## Evidence boundary

This is an encoder-level guest-memory correctness proof. KVM execution is unnecessary to establish the physical write across `HIGH_RAM_START` because the real encoder and `GuestMemoryMmap` perform the demonstrated write directly.

Boot-order relevance remains source/history evidence: x86 system-table construction runs after guest payload loading, so high RAM may already contain guest payload bytes when SMBIOS setup executes.

No exploitability or security-boundary claim is made here.
