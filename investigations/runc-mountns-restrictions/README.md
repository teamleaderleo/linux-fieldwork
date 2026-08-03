# runc mount-namespace restriction boundary

## TL;DR

At exact runc commit `0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`, configuration validation rejects masked paths and read-only paths when the container does not have a private mount namespace, but it accepts `Readonlyfs` under the same namespace boundary.

The source path is coherent enough to justify a candidate: OCI `root.readonly` becomes `configs.Config.Readonlyfs`; rootfs setup uses `chroot()` rather than `pivot_root()` when `NEWNS` is absent; finalization then remounts `/` read-only. A container-only read-only guarantee cannot be isolated in a shared mount namespace. The retained candidate rejects `Readonlyfs` without `NEWNS` and adds private/shared namespace controls.

The next step is to apply the candidate to the controlled fork, flip the characterization expectation, and run focused plus ordinary runc gates. In parallel, the wider no-`NEWNS` mount-mutation path deserves a separate source and execution pass rather than being silently folded into this patch.

## Explain like I'm five

Imagine two rooms sharing the same light switch. runc already refuses some requests that would change the shared switch while pretending the change belongs to only one room.

Current example:

```text
root.readonly = true + no private mount namespace
→ validator accepts the request
→ runtime later remounts the container root
→ the mount operation is not isolated to a private namespace
```

The candidate says: if the room does not have its own switch, reject the request instead of promising a private read-only result.

## Why care

The affected boundary is the container root mount and the parent mount namespace. A false or non-isolated read-only guarantee can produce one of two bad outcomes: the container remains writable despite the requested contract, or mount changes become visible outside the intended container boundary. Either result is more consequential than an early configuration error.

## Current state

- State: `REPAIR`
- Exact target source head: `0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`
- Controlled fork characterization PR: `teamleaderleo/runc` PR #1
- Exact characterization head: `7a452ee96af0844523f1fd606d36fbdb48ea8bfd`
- Retained candidate patch: `0001-reject-readonlyfs-without-private-mount-namespace.patch`
- Retained candidate test: `mountns_restrictions_test.go`
- Latest authoritative gate or artifact: complete source-path review plus committed characterization test; execution is pending
- First incomplete step: apply the candidate to a clean controlled-fork branch and execute the focused validator package
- Cleanup state: no processes, mounts, containers, packages, or temporary files were created by this source-read/materialization pass
- Next safe action: candidate application and focused execution; independently map no-`NEWNS` rootfs mount mutations
- External-contact state: unauthorized and not made

## Intent and precedent

The validator already treats mount-namespace isolation as required for two neighboring security settings:

- `MaskPaths` without `NEWNS` is rejected;
- `ReadonlyPaths` without `NEWNS` is rejected.

That rule lives in `libcontainer/configs/validate/validator.go` inside `security()`.

The root-readonly setting follows this source path:

1. `libcontainer/specconv/spec_linux.go` copies OCI `spec.Root.Readonly` into `configs.Config.Readonlyfs`.
2. `libcontainer/rootfs_linux.go:prepareRootfs()` prepares and bind-mounts the rootfs.
3. When `NEWNS` is present, the child uses `pivotRoot()`; otherwise it uses `chroot()`.
4. `finalizeRootfs()` calls `setReadonly()` when `Readonlyfs` is true.
5. `setReadonly()` remounts `/` with `MS_BIND | MS_REMOUNT | MS_RDONLY`.

Observed source behavior therefore crosses the same mount-isolation boundary as the already validated path restrictions. The candidate extends the existing invariant rather than inventing a new configuration model.

## Question

Should runc reject `Readonlyfs=true` when the configuration does not contain a private mount namespace, because the runtime cannot provide an isolated container-only root remount under that configuration?

## Source

- Project: `opencontainers/runc`
- Requested revision: current `main` at investigation start
- Resolved commit: `0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`
- Candidate source commit: pending clean controlled-fork application
- Controlled fork: `teamleaderleo/runc`
- Controlled fork base: `main@0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`
- Characterization branch: `fieldwork/mountns-validation-characterization`
- Characterization head: `7a452ee96af0844523f1fd606d36fbdb48ea8bfd`
- Relevant paths:
  - `libcontainer/configs/validate/validator.go`
  - `libcontainer/configs/validate/validator_test.go`
  - `libcontainer/specconv/spec_linux.go`
  - `libcontainer/rootfs_linux.go`
- Import metadata: public source read through the GitHub connector on 2026-08-03

## Environment

- Distribution and release: source-read stage is environment-independent; target execution environment pending
- Kernel and architecture: pending target execution
- Shell: pending target execution
- Privileges: the focused validator test requires no container creation or mount privileges; runtime integration controls will require an isolated privileged Linux runner
- Container, virtual machine, or host context: controlled-fork CI or disposable Linux VM for runtime controls
- Relevant tool versions: runc source at the exact commit above; Go version to be retained from the executing gate

## Baseline behavior

The controlled-fork characterization adds one table covering three neighboring settings with no private mount namespace:

```text
MaskPaths      → validation error
ReadonlyPaths  → validation error
Readonlyfs     → validation succeeds
```

The third result is encoded as current behavior in PR #1. The branch intentionally does not select the repair yet.

The source then carries an accepted `Readonlyfs` request into `finalizeRootfs()`, where `/` is remounted read-only. Without `NEWNS`, the child selected `chroot()` instead of `pivotRoot()` and does not own a private mount namespace.

## Cross-context review

The bounded adjacent pass covered five contexts:

