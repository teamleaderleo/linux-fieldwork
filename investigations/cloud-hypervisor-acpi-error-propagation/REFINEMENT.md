# ACPI error propagation refinement history

Updated: 2026-08-10

Canonical issue: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/issues/8666
Upstream PR: https://redirect.github.com/cloud-hypervisor/cloud-hypervisor/pull/8709
Final upstream head: `e9c86bacee14a2fd6fe871dc678c6b3f1ac4012a`
Final diff SHA-256: `76c53e120c22dab4886904a875e3aba86ae6d49130e4080cbcdb46ad3df56466`
Current upstream state: maintainer approved; canonical CI / merge pending

## What changed after the first green candidate

The first validated candidate propagated:

- checked ACPI table-address overflow;
- allocator / interrupt-controller / fw_cfg mutex poisoning;
- missing fw_cfg;
- guest-memory writes;
- fw_cfg I/O.

A later review asked a useful scope question: why should three mutexes inside ACPI adopt typed poison handling when the rest of the VMM overwhelmingly keeps `lock().unwrap()`?

The AArch64 chain made the asymmetry obvious:

```text
controller presence -> unwrap
mutex poison        -> ACPI error
VGIC presence       -> unwrap
```

The poison handling was therefore removed before submission. This was not a claim that `PoisonError` is impossible or that propagating it would be invalid Rust. It was a scope decision: handling those locks would make this patch define a broader internal VMM error policy that the canonical issue does not require.

Removing poison handling also removed the only new error from `create_facp_table()`, which let that function and the TDX ACPI builder return to their original non-fallible signatures.

## Static-size cleanup

The SRAT structure-size checks remain compile-time assertions, now beside the types they constrain.

The duplicate `test_generic_initiator_affinity_size` runtime test was removed because the same 32-byte property is already enforced by the const assertion. `test_next_table_address` remains because it tests two actual behaviors: successful address addition and overflow classification.

## Final error set

```text
AddressOverflow
MissingFwCfg
GuestMemory(source)
FwCfg(source)
```

The final product remains exactly two files and shrank from the earlier 99+/53- refinement to 73+/48-.

## Final validation model

The final product bytes were frozen before the last validation refinements. A separate validation carrier checks the exact product diff identity and then checks out the exact product commit before running quality/backend/architecture gates.

Primary v2 run `31367122335` / job `93387811635` passed nightly rustfmt, the focused address-helper test, Clippy with warnings denied, x86_64 KVM/MSHV, fw_cfg, TDX, and AArch64 KVM/MSHV. Artifact `9054647068` has digest `sha256:bd30f0644818a73f2827a5eed5a497c58210ec87c6e0c2e8abacc934d65c010b`.

Independent review then noticed Cloud Hypervisor's required `all-green` CI gate depends on `build-riscv64`. Validation-only head `6cc1559217fb5e7e73246095b2b5d2c10d1c4476` added the repository's canonical RISC-V KVM build and passed without changing product bytes.

A VM boot smoke test was not run and is explicitly disclosed upstream.

## Packaging rule learned here

Do not put canonical issue references into iterative internal commit messages. Temporary commits can churn heavily during review and each pushed reference can create timeline noise. Keep `Fixes #...` for the final frozen upstream commit and the intentional upstream PR relationship.

For internal GitHub interaction prose, use `redirect.github.com` for third-party canonical links. Repository Markdown may retain richer technical history without creating those interaction backlinks.

## Upstream review outcome

Rob Bradford approved the final upstream head with `Thanks!` and no requested source changes. Canonical CI run `31367757232` was in progress at the last check.

This approval is a useful confirmation of the narrowing decision: the final patch answered the issue without carrying the neighboring mutex-poison policy into public review.

## Disposition

The submitted product is frozen and maintainer-approved. Further source changes should respond to attributable CI failure, merge/rebase requirements, or a new maintainer request—not stylistic preference alone.
