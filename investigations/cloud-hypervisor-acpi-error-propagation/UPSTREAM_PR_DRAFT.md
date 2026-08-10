# Proposed upstream PR

## Title

`vmm: propagate ACPI table construction errors`

## Body

Fixes #8666.

ACPI table construction now returns typed errors for runtime failures that previously panic. The error path covers checked table-address overflow, poisoned allocator / interrupt-controller / fw_cfg locks, missing fw_cfg, guest-memory writes, and fw_cfg I/O failures.

```text
runtime ACPI failure
        |
        v
    acpi::Error
        |
        v
vm::Error::CreatingAcpiTables
        |
        v
     VM boot error
```

`next_table_address()` centralizes the repeated checked guest-address calculations. Fixed SRAT type-size checks are compile-time assertions, while the existing programming and table-layout invariants remain assertions. Successful ACPI generation and architecture-specific boot ordering remain unchanged.

Testing covers:

- the focused `next_table_address()` success/overflow unit test;
- Clippy with `kvm,fw_cfg,tdx` and warnings denied;
- x86_64 KVM and MSHV builds;
- fw_cfg and TDX builds;
- AArch64 KVM and MSHV cross-builds;
- nightly rustfmt and diff checks.

## Internal drafting notes

The upstream body intentionally stays concise. Detailed rationale for each error variant, retained invariant, call-site propagation step, and validation boundary lives in the adjacent `README.md`.

The preferred tone is descriptive present tense. The PR body avoids explaining routine Rust `Result` / `Ok` / `?` propagation that is already apparent from the diff.
