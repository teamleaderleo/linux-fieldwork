# BuildKit rootless mountpoint reproducibility and compatibility resolution

## TL;DR

BuildKit issue `6686` exposed a real reproducibility defect: the same exec could leave different empty runtime mountpoint directories in the output depending on whether the worker was rootful or rootless. The first submitted candidate fixed the mismatch by cleaning rootful runtime-created stubs from the finalized OCI mount list. Upstream replaced that candidate with the opposite convergence direction: preserve historical rootful output and recreate mountpoints removed by rootless spec conversion after the container exits.

The replacement is larger because the desired contract is larger. It preserves existing digest-affecting rootful output, preserves rootless command-time behavior, handles both runc and containerd executors, carries correct ownership, and skips nested mount destinations that a runtime would have created inside another mounted filesystem.

The durable lesson is to separate **mechanism discovery** from **canonical-behavior selection**. Source reading and execution can prove why two paths differ. They may still leave a policy question: when `A != B`, should `A -> B` or `B -> A`? In a mature content-addressed build system, compatibility history can decide that direction.

## Explain like I'm five

A rootful BuildKit worker asks the container runtime to mount `/sys`. If the image has no `/sys` directory, the runtime creates an empty `/sys` as the place where the mount goes. That empty directory can remain in the resulting layer after the container exits.

A rootless worker removes the `/sys` mount from the OCI spec because it cannot safely perform the same mount setup. The runtime therefore has no reason to create `/sys`, so the rootless result can omit the directory.

That gives two different outputs for the same build:

```text
rootful:  proc/  sys/
rootless: proc/
```

The first candidate said: clean the runtime-created `sys/` from rootful output.

The replacement says: after a successful rootless container exits, create the empty `sys/` that the rootful runtime historically leaves behind.

Both make the outputs equal. The second keeps old rootful output unchanged.

## Why care

BuildKit exports content-addressed images. A missing or added empty directory changes the uncompressed layer contents, which changes the layer diff ID and can change the resulting image identity. Linux Fieldwork reproduced this exact difference on matching rootful and rootless workers.

This means an apparently tiny cleanup edit can be a compatibility change even when ordinary applications rarely care whether an empty lower-root `/sys` directory exists. BuildKit now has an explicit `compatibility-version` mechanism for digest-affecting image assembly behavior, so this class of output change has a project-level compatibility cost.

## Current state

- State: `COMPLETE`
- Canonical internal carrier: `teamleaderleo/linux-fieldwork#229`
- Original submitted upstream PR: https://redirect.github.com/moby/buildkit/pull/7033
- Replacement upstream PR: https://redirect.github.com/moby/buildkit/pull/7039
- Canonical upstream issue: https://redirect.github.com/moby/buildkit/issues/6686
- Original submitted head: `069b2d673b4cba9fb195e8229b93432947d79ace`
- Replacement head at review: `6ed70f8651124b07578deab2d427758474902773`
- Replacement state at 2026-08-13: open, mergeable
- Cleanup state: no external state changed by this record
- Next safe action: retain this as the post-upstream design resolution; update only if the replacement design changes before merge
- External-contact state: upstream issue and original PR were human-created; this record performs no upstream interaction

## Timeline

### 2026-04-10 — compatibility-version work begins

Upstream PR `6681`, authored by Tonis Tiigi, introduced solve-wide compatibility-version support for image and OCI exports, historical golden outputs, and release compatibility testing.

### 2026-04-11 — the rootless divergence is filed

While working on compatibility output, Tonis filed issue `6686`: rootless and rootful workers produced different images because runtime mountpoint stubs differed. The compatibility test work used a workaround that pre-created `/proc` and `/sys` so the golden output did not depend on the rootless/runtime discrepancy.

### 2026-04-27 — compatibility-version lands with the workaround

The larger compatibility feature merged. The rootless discrepancy remained a separate known issue.

### April through early August — known debt, no public design discussion

The issue remained open with no comments and no equivalent public pull request found during the Linux Fieldwork investigation. The existing compatibility test workaround removed immediate pressure to resolve the design.

### 2026-08-03 onward — Linux Fieldwork reproduces and isolates the defect

Matching rootful and rootless BuildKit daemons built from the same source, using the native snapshotter and runc, reproduced the exact divergence. The `RUN` layer differed only by the runtime mountpoint member set:

