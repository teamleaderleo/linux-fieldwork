# runc exec cgroup-v2 fallback containment parity

## TL;DR

Current runc has two ways to place an exec process into a requested cgroup-v2 sub-cgroup. The early `CLONE_INTO_CGROUP` path opens the subpath through `opencontainers/cgroups.OpenFile`, which lexically anchors the requested name under the manager directory. If that start fails, runc retries without the cgroup fd and later calls `Manager.AddPid`; cgroups v0.0.8 builds that target with `filepath.Join` and checks containment with plain `strings.HasPrefix`.

Those operations can interpret the same traversal-shaped input differently. For a container cgroup ending in `foo` and request `../foo2`, the fd-opening path targets a child named `foo2` under `foo`, while the fallback `AddPid` calculation can target prefix-colliding sibling `foo2`. The cgroup-v1 sibling form is already reported upstream; the v2 capability-dependent parity question appears separate.

The next step is a privileged cgroup-v2 probe with both a child and prefix-colliding sibling present, comparing normal `CLONE_INTO_CGROUP` execution against a controlled fallback where cgroupfd start is made unavailable.

## Explain like I'm five

`runc exec --cgroup NAME` means "put this new process in a cgroup below the container's own cgroup."

There are two roads to do that on cgroup v2:

1. put the process there while creating it;
2. create the process first and move it afterward if road 1 cannot be used.

For an odd path such as `../foo2`, the two roads currently clean and check the path differently. That means kernel capability can potentially decide which cgroup the same command reaches.

Literal discriminator:

```text
container base: /.../foo
child:          /.../foo/foo2
sibling:        /.../foo2
request:        ../foo2

cgroup-fd path -> /.../foo/foo2
fallback path  -> /.../foo2   (prefix collision can pass HasPrefix)
```

## Why care

A command-line sub-cgroup selector should carry one containment contract independent of which kernel feature runc can use. A fallback path that broadens the reachable cgroup tree would turn kernel capability or syscall failure into a change in authority and process placement.

## Current state

- State: `SCOPING`
- Exact working head: upstream runc `0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`; owned fork matches
- Dependency: `github.com/opencontainers/cgroups v0.0.8`
- Latest authoritative gate or artifact: source/history comparison only
- First incomplete step: privileged runtime differential forcing the cgroupfd fallback
- Cleanup state: no cgroups created by this scout
- Next safe action: run one cgroup-v2 fixture under normal cgroupfd and one under deliberately unavailable `CLONE_INTO_CGROUP`
- External-contact state: none authorized or made

## Intent and precedent

