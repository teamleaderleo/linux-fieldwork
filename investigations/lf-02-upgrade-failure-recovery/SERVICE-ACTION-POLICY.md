# LF-02 host-hook decision policy

Tracking: issue #174 and PR #178.

## Explain it simply

The chrootless upgrade test asks host `dpkg` to operate on a target directory. The host has a configured `needrestart` status logger. Dpkg launches that logger during every package phase.

The logger then tries to touch files below `/run/needrestart`. In the retained run, every one of those writes fails. The target package still follows the expected lifecycle, and the host fingerprint remains unchanged.

The old classifier called all 32 events `service_action` and promoted the whole result. That category is useful for discovery, but it combines two different facts:

1. a host hook was invoked;
2. the hook caused a successful host-side effect.

Only the second fact establishes host mutation in this experiment.

## Why we care

Two bad policies are easy to write:

- promote every host hook, which turns ordinary configured observation hooks into product defects even when they leave no state;
- accept every host hook, which can hide a successful restart, daemon reload, cache update, or host file mutation.

The decision must preserve the warning while distinguishing an attempted effect from a completed effect.

## Chosen rule

Policy version 2 recognizes one exact mapped pattern:

- successful execution of `/usr/lib/needrestart/dpkg-status`;
- failed mutations only below:
  - `/run/needrestart`;
  - `/run/needrestart/unpacked`;
  - `/run/needrestart/errored`.

Those rows count as `mapped_needrestart_actions` and set:

```text
environment_sensitive_host_hooks=true
```

They do not promote the lifecycle result by themselves.

Promotion still occurs for:

- any successful mutation below those paths;
- any different service executable;
- any different service path;
- any unexpected mutation;
- a changed host fingerprint;
- lifecycle or conffile failure.

Unresolved rows still block a clean mapped result.

## Exact evidence

Dedicated workflow run `30579373886`, artifact `lf-02-upgrade-failure-recovery-30579373886-1`, digest:

```text
sha256:5e24e28201021b68729bf3f5174e086d8abb9cb92e40c4af867238f726980a12
```

The 32 service rows were:

```text
8  execve    /usr/lib/needrestart/dpkg-status   0
8  mkdir     /run/needrestart                    -1 EACCES
7  openat    /run/needrestart/unpacked           -1 ENOENT
7  utimensat /run/needrestart/unpacked           -1 ENOENT
1  openat    /run/needrestart/errored            -1 ENOENT
1  utimensat /run/needrestart/errored            -1 ENOENT
```

The same artifact records:

- `unexpected_mutations=0`;
- `unresolved=0`;
- unchanged host fingerprint;
- expected version-3 configure failure;
- target status `half-configured` after that failure;
- successful version-3.1 recovery to `installed`;
- preserved locally edited conffile;
- successful purge of the package and principal conffile.

## Why this follows the owning issue

Issue #174 defined product promotion around successful unexpected host mutation, misleading success, lifecycle corruption, unrecoverable state, or conffile-policy failure. It explicitly allowed classified host reads, runtime interactions, and service actions to remain mapped behavior.

Policy version 2 makes that rule executable while adding a stricter identity check for the one observed hook. The evidence row must match the known executable, known path set, and failed mutation result. A category count alone is insufficient.

## Historical precedent

Dpkg supports configured status loggers and runs them as part of package status reporting. That means logger execution can be an expected host configuration effect even when the package target lives below another root:

- https://manpages.debian.org/testing/dpkg/dpkg.1.en.html

Needrestart installs a dpkg configuration fragment and the `dpkg-status` helper under `/usr/lib/needrestart`, which explains the exact executable observed here:

- https://salsa.debian.org/debian/needrestart/-/blob/master/Makefile

System-call tracing reports both the attempted operation and its result. A failed syscall is evidence of an attempted effect; a successful return establishes that the operation completed at the syscall boundary:

- https://man7.org/linux/man-pages/man1/strace.1.html

The practical precedent is the same as transaction logging: identity, destination, and outcome all participate in the decision.

## Alternatives considered

### Every service action promotes

Easy to explain, but too coarse for an investigation whose owning rule already distinguishes successful mutation from classified host behavior. It would classify a read-only or failed configured hook as equivalent to a successful host restart.

### Every classified service action is mapped

Too permissive. A new `systemctl`, `update-initramfs`, `ldconfig`, or successful host-file write could arrive under the same broad category and escape promotion.

### Ignore all failed syscalls

Also too permissive. Repeated failed attempts can expose a compatibility defect, and an unknown service action still deserves review. Policy version 2 retains the environment-sensitive warning and maps only the exact known pattern.

### Disable host dpkg configuration for the probe

Useful as a later control, but it answers a narrower question. The current direct-dpkg boundary intentionally includes the host configuration that real chrootless execution sees. A clean-config comparison should be a separate matrix, not a replacement for the observed-host run.

## Related experiments

The next high-value comparisons are:

1. rerun with an explicitly empty temporary dpkg configuration and compare target lifecycle plus syscall categories;
2. rerun with the needrestart logger present but `/run/needrestart` writable inside a disposable host namespace, proving that a successful write promotes;
3. exercise a synthetic status logger that exits nonzero and determine whether dpkg lifecycle status changes;
4. run the apt-managed upgrade path separately, because apt adds another configuration and process boundary;
5. inventory other host dpkg hooks under `/etc/dpkg/dpkg.cfg.d` and classify them by executable identity, destination, and successful effect.

## Current disposition

The exact observed needrestart pattern is `retain-mapped-behavior` with an environment-sensitive warning. PR #178 still needs a current-base promotion slice and fresh exact-head gates before merge.

## Authority

Internal Linux Fieldwork work only. No external contact is included or authorized.