- rootful committed `proc/` and `sys/`, both mode `0755`, uid/gid `0`;
- rootless committed `proc/` and omitted `sys/`.

The investigation traced ownership to `executor/runcexecutor.Run()` plus `util/rootless/specconv.ToRootless()`: rootless conversion explicitly removes mounts whose destination begins with `/sys`.

### 2026-08-12 — minimal candidate submitted

PR `7033` moved mount-stub cleanup registration until after rootless conversion and fed the cleanup helper the finalized OCI mount list. The intended invariant was:

> if the runtime creates an absent path solely as a mount stub, clean that empty runtime-created path afterward.

The candidate was one commit, three files, `+54/-1`.

### 2026-08-13 — upstream chooses the opposite convergence direction

About 36 hours after the submitted PR opened, Tonis opened PR `7039`, explicitly replacing it. The replacement branch retained the original submitted commit as its first parent, then added a second commit implementing a different policy:

> preserve historical rootful output; for rootless execution, remember mounts removed by rootless conversion and recreate their rootfs mountpoints only after successful container exit.

The original PR was then closed with a pointer to the replacement.

## Intent and precedent

Two pieces of upstream context change how the defect should be evaluated.

First, BuildKit's compatibility documentation describes `compatibility-version` as pinning **digest-affecting image assembly behavior** for image and OCI exporters. Historical versions preserve old output behavior where BuildKit intentionally changed image-producing semantics.

Second, the compatibility integration test introduced alongside that mechanism deliberately pre-creates `/proc` and `/sys` with an explanatory comment: doing so prevents the rootless versus non-rootless runtime `/sys` stub difference from contaminating compatibility goldens.

That history proves the mountpoint difference was already known to interact with output identity. It also explains why changing the rootful side is heavier than the code diff suggests.

## Question

When rootful and rootless BuildKit executions leave different runtime mountpoint members in the resulting rootfs, which output should become canonical without creating a new digest-affecting compatibility change?

## Source

- Project: `moby/buildkit`
- Original candidate base: `f05303b3ec7bdcd3e3e93ea2527cbe1aea704b59`
- Original candidate: `069b2d673b4cba9fb195e8229b93432947d79ace`
- Replacement base reviewed: `30fe6a5116cf8d595a4ffcc96f22464dcf04d1c4`
- Replacement head reviewed: `6ed70f8651124b07578deab2d427758474902773`
- Primary source surfaces:
  - `executor/runcexecutor/executor.go`
  - `executor/containerdexecutor/executor.go`
  - `executor/stubs.go`
  - `util/rootless/specconv/specconv_linux.go`
  - `client/compatibility_test.go`
  - `solver/llbsolver/compat/compat.go`
  - `docs/build-repro.md`
- Internal exact evidence carrier: `teamleaderleo/linux-fieldwork#229`

## Environment and prior execution boundary

The original Linux Fieldwork execution used matching rootful and rootless BuildKit daemons from the same source revision, native snapshotter plus runc, a deterministic locally compiled static helper, `FROM scratch`, no registry input, no cache, and exporter timestamp rewriting to a fixed epoch.

That execution proved the runc/native mechanism. It did not provide live containerd-worker execution before submission.

## Baseline behavior

`MountStubsCleaner` records mount destinations that are absent before execution. Its deferred cleanup removes only paths that remain empty runtime-created stubs and restores parent timestamps.

Before the submitted candidate, runc registered this cleanup from BuildKit's explicit executor mount list before the OCI spec was finalized. Default OCI runtime mounts such as `/proc` and `/sys` therefore fell outside that cleanup ownership list.

Later, rootless conversion mutated `spec.Mounts` and removed `/sys*`. Rootful runc still received the `/sys` mount and created its absent lower-root mountpoint. Rootless runc did not receive that mount and did not create the path.

## Candidate A — clean according to the finalized spec

The submitted candidate moved cleanup registration after OCI spec generation and rootless conversion, then adapted `spec.Mounts` into the existing cleaner.

### Why this was reasonable

It followed a strong local invariant:

> cleanup should use the mount set the runtime will actually execute.

It reused an existing ownership-aware cleaner rather than adding a second filesystem mutation path. It preserved image-provided `/proc` and `/sys`, because the cleaner records only paths absent before execution. It was small enough to review and test narrowly.

The implementation also made rootful and rootless output converge in the proven runc/native case.

### What it silently chose

