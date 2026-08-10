# Cloud Hypervisor ACPI error propagation — final review record

Updated: 2026-08-10

Canonical issue: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8666
Upstream PR: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8709
Fieldwork issue: https://github.com/teamleaderleo/linux-fieldwork/issues/444
Final upstream head: `e9c86bacee14a2fd6fe871dc678c6b3f1ac4012a`
Canonical base used for the submitted commit: `a1fcb9f790616ac615f66de73be540b0b20844b1`
Final product scope: `vmm/src/acpi.rs`, `vmm/src/vm.rs`; 73 insertions / 48 deletions
Frozen product diff SHA-256: `76c53e120c22dab4886904a875e3aba86ae6d49130e4080cbcdb46ad3df56466`
Submission state: ready for upstream review

## One-sentence version

Several ACPI construction paths turned ordinary operation failures into VMM panics with `unwrap()` / `expect()`; the submitted change gives ACPI its own typed error boundary and lets those construction failures return through the VM boot `Result` path.

## Grug map

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

Most of the visible `Result`, `Ok(...)`, and `?` churn follows mechanically from deciding that ACPI construction can return an error.

## Final error boundary

The submitted `acpi::Error` has four variants:

```rust
AddressOverflow
MissingFwCfg
GuestMemory(vm_memory::GuestMemoryError)
FwCfg(io::Error)
```

They correspond to concrete operation-level failure channels:

- repeated checked guest-address additions can overflow;
- the ACPI fw_cfg helper receives an `Option`-returning fw_cfg accessor and no longer `expect()`s presence;
- direct guest-memory `write_slice()` calls already return `GuestMemoryError`;
- fw_cfg `add_acpi()` already returns `io::Error`, which is now owned by the ACPI error layer before the VM wraps it.

The VM-level classification is:

```rust
CreatingAcpiTables(#[source] acpi::Error)
```

That replaces the old fw_cfg-only `io::Error` source and also allows the direct guest-memory path to fail through the same VM boot boundary.

## `next_table_address()`

The repeated pattern was effectively:

```text
checked_add(...)
    ↓
Some(address) / None
    ↓
unwrap()
    ↓
None = panic
```

The helper keeps the checked arithmetic but changes the failure exit:

```rust
fn next_table_address(address: GuestAddress, length: u64) -> Result<GuestAddress> {
    address.checked_add(length).ok_or(Error::AddressOverflow)
}
```

It is used for the table-address transitions around FACP, MADT, PPTT, GTDT, MCFG, SPCR, DBG2, TPM2, SRAT, SLIT, IORT, VIOT, XSDT, plus the initial DSDT placement.

The focused unit test executes both behaviors:

```text
0x1000 + 0x20 -> 0x1020
u64::MAX + 1  -> Err(AddressOverflow)
```

The hexadecimal values are just conventional address notation; `0x1000 + 0x20 = 0x1020`.

## SRAT size checks

Two fixed ACPI structure sizes used to be asserted while building an SRAT. They are now compile-time assertions beside the types they constrain:

```rust
const _: () = assert!(size_of::<MemoryAffinity>() == 40);
const _: () = assert!(size_of::<GenericInitiatorAffinity>() == 32);
```

These are properties of the compiled program, not runtime conditions a VM request can recover from.

The old `test_generic_initiator_affinity_size` unit test was removed because the same fixed 32-byte property is now enforced at compile time. The new address-helper test remains because it exercises actual success/error behavior rather than duplicating a static property.

## Why the candidate narrowed before submission

An earlier validated candidate also converted three poisoned mutex locks into `acpi::Error::PoisonedLock`: the FACP allocator, AArch64 interrupt controller, and fw_cfg lock.

That was locally defensible Rust, but review exposed a larger policy question:

```text
most VMM mutexes
    ↓
lock().unwrap()

three ACPI mutexes
    ↓
map poison into ordinary boot error
```

The AArch64 chain made the inconsistency especially visible:

```text
interrupt controller missing -> unwrap
lock poisoned               -> propagated error
VGIC missing                 -> unwrap
```

Keeping that change would make this small issue implicitly decide which internal VMM invariants deserve recoverable error treatment. Cloud Hypervisor broadly retains `lock().unwrap()` for internal mutexes, and the issue did not require a VMM-wide poison policy.

The final candidate therefore leaves mutex poisoning and other pre-existing internal construction invariants unchanged while propagating the operation-level failures above.

This narrowing had useful mechanical consequences:

```text
remove PoisonedLock
    ↓
create_facp_table() no longer needs Result
    ↓
TDX table builder no longer needs Result
    ↓
TDX-only propagation churn disappears
```

The product shrank from the earlier 99+/53- refinement to the submitted 73+/48- diff without removing the core error-boundary fix.

## Why `MissingFwCfg` remains

The VM normally establishes fw_cfg before requesting ACPI delivery, so missing fw_cfg may look invariant-like from the caller.

The helper boundary still receives a `DeviceManager` whose `fw_cfg()` accessor returns `Option`, and the exact ACPI-facing panic site was:

```rust
.fw_cfg().expect("fw_cfg must be present")
```

Converting that local `Option` to `MissingFwCfg` is small, keeps the ACPI helper total over its input type, and does not introduce the broader mutex policy that was removed. The upstream PR deliberately does not advertise a comprehensive panic taxonomy; the fuller distinction is retained here in case review asks why this `expect()` changed while controller/VGIC unwraps did not.

## Successful behavior and invariants

The submitted change does not redesign ACPI tables, reorder them, silently omit required tables, or change architecture-specific boot ordering.

