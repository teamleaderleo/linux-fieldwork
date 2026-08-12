# Cloud Hypervisor TDVF parser candidate composition

Updated: 2026-08-12
Owning issue: #590
Worker/variant: LF-R590C
Fieldwork base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: STAGED COMPOSITION

## Purpose

Three independent parser-side #590 owners are already proven in isolation against the same exact Cloud Hypervisor source:

- LF-R590G: GUID-table structural subtraction bounds;
- LF-R590A: descriptor section-table-vs-file validation before metadata-driven allocation;
- LF-R590T: validity-safe raw section type decoding before constructing the Rust enum.

All three live in `arch/src/x86_64/tdx/mod.rs`. This carrier validates their selected composition and is not a fourth product owner.

## Deterministic materialization

The workflow starts from exact Cloud Hypervisor source and retrieves the already-tested candidate materializers from immutable Fieldwork tested commits:

- G script from `04f5eb6fc9733c4bd4a7f1892316139efeece2cb`;
- A script from `be334d724140b11d04e587e2392dffeb468bc2cd`;
- T script from `f19cadeb69333f941dda611f2ddc81d68560517a`.

It applies them in order `G -> A -> T` and records the diff after each layer plus the final combined diff. The expected interaction is deliberate:

- G modifies earlier GUID discovery and adds its error variants/tests;
- A inserts the section-table file-range check immediately before the existing section allocation/read block;
- T replaces that allocation/read block with an all-integer `RawTdvfSection` read + validated conversion, leaving A's preceding range check intact.

## Focused composition matrix

The combined source must pass all owning candidate regressions/controls:

- G: undersized GUID table -> typed error;
- G: oversized entry -> typed error;
- G: 18-byte footer-only fallback control;
- A: 1 GiB-advertising tiny descriptor -> `InvalidDescriptorRange` before allocation;
- A: valid one-section control;
- T: unknown raw type 7 -> `InvalidSectionType(7)`;
- T: all currently represented types `0..=6` and `0xffffffff` remain accepted.

## Broad gates

- full `arch` + `hypervisor` library tests with package-qualified `tdx,kvm` feature graph;
- hosted `/dev/kvm` permission repaired when present;
- Clippy with `-D warnings`, allowing only already identified exact-current unrelated x86 baseline warning classes;
- nightly rustfmt;
- `git diff --check`;
- complete final parser diff review and SHA-256 artifact receipt.

## Evidence boundary

A green composition proves coexistence only. Product evidence remains owned by LF-R590G, LF-R590A, and LF-R590T. This carrier must not add BFV/CFV source ranges, VMM destination behavior, HOB rules, Payload handling, or section cardinality policy.