The candidate did more than fix stale-state ordering. It chose a canonical output policy:

```text
rootful has sys/    rootless lacks sys/
        |                   |
        +------ clean ------+
                  |
                  v
             both lack sys/
```

That changes existing rootful output for affected builds whose input rootfs lacks a runtime mountpoint such as `/sys`.

## Replacement B — restore rootless mountpoints after execution

The replacement changes rootless spec conversion to return the destinations it removed. The executors remember those destinations and, after a successful container exit, create the corresponding top-level mountpoint stubs with the ownership and mode that rootful execution historically leaves behind.

Conceptually:

```text
rootful has sys/    rootless lacks sys/
        |                   |
        |              remember removed /sys
        |                   |
        |              execute without /sys
        |                   |
        |              create sys/ afterward
        |                   |
        +-------------------+
                  |
                  v
             both have sys/
```

### Why creation happens after the container exits

Creating `/sys` before rootless execution would change command-time behavior. Rootfully, `/sys` is a read-only runtime mount. Rootlessly, if BuildKit merely pre-created an ordinary directory while omitting the mount, a build command could write into that directory and persist data into the layer.

The replacement integration test therefore executes a write attempt equivalent to:

```sh
touch /sys/written || true
```

and requires the final result to contain only the expected empty runtime mountpoints. It also checks mode and ownership parity.

### Why nested destinations are skipped

If the removed destinations include both `/sys` and `/sys/fs/cgroup`, a rootful runtime creates the nested destination inside the mounted `/sys` filesystem. The nested path is therefore not a lower-root artifact. Recreating both paths in the rootfs would invent content that rootful execution never leaves there.

The replacement creates only the correct lower-root mountpoint boundary.

### Why both executors are touched

The discrepancy originates in rootless spec conversion, not solely in runc cleanup. Carrying the removed-destination information through the conversion allows both runc and containerd executor paths to preserve the same intended result.

## Compatibility impact of Candidate A

The practical impact has two different scales.

### Runtime/application impact

For many ordinary containers, deleting an empty lower-root `/sys` is likely invisible during normal runtime because a real sysfs mount covers that path. This is why the candidate can feel cosmetically different rather than operationally dangerous.

### Content-addressed output impact

For BuildKit, the member set of a layer is observable output. An absent `sys/` changes the uncompressed layer contents and therefore the diff ID. The Linux Fieldwork reproduction already demonstrated different diff IDs arising from exactly this missing-member divergence.

Consequences can include changed image identity, compatibility goldens, signatures or attestations tied to digests, registry artifacts, exact reproducibility checks, and cache relationships that depend on exported content identity.

The blast radius is bounded: an input image that already contains `/sys` is preserved by the existing cleaner and would not lose that image-owned directory. The affected class is specifically builds where a runtime mountpoint is absent before an exec and historically survives as a runtime-created lower-root stub.

## Would deeper source reading have produced the replacement design before submission?

### What deeper reading could have caught

A broader pre-submission compatibility pass could have found two strong warnings:

1. BuildKit had recently introduced explicit compatibility versions for digest-affecting image output.
2. The compatibility integration suite already pre-created `/proc` and `/sys` specifically to avoid this rootless/rootful mountpoint divergence.

Those facts should raise the question:

> Are we allowed to change the historical rootful result, or should rootless converge toward it?

That question is now a reusable review check.

### What deeper reading would still leave open

Those facts do not mechanically derive the entire replacement implementation. They establish that Candidate A has a compatibility cost. They do not uniquely dictate:

- whether upstream prefers a new compatibility version or preservation of current rootful output;
- whether mountpoints should be created before or after execution;
- how rootless conversion should expose removed destinations;
- how nested destinations should be represented;
- which executor paths should own recreation.

The decisive input was project policy: preserve existing rootful output and avoid a compatibility-version bump for this fix. Once that policy was explicit, the larger implementation followed from command-time parity and executor coverage.

So the retained lesson is neither "read everything first" nor "small fixes are naive." The better lesson is:

> read enough adjacent compatibility history to identify policy questions, then make those questions explicit before treating one convergence direction as purely mechanical.

## Why the dormant issue moved immediately after a patch appeared

The public sequence supports a common open-source dynamic.

Before a candidate exists, a known defect with a local workaround can remain low-pressure debt. The issue records the problem; the workaround lets the main feature ship; maintainers have many other priorities.

