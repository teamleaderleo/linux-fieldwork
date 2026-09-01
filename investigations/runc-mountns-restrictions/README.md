# runc read-only rootfs without a mount namespace

## TL;DR

At exact runc commit `0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`, validation rejects masked paths and read-only paths when no mount namespace is configured, but accepts `Readonlyfs` under the same condition.

The full source path shows why that matters: OCI `root.readonly` becomes `configs.Config.Readonlyfs`, but `linuxStandardInit.Init()` calls `finalizeRootfs()` only when `configs.NEWNS` is present. The read-only remount therefore never runs when the mount namespace is omitted. The request is accepted and silently ignored.

A retained candidate rejects `Readonlyfs` without `NEWNS` and adds focused positive and negative controls. The controlled fork has a separate characterization PR so current behavior and the repair remain independently reviewable.

## Explain like I'm five

A configuration asks runc to lock the container's root filesystem.

```text
root.readonly = true + no mount namespace
→ runc accepts the configuration
→ runc skips the function that locks the root
→ the container root stays writable
```

The candidate rejects the impossible combination instead of saying yes and quietly doing nothing.

## Why care

`root.readonly` is an explicit OCI isolation and integrity request. Silently leaving the root writable breaks the configuration contract and can invalidate security assumptions made by callers, policy engines, and operators.

An early validation error is observable and actionable. Silent acceptance is not.

## Current state

- State: `REPAIR`
- Exact target source head: `0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`
- Controlled fork characterization PR: `teamleaderleo/runc` PR #1
- Current characterization head: `10d1f2e8a13d07e3119f10ee298b909cf7456f01`
- Linux Fieldwork PR: #424
- Retained candidate patch: `0001-reject-readonlyfs-without-private-mount-namespace.patch`
- Retained candidate test: `mountns_restrictions_test.go`
- Latest authoritative result: complete source-path review plus committed characterization; candidate execution pending
- First incomplete step: apply the candidate to a clean controlled-fork branch and execute the focused validator package
- Cleanup state: no processes, mounts, containers, packages, or temporary files were created by this source-read pass
- Next safe action: candidate application and focused execution; run the broader no-`NEWNS` mount-setup audit independently
- External-contact state: unauthorized and not made

## Intent and precedent

The validator already rejects two neighboring requests without `NEWNS`:

- `MaskPaths`;
- `ReadonlyPaths`.

That check lives in `libcontainer/configs/validate/validator.go:security()`.

The read-only-root source path is:

1. `libcontainer/specconv/spec_linux.go` copies `spec.Root.Readonly` to `configs.Config.Readonlyfs`.
2. `libcontainer/configs/validate/validator.go` currently performs no `Readonlyfs`/`NEWNS` compatibility check.
3. `libcontainer/container_linux.go` passes `Namespaces.CloneFlags()` to bootstrap; an omitted mount namespace does not acquire `CLONE_NEWNS` elsewhere.
4. `libcontainer/nsenter/nsexec.c` unshares only the requested clone flags.
5. `libcontainer/rootfs_linux.go:prepareRootfs()` selects `chroot()` when `NEWNS` is absent and `pivotRoot()` when it is present.
6. `libcontainer/standard_init_linux.go` calls `finalizeRootfs()` only inside `if Namespaces.Contains(NEWNS)`.
7. `finalizeRootfs()` is the only path in this flow that observes `config.Readonlyfs` and calls `setReadonly()`.

The missing validator rule therefore permits a request whose implementation is structurally skipped.

## Question

Should runc reject `Readonlyfs=true` when no mount namespace is configured because that configuration cannot reach the root-readonly implementation?

## Source

- Project: `opencontainers/runc`
- Resolved commit: `0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`
- Controlled fork: `teamleaderleo/runc`
- Fork base: `main@0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`
- Characterization branch: `fieldwork/mountns-validation-characterization`
- Characterization head: `10d1f2e8a13d07e3119f10ee298b909cf7456f01`
- Relevant paths:
  - `libcontainer/configs/validate/validator.go`
  - `libcontainer/configs/validate/validator_test.go`
  - `libcontainer/specconv/spec_linux.go`
  - `libcontainer/container_linux.go`
  - `libcontainer/configs/namespaces_syscall.go`
  - `libcontainer/nsenter/nsexec.c`
  - `libcontainer/rootfs_linux.go`
  - `libcontainer/standard_init_linux.go`
- Retrieval date: 2026-08-03

## Environment

- Source review: environment-independent
- Focused validator test: no mount or container privileges required
- Runtime integration: should run in a disposable privileged Linux VM or nested private mount namespace
- Target Go directive: `go 1.25.0`
- Exact execution environment: pending

## Baseline behavior

The controlled-fork characterization places three neighboring settings under one discriminator with no configured mount namespace:

```text
MaskPaths      → validation error
ReadonlyPaths  → validation error
Readonlyfs     → validation succeeds
```

The source path then proves that `Readonlyfs` is not merely delayed. `standard_init_linux.go` skips `finalizeRootfs()` when `NEWNS` is absent, and no other reviewed path applies the root-readonly remount.

## Cross-context review

The bounded adjacent pass covered:

