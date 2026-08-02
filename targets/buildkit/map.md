# BuildKit Target Map

## In simple words

BuildKit turns Dockerfiles and other build inputs into a content-addressed execution graph. It decides when local files, images, secrets, caches, workers, and subprocesses become part of a build and how their results are reused or cleaned up.

## Source identity

- Canonical repository: `https://github.com/moby/buildkit.git`
- Canonical branch: `master`
- Current research revision: `275d6864ff0ce91a06225af5f5b012887bd257cf`
- Controlled fork: `https://github.com/teamleaderleo/buildkit.git`
- Fork default branch: `master`
- Fork head observed: `df0761886a20e368d75e0aa6bb3f20874f58b692`
- Current-main relation at observation: canonical `master` was five commits ahead and the fork had no unique commits relative to that merge base.
- Imported source tree: not yet present under `upstream/`; repository reads in this round are pinned to the canonical commit above.

Preserve the fork default branch. Create an exact canonical-base research branch when execution or a candidate begins.

## Why it recurs

BuildKit crosses graph construction, local-session file transfer, provenance, content stores, cache identity, rootless workers, OCI runtimes, cancellation, process cleanup, mounts, snapshotters, and distributed build execution.

## Relevant programmes

- [`Rootless execution, namespaces, and mounts`](../../programmes/rootless-execution/STATUS.md)
- [`Services, processes, and resources`](../../programmes/services-resources/STATUS.md)
- [`Filesystems, archives, and disk images`](../../programmes/filesystems-images/STATUS.md)
- [`Ecosystem contributions and upstream fixes`](../../programmes/ecosystem-contributions/STATUS.md)

## Mapped lanes

- LF-04 — mount propagation and teardown
- LF-06 — namespace capability lifecycle
- LF-15 — OverlayFS copy-up and metadata
- LF-22 — cgroup v2 delegation and resource cleanup
- LF-23 — cancellation, subprocess, and file-descriptor cleanup
- LF-39 — foundational-library boundary corpus
- LF-40 — package metadata, provenance, and verification

## Current investigations

- [Avoid loading an unused local build context](../../investigations/buildkit-unused-context-lazy-load/README.md)

## Secondary research queue

- `moby/buildkit#2855` — rootless `--oci-worker-no-process-sandbox` cancellation, surviving build commands, and zombie ownership. Reproduce on current `master` before treating the 2022 report as current behavior.
- Solver execution deduplication after client cancellation.
- Rootless worker process ancestry and subreaper behavior.
- Cache and provenance differences between an absent input and an unused input.

## Source and test surfaces

Begin with:

- `frontend/dockerfile/builder/build.go`
- `frontend/dockerui/config.go`
- `frontend/dockerfile/dockerfile2llb/convert.go`
- `frontend/dockerfile/dockerfile2llb/convert_copy.go`
- `frontend/dockerfile/dockerfile2llb/validations.go`
- Dockerfile integration tests and gateway-client fixtures

For rootless cancellation, keep a separate source map across the solver, executor, OCI worker, containerd/runc calls, rootlesskit process tree, and test harnesses.

## Policy boundary

This map authorizes reading and controlled-fork research only. No upstream issue, pull request, comment, review, email, or other BuildKit interaction is authorized.