Other internal VMM and table-construction invariants remain unchanged. Examples include AArch64 controller/VGIC presence, serial lookup consistency, IORT layout/alignment assertions, and fw_cfg pointer bookkeeping.

That sentence is intentionally modest. The PR does not claim ownership of every remaining panic site in ACPI or the wider VMM.

## Exact validation

The final product bytes were separated from validation-only workflow commits. The product branch was frozen first; a separate validation carrier checked the exact product diff identity, then detached to the exact product commit before running the matrix.

Primary v2 run:

- run: `31367122335`
- job: `93387811635`
- artifact: `9054647068`
- artifact digest: `sha256:bd30f0644818a73f2827a5eed5a497c58210ec87c6e0c2e8abacc934d65c010b`

Passed on the frozen product bytes:

- exact canonical parent and two-file product scope;
- exact product diff SHA-256 `76c53e120c22dab4886904a875e3aba86ae6d49130e4080cbcdb46ad3df56466`;
- intended error-boundary presence/absence checks;
- nightly rustfmt;
- focused `next_table_address()` unit test with normal addition and overflow;
- VMM Clippy with warnings denied for `kvm,fw_cfg,tdx`;
- x86_64 KVM compile;
- x86_64 MSHV compile;
- fw_cfg feature compile;
- TDX feature compile;
- AArch64 KVM cross-compile;
- AArch64 MSHV cross-compile.

A later validation-only refinement added the repository's canonical RISC-V KVM build after independent review noticed that `build-riscv64` is part of Cloud Hypervisor's required `all-green` CI dependency set. Validation head `6cc1559217fb5e7e73246095b2b5d2c10d1c4476` passed, including the RISC-V build, while the product bytes remained unchanged.

A VM boot smoke test was not run for this change. That limit is stated explicitly in the upstream PR rather than implied away by the compile matrix.

## Final upstream packaging

The submitted branch is one signed commit over the canonical base:

`e9c86bacee14a2fd6fe871dc678c6b3f1ac4012a`

The commit includes:

- a `vmm:` component title;
- why the existing behavior is wrong before the implementation summary;
- `Fixes #8666` only in the final frozen submission commit;
- `Assisted-by: ChatGPT:GPT-5.6-Sol` using the repository's documented agent/model grammar;
- `Signed-off-by: Leo Li <cheerleaderleo@outlook.com>`.

The PR body is intentionally shorter and more human-facing than this record. It uses a small control-flow diagram, names the helper/error boundary, states the validation evidence and the boot-test ceiling, and leaves source archaeology and discarded designs here.

## Rust learning notes

### `unwrap()`

For `Option<T>`:

```text
Some(value) -> value
None        -> panic
```

For `Result<T, E>`:

```text
Ok(value) -> value
Err(error) -> panic
```

It does not propagate an error; it asserts success.

### `Result`, `Ok`, and `?`

```text
child can fail
    ↓
child returns Result
    ↓
parent has no useful local recovery
    ↓
parent returns Result too
```

Then:

- `Ok(value)` packages the successful return;
- `?` extracts success or returns the error upward immediately;
- `map_err(...)` converts a lower-level error into the local error type before propagation.

A large part of the diff is therefore compiler-guided plumbing after the error-boundary decision, not independent new business logic.

## Review/communication lessons from this submission

The public PR and the internal notebook serve different audiences.

The internal record can answer every "why this line?" question, retain discarded designs, record exact receipts, and teach the Rust mechanics. The upstream PR should instead help a maintainer scan the problem, ownership boundary, important helper, and evidence quickly.

A useful two-layer pattern is:

```text
first screen: WTF happens?
    ↓
small arrows + real function/error names

second layer: prove it
    ↓
exact source, receipts, caveats, discarded alternatives
```

The wording pass also established a useful review priority:

```text
factual inaccuracy
    > scope/design ambiguity
    > evidence overclaim
    > style preference
```

Examples:

- correcting the implication that fw_cfg `add_acpi()` was previously a panic mattered because it was factually wrong; the I/O error already propagated and is now re-homed under `acpi::Error`;
- removing poisoned-lock handling mattered because it broadened product policy;
- adding RISC-V mattered because it closed a real required-CI surface;
- changing "ACPI fixes" to "ACPI requires" in a comment did not justify product churn once bytes were frozen.

The stop rule became: once exact product bytes are green, independent review converges, the PR is factually accurate, and remaining objections are stylistic, stop proactively changing the commit. Further product changes should come from a concrete maintainer comment, CI failure, source movement, or new counterexample.

## Backlink hygiene learned the hard way

GitHub interaction surfaces can create backlinks into canonical repositories. Internal issue/PR prose should use `redirect.github.com` for third-party issue/PR/commit links.

Temporary or iterative commit messages should not contain `Fixes #...`, bare `OWNER/REPO#N`, or direct canonical issue links. The canonical reference belongs in the final frozen upstream commit once, and the upstream PR owns its intentional `Fixes #...` relationship.

Repository Markdown files do not create the same GitHub issue-reference backlinks, but using redirect links here too keeps the intent obvious.

## Current disposition

`SUBMITTED UPSTREAM — REVIEW PENDING.`

Do not change the submitted product proactively for stylistic cleanup. Reopen product work for:

- a maintainer-requested code change;
- upstream CI failure attributable to this patch;
- canonical source movement requiring rebase/repair;
- a concrete counterexample to the chosen error boundary;
- a distinct remaining runtime panic that belongs in this issue rather than a successor.
