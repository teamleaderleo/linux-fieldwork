# Campaign 0001: Rootless bootstrap lab

## In simple words

Build Debian root filesystems repeatedly, compare every meaningful byte and metadata field, and follow each difference to the component that owns it. Begin with `mmdebstrap`; escalate into APT, dpkg, autopkgtest, QEMU, container runtimes, or the kernel only when evidence crosses that boundary.

## Question

Can a controlled package snapshot produce equivalent Debian roots across repeated builds, privileged and rootless execution, and native and foreign architectures?

## Why this campaign

The same mechanisms appear in server images, Docker and OCI images, package testbeds, CI workers, build chroots, recovery systems, and VM roots. A bootstrap failure often exposes a deeper issue in namespace behavior, package scripts, mount handling, architecture emulation, or image metadata.

## Starting source

- Imported package tree: `upstream/mmdebstrap/`
- Imported Debian revision: `debian/1.5.7-3`
- Resolved commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Debian bug under initial investigation: `#1141078`, “mmdebstrap autopkgtest fails”

Upstream contact authorization: **false**.

## Initial hypotheses

1. Repeated builds become equivalent once package indexes, package versions, environment, locale, clock input, and archive ordering are controlled.
2. Rootless and privileged modes should produce equivalent archive ownership and content for supported variants; device handling and mount-dependent hooks are likely divergence points.
3. Foreign-architecture differences may come from package availability, maintainer-script execution under QEMU, binfmt configuration, or architecture-specific package contents.
4. The important autopkgtest failure may belong to a package transition or test environment instead of the `mmdebstrap` implementation.

## Matrix

| Axis | First values |
| --- | --- |
| Suite | stable, testing, unstable |
| Architecture | amd64, arm64 |
| Mode | unshare, root reference |
| Output | tar, ext filesystem, bootable QEMU image |
| Repetition | two builds per cell |
| Comparison | archive hash, metadata manifest, package manifest, diffoscope, boot transcript |

The first runnable slice stays smaller: native architecture, tar output, two repeated builds, and explicit package snapshot input.

## Tools added by this campaign

- `tools/tar_manifest.py` records tar member type, mode, ownership, size, timestamp, links, device numbers, PAX metadata, and SHA-256 content hashes.
- `tools/manifest_diff.py` compares two manifests and can ignore named noise fields such as `mtime`.
- `scripts/capture-linux-context.sh` records kernel, identity, namespaces, subordinate IDs, cgroups, mounts, capabilities, seccomp state, resource limits, and available container/bootstrap tools.

## Work sequence

### Phase A: Laboratory controls

1. Capture the execution context.
2. Pin source revision and package source inputs.
3. Produce two tar roots with identical declared inputs.
4. Generate manifests and compare them with every field enabled.
5. Classify each difference as package content, package script output, archive metadata, host leakage, runtime behavior, or unexplained.

### Phase B: Rootless boundary

1. Repeat under `unshare` and a privileged reference mode.
2. Record UID/GID maps and subordinate ID allocation.
3. Trace the first operation that differs.
4. Reduce any divergence to one package, hook, mount, archive member, or syscall sequence.

### Phase C: Architecture boundary

1. Add arm64 roots on an amd64 host.
2. Separate dependency-resolution differences from emulated maintainer-script behavior.
3. Record QEMU and binfmt versions and handlers.
4. Boot retained images when archive comparison alone cannot establish operational equivalence.

### Phase D: Owner promotion

Promote only proven findings:

- `mmdebstrap` code or test behavior -> candidate patch under this repository
- package dependency or maintainer script -> Debian package investigation
- APT solver or dpkg database behavior -> APT/dpkg campaign
- autopkgtest lifecycle -> autopkgtest campaign
- QEMU or binfmt execution -> QEMU/binfmt campaign
- namespace, mount, idmap, filesystem, or syscall behavior -> kernel reproducer and selftest candidate

## Evidence layout

```text
campaigns/0001-rootless-bootstrap/
  README.md
  debian-bug-1141078.md
  runs/<run-id>/context.md
  runs/<run-id>/commands.log
  runs/<run-id>/left.manifest.jsonl
  runs/<run-id>/right.manifest.jsonl
  runs/<run-id>/diff.json
  findings/<finding>.md
```

Large root filesystem archives stay out of Git. Store hashes, manifests, package lists, compact logs, and reproduction commands here.

## Stop conditions

A lane stops when one of these becomes true:

- repeated controlled builds compare equal;
- the first divergence has a minimal reproducer and a clear owner;
- the environment cannot exercise the required namespace, mount, architecture, or virtualization feature and the missing capability is recorded;
- further work requires upstream contact or external resources beyond current authorization.

## Current status

- Campaign defined.
- Archive comparison tools implemented and unit-tested locally.
- Linux execution-context probe implemented and syntax-checked locally.
- Debian bug `#1141078` recorded for contained reproduction work.
- No upstream issue, merge request, email, comment, or patch submission has been made.