1. **OCI conversion** — `root.readonly` reaches `Config.Readonlyfs` unchanged.
2. **Validation precedent** — neighboring path restrictions already require `NEWNS`.
3. **Namespace creation** — bootstrap receives only configured clone flags.
4. **Root transition** — no `NEWNS` selects `chroot()`.
5. **Read-only implementation** — `finalizeRootfs()` is gated on `NEWNS` and contains the `Readonlyfs` action.
6. **Broader mount setup** — `prepareRoot()` still changes propagation and bind-mounts the rootfs before the root transition.
7. **Joined namespace semantics** — `Contains(NEWNS)` accepts either a newly created namespace or a namespace joined by path.

Items 6 and 7 can affect broader design decisions but do not erase the demonstrated silent-ignore defect. They remain independent follow-up lanes.

## Hypothesis or candidate

The retained candidate adds:

```go
if config.Readonlyfs && !config.Namespaces.Contains(configs.NEWNS) {
    return errors.New("unable to make rootfs read-only without a private MNT namespace")
}
```

It accepts:

- `Readonlyfs=true` with a configured mount namespace;
- configurations that do not request a read-only rootfs.

It rejects:

- `Readonlyfs=true` with the mount namespace omitted.

It preserves:

- existing masked-path and read-only-path behavior;
- the current root-readonly implementation when a mount namespace exists;
- unrelated namespace and mount validation.

It leaves open:

- whether the error should say `configured` rather than `private`, because a namespace path may join an existing namespace;
- whether joining the caller's own mount namespace should be rejected through a stronger identity check;
- broader no-`NEWNS` rootfs setup behavior;
- runtime compatibility across privileged, rootless, and user-namespace modes.

## Reproduction

```sh
git checkout 0c87c02ff02123f1bc2cd1b3f850f94e5b8de983

# Current behavior carrier.
go test ./libcontainer/configs/validate \
  -run TestValidateMountNamespaceRestrictionCoverage -count=1

# Candidate carrier.
git apply /path/to/0001-reject-readonlyfs-without-private-mount-namespace.patch
go test ./libcontainer/configs/validate \
  -run TestValidateReadonlyfsMountNamespaceBoundary -count=1

gofmt -w libcontainer/configs/validate/mountns_restrictions_test.go
git diff --check
```

After the focused package passes, run the ordinary runc Go, lint, and integration gates on the exact candidate head.

A runtime control should compare an attempted write inside the rootfs under:

- omitted mount namespace plus `root.readonly=true` on baseline;
- omitted mount namespace plus candidate validation;
- private mount namespace plus `root.readonly=true`;
- private mount namespace plus `root.readonly=false`.

Run those controls only inside an outer disposable mount namespace or VM.

## Results

### Demonstrated source result

At the resolved source commit:

- validation accepts `Readonlyfs` without `NEWNS`;
- bootstrap does not create an unrequested mount namespace;
- standard init skips `finalizeRootfs()` without `NEWNS`;
- the read-only-root action therefore does not execute;
- the validator has no early error for this unsupported combination.

### Materialized characterization

Controlled-fork PR #1 records the current validator asymmetry. Its workflow carrier at head `10d1f2e8a13d07e3119f10ee298b909cf7456f01` is intended to execute the focused test independently of the candidate.

### Candidate state

The candidate patch and exact test are retained in this investigation. They are `target-test-prepared`, not yet `target-executed`.

### Corrected claim

An earlier draft incorrectly said the no-`NEWNS` path reached a shared root remount. Complete source review disproved that wording. The accurate defect is silent omission: the remount is skipped entirely.

## Branch candidates

1. **Direct validator repair — high confidence.** Apply the retained patch and execute focused plus ordinary gates.
2. **Error-contract polish — bounded.** Decide whether the error should refer to a `configured MNT namespace` rather than a `private` one.
3. **Joined namespace identity — independent.** Test a namespace path that points to the caller's current mount namespace and one that points to a separate namespace.
4. **No-`NEWNS` rootfs setup audit — independent, high value.** Trace propagation, bind-mount, chroot, cleanup, and parent visibility with disposable-namespace controls.
5. **Runtime behavior matrix — required before compatibility claims.** Execute privileged, rootless, user-namespace, private-mount, and joined-mount variants.

## Interpretation

The narrow candidate now has a simpler and stronger basis than the initial draft: runc accepts a requested property that its own control flow deliberately does not apply under that namespace configuration.

The direct validator repair matches neighboring precedent and turns silent contract loss into an explicit configuration error.

The broader mount-setup and joined-namespace questions remain worth investigating in parallel. They should not be used to delay or overstate the narrow result.

## Evidence boundary

This generation establishes source flow, validator behavior as encoded in a controlled-fork test, and a reviewable candidate patch.

It does not yet establish:

- live-kernel write behavior;
- candidate test execution;
- ordinary runc gate results;
- rootless or cross-kernel compatibility;
- the correct policy for joining an existing mount namespace;
- the safety of every no-`NEWNS` rootfs setup operation;
- maintainer intent beyond current source and adjacent validation precedent.

## Next step

Continue in parallel:

1. apply the candidate on a clean owned-fork branch and execute focused and ordinary gates;
2. execute the characterization workflow and retain its exact receipt;
3. open the independent no-`NEWNS` rootfs setup audit;
4. inspect joined mount-namespace identity before final error wording is frozen.

Move the candidate to technical review only after exact-head execution and complete-diff inspection.

## Authority

No upstream issue, pull request, patch submission, comment, review, reaction, email, or other external interaction has been authorized or created. All work is confined to owned repositories and quiet public-source observation.
