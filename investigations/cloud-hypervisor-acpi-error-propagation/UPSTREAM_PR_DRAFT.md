# Upstream PR record

Updated: 2026-08-10

Upstream PR: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8709
State: maintainer approved; canonical CI / merge pending
Head: `e9c86bacee14a2fd6fe871dc678c6b3f1ac4012a`
Review: Rob Bradford — approved with `Thanks!` on 2026-08-10
Canonical CI run: `31367757232` — in progress at last check

## Title

`vmm: Propagate ACPI table construction errors`

## Submitted body

Fixes #8666.

Several operations in ACPI table construction currently use `unwrap()` / `expect()`, allowing failures to panic the VMM. This PR gives the ACPI path its own error type and propagates ACPI construction failures through `vm::Error::CreatingAcpiTables`.

```text
checked_add / write_slice / fw_cfg
              ↓
          acpi::Error
              ↓
               ?
              ↓
    CreatingAcpiTables
              ↓
        Vm::boot() Err
```

I added `next_table_address()` to consolidate the repeated checked table-address additions. It returns `AddressOverflow` instead of unwrapping a failed addition.

A missing `fw_cfg` device, `fw_cfg` delivery failures, and guest-memory write failures propagate through the same ACPI error path. Making the builders return `Result` accounts for most of the `Ok(...)` / `?` changes.

Fixed SRAT structure sizes are checked at compile time. Other internal VMM and table-construction invariants remain unchanged.

### Validation

`next_table_address()` has a test covering normal addition and overflow.

The change was also validated with nightly rustfmt, VMM Clippy with warnings denied, x86_64 KVM/MSHV builds, `fw_cfg` and TDX feature builds, AArch64 KVM/MSHV cross-builds, and the repository's RISC-V KVM build.

A VM boot smoke test hasn't been run for this change.

AI assistance: ChatGPT (GPT-5.6-Sol) was used for source review, test design, and patch refinement.

## Why this body is intentionally small

The public body is not the full investigation report. Its job is to let a maintainer answer quickly:

```text
what was wrong?
    ↓
where do failures go now?
    ↓
what helper/design choice matters?
    ↓
what was actually validated?
    ↓
what was not tested?
```

Detailed Rust explanations, discarded poisoned-lock handling, exact receipts, and scope defenses live in `README.md` and `REFINEMENT.md`.

## Writing decisions retained for later submissions

- PR prose does not need commit-message 72-column wrapping; GitHub renders normal Markdown paragraphs.
- First person is acceptable when it sounds more natural (`I added ...`).
- Arrow diagrams earn space when they replace prose and expose control flow immediately.
- Avoid abstract words when simpler source-level language works. For example, the final opening dropped `fallible` and simply names `unwrap()` / `expect()`.
- State the evidence ceiling explicitly. `A VM boot smoke test hasn't been run` makes the compile/test matrix more credible, not less.
- Do not preload every possible scope defense into the PR. `Other internal VMM and table-construction invariants remain unchanged` is enough until a reviewer asks for the detailed taxonomy.
- Correct factual overclaims even late in drafting. The final opening does not imply that fw_cfg `add_acpi()` previously panicked; that I/O error already propagated and is now re-homed under `acpi::Error`.

## Review outcome so far

The first maintainer review approved the submitted head without requested changes. This is evidence that the final narrowing and concise public explanation were sufficient for initial review; it is not a reason to weaken the retained internal evidence or to assume canonical CI/merge before those events occur.
