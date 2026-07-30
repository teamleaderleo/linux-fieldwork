# Testing Debian maintainer-script interruption

## In simple words

Debian package maintainer scripts can change several kinds of system state during installation or upgrade. If a script is interrupted between those changes, rerunning package configuration may converge cleanly, duplicate state, or require manual repair.

A useful interruption probe places deterministic stop points between visible side effects, captures the package state before recovery, reruns the normal package action, and compares the final result with a clean installation.

## What I learned

A credible maintainer-script recovery test needs more than an interrupted exit code.

For each interruption point, record and assert:

- the first package command failed for the expected reason;
- dpkg recorded the expected intermediate state, such as `install ok half-configured`;
- the ordinary recovery command completed;
- the final package state became `install ok installed`;
- filesystem, generated configuration, links, users/groups, service state, alternatives, and caches match or deliberately diverge from the clean baseline;
- repeated non-idempotent operations have the expected count;
- and the harness exits nonzero when any expected outcome drifts.

A deliberately non-idempotent append is a useful fixture because it distinguishes interruption points before and after the append. Recovery before the append can converge; recovery after the append duplicates the registry entry.

The harness itself also needs safety boundaries. A caller-controlled work path must be resolved and restricted to a disposable temporary root before any `rm -rf` or chroot construction occurs.

## Source and provenance

- Programme lane: LF-07 maintainer-script interruption and idempotency
- Fixture: `lf-script-idempotency-fixture` version 1.0
- Runner: `artifacts/run-probe.sh`
- Pull request: #18

## Example

A minimal sequence can use four side effects:

1. overwrite a deterministic state marker;
2. append one registry line;
3. overwrite generated configuration;
4. replace an alternative-like symlink.

Interruption after step 1 should rerun the append once and converge. Interruption after steps 2 or 3 reruns the append and produces two registry lines.

The test should assert the exact matrix rather than only print it.

## Validation

The LF-07 runner builds a dependency-free package, installs it into disposable dpkg roots, triggers `SIGTERM` at three named points, captures half-configured state, runs `dpkg --configure`, and compares snapshots with a clean installation.

A negative control that replaces the append with an overwrite must make the expected-divergence assertions fail.

The dedicated repository workflow runs the asserted matrix in a disposable privileged Debian sid container. Separate unit checks verify that `/` and non-temporary caller paths are rejected before cleanup.

## Environment and assumptions

- Debian dpkg and dpkg-deb behavior.
- Privileged disposable container for chroot-style package script execution.
- BusyBox supplies the small command set inside the synthetic root.
- Purpose-built fixture rather than a claim about a real Debian package.

## Limits

This probe does not cover apt transaction recovery, upgrades, removals, external triggers, service-manager behavior, debhelper-generated snippets, abrupt `SIGKILL`, power loss, filesystem durability, or real package maintainer scripts.

## Related work

- Related issue: #13
- Related pull request: #18
- Related lane report: LF-SCOUT-DEB-01