1. **OCI conversion** — `root.readonly` reaches `Config.Readonlyfs` without a namespace compatibility check.
2. **Validator siblings** — masked and read-only paths already require `NEWNS`.
3. **Root transition** — `NEWNS` selects `pivotRoot()`; its absence selects `chroot()`.
4. **Final root remount** — `Readonlyfs` unconditionally reaches `setReadonly()` after the root transition.
5. **Broader mount setup** — `prepareRoot()` changes propagation and bind-mounts the rootfs before the transition.

The fifth context can change a broader decision but does not require widening this patch. It creates a separate branch candidate: determine which rootfs setup mount mutations are intended or safe when runc is explicitly configured to share the caller's mount namespace.

## Hypothesis or candidate

The candidate adds one precise validation rule:

```go
if config.Readonlyfs && !config.Namespaces.Contains(configs.NEWNS) {
    return errors.New("unable to make rootfs read-only without a private MNT namespace")
}
```

It accepts:

- `Readonlyfs=true` with a private mount namespace;
- existing configurations that do not request a read-only rootfs.

It rejects:

- `Readonlyfs=true` with no configured private mount namespace.

It preserves:

- the existing error and behavior for `MaskPaths` and `ReadonlyPaths`;
- the existing rootfs implementation when `NEWNS` exists;
- unrelated namespace and mount validation.

It deliberately leaves for separate work:

- joining an existing external mount namespace by path;
- whether a joined namespace should be treated as sufficiently private for this guarantee;
- the broader safety and compatibility of `prepareRoot()` mutations with no `NEWNS`;
- runtime-level integration coverage across rootless, user-namespace, and privileged configurations.

## Reproduction

The focused characterization and candidate commands are prepared as follows:

```sh
git checkout 0c87c02ff02123f1bc2cd1b3f850f94e5b8de983

# Baseline characterization artifact:
cp /path/to/mountns_restrictions_characterization_test.go \
  libcontainer/configs/validate/mountns_restrictions_test.go
go test ./libcontainer/configs/validate \
  -run TestValidateMountNamespaceRestrictionCoverage -count=1

# Candidate application:
git apply /path/to/0001-reject-readonlyfs-without-private-mount-namespace.patch
go test ./libcontainer/configs/validate \
  -run TestValidateReadonlyfsMountNamespaceBoundary -count=1

gofmt -w libcontainer/configs/validate/mountns_restrictions_test.go
git diff --check
```

After the focused package passes, run the repository's ordinary Go test and lint gates on the exact candidate head. A runtime integration probe should use a disposable mount namespace or VM so a failed hypothesis cannot alter the operator's live mount table.

## Results

### Demonstrated source result

At the resolved source commit:

- validator coverage is asymmetric across three neighboring mount restrictions;
- `Readonlyfs` reaches a remount operation;
- no `NEWNS` selects `chroot()` rather than `pivotRoot()`;
- the validator has no explicit `Readonlyfs`/`NEWNS` compatibility check.

### Materialized characterization

Controlled-fork PR #1 retains a table-driven test at exact head `7a452ee96af0844523f1fd606d36fbdb48ea8bfd`. It records current behavior and is a characterization carrier, not the selected implementation.

### Not yet demonstrated

No focused Go test, ordinary repository gate, or privileged runtime integration probe has been executed for the candidate in this investigation generation. The candidate remains `target-test-prepared`, not `target-executed`.

## Branch candidates

1. **Direct validator repair — high confidence.** Apply the retained patch, flip the shared-namespace expectation, and execute package plus repository gates.
2. **No-`NEWNS` rootfs mutation audit — high value, separate question.** Trace propagation, bind-mount, chroot, cleanup, and visibility to the parent namespace with negative controls.
3. **Joined mount namespace semantics — medium value.** Distinguish absence of `NEWNS` from joining a namespace by path and decide whether the validation predicate should use `Contains`, `IsPrivate`, or a more explicit authority rule.
4. **Runtime integration matrix — required before strong compatibility claims.** Compare private mount namespace, joined namespace, shared host namespace, rootless user namespace, and ordinary privileged creation in disposable environments.

## Interpretation

The narrow candidate is supported by source structure and existing validator precedent. It is the smallest change that makes the read-only-root contract fail early when isolation is absent.

The source review also reveals a broader question that should not be hidden inside the narrow repair: rootfs preparation performs mount propagation and bind operations even on the no-`NEWNS` path. That may be intentional legacy behavior, constrained by caller setup, or a separate defect class. It needs its own exact execution and history review.

## Evidence boundary

This generation establishes source flow, current validator behavior as encoded in a controlled-fork test, and a reviewable candidate patch.

It does not establish:

- actual runtime behavior on a live kernel;
- whether every no-`NEWNS` configuration leaves the root writable or changes a shared mount;
- behavior when joining an existing mount namespace by path;
- rootless compatibility;
- cross-kernel behavior;
- complete runc test-suite results;
- maintainer intent beyond the current source and adjacent validator precedent.

## Next step

Continue both useful branches in parallel:

1. create a clean candidate branch in `teamleaderleo/runc`, apply the retained patch, run focused and ordinary gates, and classify any setup failure separately from product behavior;
2. open a separate bounded scout for the no-`NEWNS` rootfs mount-mutation path, with a disposable-namespace runtime probe and parent-mount visibility controls.

The candidate should move toward technical review only after exact-head execution and complete-diff inspection. The broader audit should remain independent so a larger finding cannot destabilize the narrow repair without evidence.

## Authority

No upstream issue, pull request, patch submission, comment, review, reaction, email, or other external interaction has been authorized or created. All work is confined to owned repositories and quiet public-source observation.
