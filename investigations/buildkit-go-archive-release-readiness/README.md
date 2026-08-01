# BuildKit / go-archive release-readiness investigation

State: `ACTIVE — SOURCE AND TEST MAP COMPLETE; EXECUTION PENDING`  
Programme: `filesystems-images`, LF-14 archive extraction and metadata contracts  
Selection record: `research/rounds/2026-08-01-hot-repository-refresh/selection.md`  
External contact: `false`

## Question

Can BuildKit safely move forward from `github.com/moby/go-archive` v0.2.0 now that the two regressions which forced its 2026-07-31 rollback have been repaired on go-archive `main`?

A useful answer requires more than “the new tests pass.” It must distinguish release compatibility, extraction confinement, metadata identity, and performance cost across exact dependency states.

## Exact observed source identities

| Item | Identity |
| --- | --- |
| BuildKit rollback merge | `moby/buildkit` `275d6864ff0ce91a06225af5f5b012887bd257cf` |
| BuildKit rollback test head | `22ea4efb43c3c91651dab7f44d1599c4c42b9412` |
| User BuildKit fork current observed head | `teamleaderleo/buildkit` `df0761886a20e368d75e0aa6bb3f20874f58b692` |
| go-archive implied-parent repair | PR #92 merge `279fa6d455e5a39d8e24e67dd236abee6e2de08b` |
| go-archive absolute-symlink/hard-link repair | PR #93 merge `9e6d2c7c969f4871fe6ded98ae0e28963fde311f` |
| go-archive current observed head | `9e6d2c7c969f4871fe6ded98ae0e28963fde311f` |
| Last known-good dependency | `github.com/moby/go-archive v0.2.0` |
| Regressing dependency | `github.com/moby/go-archive v0.2.1` |
| Released but incomplete comparison | `github.com/moby/go-archive v0.3.0` |

Refresh every identity immediately before execution.

## Confirmed historical failures

### Implied parent directory

An archive may contain:

```text
etc/dnf/
etc/dnf/dnf.conf
```

without a separate `etc/` header. BuildKit's v0.2.1 update failed Dockerfile `ADD` with:

```text
mkdir /etc/dnf: no such file or directory
```

PR #92 restores creation of implied parents even when the final archive entry is itself a directory.

### Absolute symlink within extraction root

Container root filesystems commonly contain:

```text
var/run -> /run
```

The `os.Root` transition treated `/run` as host-rooted and rejected later archive entries under `var/run`. PR #93 adds chroot-like resolution relative to the extraction root for intermediate absolute symlinks and hard-link targets, while retaining the final filesystem operation through `os.Root`.

PR #93 describes this as a compatibility workaround with a resolution/use race confined inside the extraction root. That limitation is part of the release-readiness decision.

## First executable matrix

Run every row from a clean BuildKit checkout containing the rollback's integration tests.

| Candidate | Expected result |
| --- | --- |
| v0.2.0 | all compatibility cases pass; baseline performance |
| v0.2.1 | implied-parent test fails; retained negative control |
| v0.3.0 | record exact implied-parent and absolute-symlink results; do not infer |
| go-archive `9e6d2c7...` | all focused compatibility and containment cases pass |

### Focused BuildKit cases

- `testDockerfileAddArchiveWithImpliedParentDir`
- `testDockerfileAddArchiveThroughAbsoluteSymlink`
- hard-link identity through the absolute symlink

### Direct go-archive cases

- `TestImpliedDirectoryPermissions`
- `TestUntarThroughAbsoluteSymlink`
- hard-link source through absolute symlink
- full `go test ./...`

## Additional discriminators