[runc PR 3381](https://redirect.github.com/opencontainers/runc/pull/3381) introduced explicit enforcement that `runc exec --cgroup` names a sub-cgroup. Its review considered lexical cleaning, then settled on `strings.HasPrefix` after joining the base and requested subpath.

The component-boundary flaw in that check is now demonstrated for cgroup v1 by [runc issue 5351](https://redirect.github.com/opencontainers/runc/issues/5351): a base ending in `foo` accepts sibling `foo2` because the sibling path shares the same string prefix.

Later, [runc PR 4822](https://redirect.github.com/opencontainers/runc/pull/4822) moved normal exec placement through the cgroup manager's `AddPid`, and [runc PR 4812](https://redirect.github.com/opencontainers/runc/pull/4812) added `CLONE_INTO_CGROUP` with an explicit retry path when cgroup-fd process creation fails.

Current cgroups v0.0.8 `fs2.Manager.AddPid` contains the same join-plus-prefix pattern:

```go
path := filepath.Join(m.dirPath, subcgroup)
if !strings.HasPrefix(path, m.dirPath) {
    return fmt.Errorf("bad sub cgroup path: %s", subcgroup)
}
return cgroups.WriteCgroupProc(path, pid)
```

The cgroup-fd path instead calls `cgroups.OpenFile(base, sub, ...)`. cgroups v0.0.8 deliberately computes its target with:

```go
path := filepath.Join(dir, filepath.Clean("/"+file))
```

The leading slash used for cleaning prevents relative `..` components from escaping the supplied `dir` during this lexical join. The openat2 path also uses beneath/no-magic-link resolution flags when available.

## Question

Can the same `runc exec --cgroup <subpath>` request reach different cgroup-v2 directories depending on whether the initial `CLONE_INTO_CGROUP` start succeeds or runc retries through `Manager.AddPid`?

## Source

- Project: opencontainers/runc
- Requested revision: current upstream `main` during this scout
- Resolved commit: `0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`
- Candidate source commit: none
- Dependency: opencontainers/cgroups v0.0.8
- Relevant runc paths: `libcontainer/process_linux.go`, `tests/integration/exec.bats`
- Relevant cgroups paths: `fs2/fs2.go`, `file.go`
- Historical / related carriers:
  - [runc PR 3381](https://redirect.github.com/opencontainers/runc/pull/3381)
  - [runc issue 5351](https://redirect.github.com/opencontainers/runc/issues/5351)
  - [runc PR 4822](https://redirect.github.com/opencontainers/runc/pull/4822)
  - [runc PR 4812](https://redirect.github.com/opencontainers/runc/pull/4812)

## Environment

Required decisive probe:

- Linux with writable cgroup v2 hierarchy suitable for runc integration testing
- root or equivalent delegated cgroup authority
- one execution mode where `CLONE_INTO_CGROUP` succeeds
- one controlled mode where the cgroup-fd start fails and runc takes its documented retry path

The current execution sandbox does not provide this privileged cgroup test surface.

## Baseline behavior

Existing runc integration coverage verifies that plain `..` is rejected for cgroup v2 and that ordinary child sub-cgroups work. It does not exercise a prefix-colliding name such as base `foo` plus request `../foo2`.

The source-level paths differ:

### Early cgroup-fd path

```text
base=/sys/fs/cgroup/.../foo
sub=../foo2
OpenFile(base, sub)
filepath.Clean("/" + sub) -> /foo2
join -> /sys/fs/cgroup/.../foo/foo2
```

### Post-start AddPid fallback

```text
base=/sys/fs/cgroup/.../foo
sub=../foo2
filepath.Join(base, sub) -> /sys/fs/cgroup/.../foo2
strings.HasPrefix(path, base) -> true when sibling is named foo2
```

This establishes a semantic mismatch in target calculation. Runtime reachability of the fallback under the exact fixture remains to be demonstrated.

## Hypothesis or candidate

### Hypothesis

If runc is forced to retry without `UseCgroupFD`, `--cgroup ../foo2` can reach a prefix-colliding sibling through `fs2.Manager.AddPid`, while normal cgroup-fd execution resolves the same request beneath the container base.

### Candidate repair boundary

Choose one containment rule before placement so both roads consume the same validated subpath. Possible boundaries include:

- component-aware lexical containment in runc before either path;
- correcting `Manager.AddPid` in opencontainers/cgroups and updating runc's dependency;
- both, if runc needs an immediate invariant while the shared library carries the canonical fix.

Do not select the repair until the runtime differential proves which path executes and what target it reaches.

## Reproduction

Proposed fixture:

```text
container cgroup: /.../foo
create child:     /.../foo/foo2
create sibling:   /.../foo2
request:          runc exec --cgroup ../foo2 ...
```

Run twice:

1. normal modern cgroupfd path;
2. same source and fixture with `CLONE_INTO_CGROUP` deliberately unavailable so runc logs its retry and reaches `Manager.AddPid`.

The child and sibling both exist so each interpretation can succeed, making the resulting `/proc/self/cgroup` path the discriminator rather than an ENOENT side effect.

Negative controls:

- ordinary child `--cgroup foo2` should remain beneath the base;
- a non-prefix sibling name should be rejected by the fallback path rather than falsely demonstrating every traversal as an escape.

## Results

Source and history establish:

- the intended API is sub-cgroup-only;
- cgroup v1 already has a demonstrated prefix-collision defect in the same family;
- cgroup v2 `Manager.AddPid` retains the same component-insensitive prefix test;
- the cgroup-fd open path cleans the relative name beneath its supplied directory;
- runc deliberately retries through the post-start path when cgroup-fd process creation fails.

A runtime differential has not yet executed, so this remains a strong hypothesis rather than a demonstrated runc-v2 defect.

## Interpretation

This is a promising capability-parity investigation because the discriminating fact is precise: the same user input should identify the same allowed subtree regardless of which placement mechanism the kernel permits.

It also reuses a proven defect family without assuming the sibling case transfers automatically. The runtime fallback must lose before a patch is promoted.

## Evidence boundary

No privileged cgroup-v2 execution was performed in this scout. The source calculation shows different lexical targets; it does not prove that a particular host/kernel will reach the fallback or that systemd-backed managers have identical behavior.

The existing upstream cgroup-v1 issue belongs to another reporter and should be treated as precedent, not as permission to duplicate or take over that carrier.

## Next step

Run the two-road cgroup-v2 fixture in a privileged VM or CI environment. Capture:

- exact runc head;
- kernel and cgroup mode;
- debug evidence that identifies cgroupfd success versus fallback retry;
- `/proc/self/cgroup` from the exec process;
- child and sibling directory identities before and after;
- cleanup and an immediate clean rerun.

Promote a fix only if the fallback reaches a different or out-of-subtree target.

## Authority

No upstream contact is authorized or made. All work remains local or in `teamleaderleo/*` repositories unless a human explicitly authorizes publication.