A concrete candidate changes the cost model. Someone now has to decide whether the proposed behavior is acceptable. The patch turns an abstract follow-up into a reviewable policy choice.

Here, the submitted candidate had already done much of the expensive discovery work:

- proved the defect still existed;
- isolated the differing filesystem member;
- traced the owner to rootless spec conversion and runtime mountpoint creation;
- found the existing cleanup helper;
- demonstrated one working convergence direction;
- supplied a small signed commit as a concrete branch point.

The replacement branch literally retained that submitted commit as its first parent and expressed the alternate policy in the next commit. This is strong evidence that the first candidate functioned as a useful branch point even though its final behavior was superseded.

The useful process concept is **activation energy**: a small, executable proposal can make a dormant design question cheap enough and urgent enough for a maintainer to resolve.

## Reusable review lessons

### 1. Reproducibility fixes need a convergence direction

When two modes produce different outputs, proving the difference is only half the job. Ask which side is historical, documented, compatibility-pinned, or otherwise canonical.

### 2. Tiny diffs can have large semantic reach

A two-line movement inside cleanup code can alter layer member sets and digests. Review output identity separately from implementation size.

### 3. Compatibility can preserve accidental history

An empty runtime-created directory may look like disposable residue. Once it has appeared in exported content for years, a mature content-addressed system can treat it as compatibility behavior.

### 4. Separate command-time parity from final-output parity

Pre-creating a missing rootless mountpoint would make the final tree look right while making the build command see a writable directory where rootful execution sees a read-only mount. Test both execution semantics and retained output.

### 5. Cleanup ownership and output ownership are different questions

Candidate A asked whether BuildKit could identify a runtime-created stub and safely clean it. The answer can be yes while project policy still says the historical artifact should remain.

### 6. Adjacent backends can reveal the true abstraction boundary

A runc-local fix can prove the mechanism while a rootless-conversion-level fix better serves both runc and containerd. Before widening a patch, distinguish "same bug" from "same implementation owner."

### 7. A replaced patch can still be successful fieldwork

A candidate that reveals the right mechanism, supplies evidence, and forces the missing design decision has produced value even when upstream chooses another implementation.

### 8. Dormant issues often need a forcing function, not more prose

A tested patch or reproduction can turn a four-month-old known issue into a one-day design decision because it collapses uncertainty and creates a concrete review obligation.

### 9. Maintainer context is an input, not magic foresight

The public record does not support the idea that the final replacement implementation sat ready for months. A more ordinary explanation fits: the maintainer knew the defect, had a workaround, worked on other priorities, then derived the stronger design once a concrete candidate made the policy choice immediate.

### 10. Preserve the superseded branch as evidence

The original candidate remains useful for understanding the mechanism, the tempting local invariant, the compatibility cost, and the exact point where policy changes the implementation direction.

## Evidence boundary

Demonstrated:

- exact runc/native rootful-versus-rootless missing-member divergence;
- the source mechanism that removes `/sys` in rootless conversion;
- Candidate A restores parity in the proven runc/native matrix;
- upstream replacement explicitly chooses historical rootful output to avoid a compatibility-version bump;
- replacement code handles removed-mount reporting, post-exit recreation, nested destinations, ownership, runc, containerd, and an integration test for command-time write behavior;
- the replacement branch includes the original submitted commit as its first parent.

Inferred:

- many ordinary applications would rarely observe the missing lower-root `/sys` during normal runtime;
- the original patch acted as the immediate forcing function for upstream design attention. The timing and parent relationship strongly support this interpretation, while private maintainer thought and scheduling are unknowable.

Unproven here:

- ecosystem frequency of base images that omit `/sys`;
- size of real-world cache churn from Candidate A;
- live containerd-worker execution of the replacement at this review point;
- final merge state or later revisions of PR `7039`.

## Next step

Treat the original candidate as superseded implementation provenance and the replacement as the current upstream design. If PR `7039` changes before merge, compare the new head against `6ed70f8651124b07578deab2d427758474902773` and update only the changed design conclusions.

For future reproducibility investigations, add an explicit pre-candidate discriminator:

> If two modes differ, which existing output is compatibility-protected, and what evidence would justify changing it?

## Authority

No upstream interaction is performed by this investigation record. Third-party issue and pull-request references use `redirect.github.com` to keep controlled-repository interaction surfaces quiet if text is later reused there. The original upstream issue and PR were created manually by the human contributor.