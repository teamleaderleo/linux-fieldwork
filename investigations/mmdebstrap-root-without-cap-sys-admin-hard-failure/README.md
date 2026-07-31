# Hook-free capability tests must keep hard-failure semantics

Date: 2026-07-31

Tracking: issue #153, Packet B in issue #194. Historical focused carrier: PR #171. Real-sid experiment carrier: PR #72.

## TL;DR

`root-without-cap-sys-admin` deliberately removes mount authority, while the package test's global `file-mirror-automount` hook immediately attempts a bind mount. The setup fails before the capability behavior under test.

This current-main candidate gives that class a distinct hook-free phase while preserving ordinary child failures. Focused tests cover parser acceptance, hook exclusion, selector failures, time exhaustion, status mapping, unchanged capability assertions, patch application, syntax, cleanup, and rerun.

## Explain like I'm five

The exam asks a person to work without a key. The examiner then requires the same key to enter the room.

The repair gives this exam a room that does not require the key. A wrong answer still counts as wrong.

## Why care

The case checks a privilege-sensitive fallback and confirms that `/proc/self/fd` stays absent in the target. The old setup can falsely blame mmdebstrap for a hook failure. Moving the case into the existing soft phase creates the opposite problem: a real regression becomes neutral status 77.

This test needs compatible setup and authoritative failure semantics.

## Concrete failure

```text
test drops CAP_SYS_ADMIN
→ global file-mirror hook calls mount --bind
→ mount fails with permission denied
→ intended mmdebstrap and /proc/self/fd assertions never run
```

## Source and history

The imported source under `upstream/mmdebstrap` remains unchanged. The retained patch applies to temporary copies of:

- `coverage.txt`;
- `coverage.py`;
- `debian/tests/testsuite`.

Merged PR #158 used the existing `Needs-APT-Config` phase to remove the hook conflict. That phase deliberately maps any selected test failure to 77 because transition tests can be incompatible with the package test's APT pinning. Issue #153 reopened because the capability invariant needs harder semantics.

PR #171 developed and reviewed the focused four-file candidate. This branch extracts that exact focused unit onto current `main`, separating it from PR #171's old base and PR #72's broad sid-reduction tooling.

## Candidate

Add a distinct metadata field:

```text
Needs-Hook-Free-APT-Config: true
```

Then:

1. accept the field in `coverage.py`;
2. skip that class while host APT hooks are active;
3. select it in a dedicated later phase with `CMD=mmdebstrap`;
4. keep `sourcesfilter` and `file-mirror-automount` out of that phase;
5. propagate child statuses 1 and 2 unchanged;
6. map GNU `timeout` status 124 to neutral 77;
7. fail with status 1 when zero tests are selected;
8. preserve selector-command errors greater than 1;
9. keep the original capability drop, `/proc/self/fd`, tar, and archive assertions.

## Why this approach

A hook fallback from bind-mounting to copying would change hook behavior and require a broader mount/copy compatibility matrix. A test-name special case would hide the reusable scheduling rule.

A distinct metadata class states the actual contract: this test needs host APT configuration without host hooks, and its functional failure remains authoritative.

## Historical and technical precedent

Autopkgtest reserves status 77 for tests that are inapplicable at runtime. GNU `timeout` uses 124 for time-limit expiry. `grep-dctrl` returns 1 when no paragraph matches and a higher status for command errors.

These conventions yield the decision table:

```text
selected child 0   → package phase 0
selected child 1   → package phase 1
selected child 2   → package phase 2
timeout 124        → package phase 77
no selected tests  → package phase 1
selector error 2   → package phase 2
no time remaining  → package phase 77
```

References:

- Debian autopkgtest specification: https://sources.debian.org/src/debian-policy/4.7.2.0/autopkgtest.md
- GNU `timeout`: https://www.gnu.org/software/coreutils/timeout
- `grep-dctrl`: https://manpages.debian.org/trixie/dctrl-tools/grep-dctrl.1.en.html

## Second-pass repair

The package script uses `set -e`. A direct command substitution exits early when real `grep-dctrl` returns 1 for no matches, bypassing the promised empty-selection diagnostic.

The candidate captures selector status explicitly:

- 0: use selected names;
- 1: reach the controlled empty-selection status 1;
- greater than 1: preserve the selector failure;
- every selection failure occurs before `timeout` runs.

The guard test creates its per-run parent before fake commands execute. This repairs the earlier test-harness failure where the guard stopped before exercising the candidate.

## Focused evidence

The two regression files prove:

- parser acceptance of the metadata;
- host-hook exclusion;
- a dedicated hard phase before the soft transition phase;
- no injected hook in the hard phase;
- status mapping `0→0`, `1→1`, `2→2`, `124→77`;
- real-style no-match status 1 and selector-error status 2;
- exhausted-time status 77 before child execution;
- unchanged `capsh --drop=cap_sys_admin`, `/proc/self/fd`, tar creation, and archive comparison;
- patch application, Python compilation, and shell syntax;
- temporary cleanup and repeat execution.

Historical PR #171 exact head `6469430c8fab67f9628d3346d2666e9ab7101ba5` passed Linux Fieldwork CI run `30582150648`.

## Composition boundary

PR #72 owns the disposable sid run. Its recent red runs belong to temporary command-proxy carriers and occurred before the dedicated capability phase. They neither validate nor refute this scheduling candidate.

The focused unit can be reviewed independently. A sid artifact that reaches the phase remains valuable integration evidence before any upstream proposal.

## Evidence boundary

This changes package-test scheduling and classification only. It does not change mmdebstrap product behavior, hook implementation, the package-test time budget, or historical Debian bug ownership.

## Current disposition

`HOLD` until this current-main extraction passes exact-head CI. After a green exact head, the focused unit should move to `READY FOR FINAL HUMAN CHECK`; PR #171 can become a historical carrier, while PR #72 stays the broad integration experiment.

## Human decision

Confirm that tests which deliberately remove mount authority should run without mount-dependent host hooks and retain hard functional failures.

## Authority

Internal Linux Fieldwork work only. No external issue, email, patch, merge request, comment, or review is authorized or included.
