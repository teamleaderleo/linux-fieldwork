# Cloud Hypervisor QCOW backing direct-I/O portability — 2026-08-11

## TL;DR

Current upstream main deliberately opens QCOW backing files with `O_DIRECT` whenever the top-level disk has `direct=on`.

The ordinary same-filesystem path is well covered. The landing PR exercises raw backing files, QCOW2 backing files, three-layer backing chains, concurrent reads, cross-cluster reads, copy-on-write paths, and reads around the backing virtual-size boundary with direct I/O enabled. `AlignedFile::try_clone()` also preserves the probed alignment when nested QCOW backing readers duplicate their data fd.

The remaining portability question is narrower:

> If the overlay image lives on a filesystem that supports `O_DIRECT`, while one backing image lives on a filesystem that rejects `O_DIRECT`, should `direct=on` reject the whole chain or permit a buffered backing layer?

Current code chooses rejection implicitly because the same `direct_io` boolean is inherited by every backing file open. The public disk config has one `direct` field and no per-backing override.

This round does **not** classify that as a defect. The first probe is a mixed-filesystem acceptance matrix plus project-contract review.

## Exact source boundary

- Upstream: `cloud-hypervisor/cloud-hypervisor`
- Branch: `main`
- Exact head: `915d359f97475b1a39d8561f8db514da9e692d19`
- Relevant landed PR: https://github.com/cloud-hypervisor/cloud-hypervisor/pull/8673
- Historical direct-I/O regression/fix: https://github.com/cloud-hypervisor/cloud-hypervisor/issues/8007 and https://github.com/cloud-hypervisor/cloud-hypervisor/pull/8012
- Execution in this Fieldwork round: source, issue, PR, and test review only
- External-contact state: **disabled / no contact performed**

## Why this surfaced

The April QCOW direct-I/O regression was caused by a refactor bypassing the aligned I/O wrapper. Maintainer analysis at the time explicitly said backing files were unaffected because they were opened without `O_DIRECT`.

PR 8673 changes that premise intentionally: backing fds now receive `O_DIRECT` when the top-level QCOW disk requests direct I/O.

That is a sensible performance correction, but it creates a new capability dependency across the whole backing chain.

## Current code path

`parse_qcow()` obtains:

```text
direct_io = file.is_direct()
```

and passes that same value into `BackingFile::new()`.

For every backing layer, `BackingFile::new()` performs:

```text
OpenOptions::new()
    .read(true)
    + O_DIRECT when direct_io=true
```

then wraps the fd in `AlignedFile`.

For nested QCOW2 backing files, parsing recurses with the same direct state. When the parsed backing is converted into the shared reader, `inner.raw_file.file().try_clone()` clones the `AlignedFile`, preserving both the fd and its probed alignment.

So the direct-I/O intent now propagates consistently through the chain.

## Negative result: alignment state is retained

One tempting failure hypothesis was that nested QCOW conversion cloned only the raw fd and lost the alignment tracked by `AlignedFile`.

Current source defeats that hypothesis:

- `QcowRawFile::file()` returns `&AlignedFile`;
- `AlignedFile::try_clone()` clones the underlying file and copies the alignment value;
- `Qcow2Backing.data_file` is itself an `AlignedFile`;
- raw backing readers also retain an `AlignedFile` directly.

Retain this negative result so future work does not reopen an already-resolved ownership question.

## Negative result: direct backing-chain behavior has broad same-filesystem tests

The PR 8673 test diff wraps a large existing backing corpus in a real `O_DIRECT` capability gate and runs direct variants including:

- raw backing reads;
- QCOW2 backing reads;
- multi-queue concurrent QCOW2 backing reads;
- three-layer backing chains;
- partial writes and copy-on-write preservation;
- punch-hole fallthrough;
- reads beyond and across backing virtual-size boundaries;
- cross-cluster reads.

The helper probes an actual aligned `O_DIRECT` read instead of treating any open error as proof that the filesystem lacks support.

This is strong evidence for the same-filesystem case.

## Mixed-filesystem question

The test helper answers one question for the temporary directory used by the test:

```text
does this filesystem support aligned O_DIRECT reads?
```

A real backing chain can span multiple mounts or filesystem types because backing paths are ordinary paths and relative paths are resolved against the image containing them.

That yields four capability combinations:

| overlay filesystem | backing filesystem | current expected open behavior |
|---|---|---|
| direct yes | direct yes | succeeds, direct throughout |
| direct yes | direct no | backing open fails |
| direct no | direct yes | top-level direct open/probe fails before backing semantics matter |
| direct no | direct no | direct request fails |

The second row is the useful discriminator.

## Competing contract interpretations

### Contract A — `direct=on` applies to the whole logical disk chain

Under this interpretation every participating image must support direct I/O. Failing the chain is correct because silently buffering one backing layer would violate the caller's direct-I/O request.

Promotion signal: project docs, historical discussion, or other backends consistently treat `direct` as an end-to-end guarantee.

### Contract B — `direct=on` applies to the writable/top-level image

Under this interpretation backing layers may remain buffered while the active overlay is direct. This matches the behavior before PR 8673 and may preserve mixed-storage deployments.

Promotion signal: existing docs or callers describe direct I/O as a property of the configured image file rather than every transitively referenced backing file, or a real deployment depends on buffered read-only backing layers.

### Contract C — explicit mixed policy

A future API could distinguish top-level direct I/O from backing-layer policy. This is broader API design and has no current justification from this source pass.

Keep it outside the first probe.

## First probe

Use two disposable mounts/filesystems with known opposing capability:

```text
A: O_DIRECT read succeeds
B: O_DIRECT read fails with a capability-related error
```

Create:

1. raw backing on B;
2. QCOW2 overlay on A referencing that raw backing;
3. a control pair with both files on A.

Open both with the same QCOW options and `direct=on,backing_files=on`.

Record:

- top-level open result;
- exact backing-open errno/error chain;
- whether `direct=off` succeeds for the mixed pair;
- whether same-A direct control succeeds;
- resolved backing path;
- filesystem types and mount options;
- `statx` / direct-I/O alignment information where available.

Repeat with a QCOW2 backing layer if the raw discriminator is useful.

## Stop condition

Close as a negative/intentional result if project contract evidence says direct I/O is end-to-end and the mixed-filesystem failure is clear at open time with a useful error.

Promote only if one of these appears:

- documented semantics imply the backing layer may be buffered;
- current behavior regresses a supported mixed-filesystem deployment;
- error reporting hides which backing layer lacks direct support;
- capability differs across nested layers in a way that produces runtime I/O failure after a successful open;
- an equivalent backend handles the same direct-I/O request with a conflicting policy.

## Reusable lesson

A boolean propagated through a recursive storage graph can silently become an **all-nodes capability requirement**.

When a feature flag crosses backing files, parents, children, or layered devices, test heterogeneous capability across nodes instead of testing only an all-capable graph.

That lens transfers beyond QCOW to migration transports, memory backends, nested device chains, and host-feature fallbacks.