1. `Untar` and `UnpackLayer` produce the same paths and metadata.
2. Absolute symlink target exists before extraction versus is created by the archive.
3. Entry after the symlink is a directory, regular file, symlink, and hard link.
4. Implied parents versus explicit parent headers.
5. Relative symlink escape remains rejected before and after the compatibility fallback.
6. A relative escape followed by an absolute symlink remains rejected.
7. Whiteout conversion, opaque-whiteout tracking, and deferred directory timestamps use the same resolved root-relative path.
8. Hard-link inode identity and contents survive extraction and local output export.
9. File modes, UID/GID behavior under `NoLchown`, and timestamps remain stable.
10. Two immediate runs produce the same tree digest and leave no temporary root, process, mount, socket, trace file, or cache owned by the investigation.

## Performance probe

The release decision must record at least:

- wall-clock duration for the focused tests;
- extraction duration for a synthetic archive with many deep sibling paths;
- syscall count or a defensible proxy for repeated path resolution;
- comparison against v0.2.0 under the same filesystem and cache state;
- separate cold and immediate-rerun results.

Do not make a performance claim from BuildKit's full integration-suite duration alone.

## Proposed commands

The exact test selector must be confirmed from the refreshed checkout. Expected shape:

```sh
git clone https://github.com/teamleaderleo/buildkit.git buildkit-go-archive-readiness
cd buildkit-go-archive-readiness
git remote add upstream https://github.com/moby/buildkit.git
git fetch upstream
git checkout --detach 275d6864ff0ce91a06225af5f5b012887bd257cf

# For each dependency candidate, use a clean module state.
go mod edit -replace github.com/moby/go-archive=/absolute/path/to/go-archive-candidate
go mod tidy

# Confirm exact test names and package before running.
go test ./frontend/dockerfile/dockerfile_integration_test.go -run 'AddArchiveWithImpliedParentDir|AddArchiveThroughAbsoluteSymlink'
```

For go-archive:

```sh
git clone https://github.com/moby/go-archive.git go-archive-candidate
cd go-archive-candidate
git checkout 9e6d2c7c969f4871fe6ded98ae0e28963fde311f
go test ./...
```

These commands are a source map, not an execution receipt. Record the actual package selector, Go version, OS, kernel, filesystem, command output, statuses, and cleanup when run.

## First-failure ownership

Classify a red run before editing product code:

- stale BuildKit fork missing rollback tests;
- wrong test package or unsupported direct-file `go test` invocation;
- module replacement/tidy drift;
- Go toolchain mismatch;
- unavailable integration sandbox/buildctl/backend;
- fixture construction error;
- actual go-archive product behavior;
- BuildKit integration behavior outside go-archive.

## Promotion signals

### Ready for dependency bump preparation

- exact current go-archive head passes direct and BuildKit focused gates;
- v0.2.1 fails the retained implied-parent control;
- relative escapes remain rejected;
- metadata and hard-link identity match v0.2.0;
- performance delta is measured and acceptable;
- full go-archive tests pass after cleanup and rerun;
- no equivalent BuildKit bump is already active.

### Hold

- v0.3.0/current main still fails a compatibility case;
- confinement weakens or an escape negative control changes;
- metadata differs without an explicit contract decision;
- performance regression is large enough to alter the release decision;
- the defining BuildKit integration boundary cannot be executed.

### Split

- source fixes are correct but BuildKit requires separate integration or performance work;
- a release/tagging action belongs to go-archive maintainers while BuildKit can only retain tests;
- whiteout or deferred-metadata behavior reveals an independent defect.

## Current result

Source and carrier review is complete. Both fixes required by the rollback are merged to go-archive `main`, and BuildKit already contains the exact high-value integration fixtures. Execution has not begun in this conversation runtime, so no pass, failure, performance, or release recommendation is claimed yet.

## Next safe step

Refresh the user's BuildKit fork from exact upstream rollback head, materialize go-archive v0.2.0/v0.2.1/v0.3.0/current-main candidates, and run the focused matrix with explicit cleanup between candidates.

## Authority

Fork refreshes, local branches, local module replacements, tests, benchmarks, and Linux Fieldwork records are internal technical work. Do not open or comment on a BuildKit or go-archive issue or pull request without explicit authorization.
