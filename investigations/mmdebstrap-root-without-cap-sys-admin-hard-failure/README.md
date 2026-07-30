# Hook-free capability tests must keep hard-failure semantics

## Explain it like I am five

This test asks: “Can mmdebstrap behave correctly after we take away its permission to mount things?”

The test runner then attaches a helper that immediately tries to mount something.

That is like testing whether a person can finish a task without a key while the examiner requires that same key to open the examination room. The person never reaches the task. The setup fails first.

The corrected candidate runs this one capability test in a room without the mount-dependent helper and still treats a real test failure as a failure.

## What actually goes wrong?

The `root-without-cap-sys-admin` case deliberately runs:

```sh
capsh --drop=cap_sys_admin
```

Its purpose is to check mmdebstrap's fallback behavior and confirm that `/proc/self/fd` stays absent in the target.

The Debian package test's main host-APT phase injects `file-mirror-automount`. In root mode that hook performs a bind mount. The case has deliberately removed the capability required for that bind mount, so execution stops in the hook before reaching the mmdebstrap behavior under test.

Literal sequence:

```text
test removes CAP_SYS_ADMIN
→ global helper calls mount --bind
→ mount returns permission denied
→ intended /proc/self/fd assertion never runs
```

## Why should anyone care?

A failing test usually tells us the product failed. This failure tells us the test setup contradicted the condition being tested.

Leaving the contradiction in place creates two bad choices:

- treat the hook failure as a product regression, which blames mmdebstrap for a setup error;
- move the case into a phase where every failure becomes a neutral skip, which can hide a real regression in the capability fallback.

The test checks a privilege-sensitive safety path. Its ordinary failures need to remain authoritative.

## Was the old behavior intentional?

The global hooks serve a real purpose: many package tests need local APT sources and test binaries visible inside the generated root. Applying them to the main phase is a useful default.

The capability case has the opposite requirement. It deliberately removes the privilege one of those hooks consumes. The conflict looks like a scheduling oversight created by combining two individually sensible test features.

Merged PR #158 removed the incompatible hook by using the existing `Needs-APT-Config` phase. That phase intentionally treats failures as transition-test skips. The move solved the mount contradiction while weakening this case's result. Issue #153 was reopened for that reason.

## Proposed fix in plain terms

Give tests a distinct metadata label:

```text
Needs-Hook-Free-APT-Config: true
```

Then:

1. skip those cases while the host APT hooks are active;
2. run them later with `CMD=mmdebstrap` and without `sourcesfilter` or `file-mirror-automount`;
3. preserve ordinary child statuses such as 1 and 2;
4. map GNU `timeout` status 124 to neutral 77 because the package-test time budget expired before a result;
5. fail with status 1 when the metadata selects zero tests;
6. leave the original capability drop and assertions unchanged.

## Why this boundary?

A broader change could make `file-mirror-automount` fall back to copying whenever bind mounting fails. That changes hook behavior and requires mount/copy parity work.

A narrower change could skip this one named test through an ad hoc condition. That hides the scheduling rule and makes the next capability-sensitive case repeat the same problem.

A separate metadata class states the real contract: **this test needs APT configuration without host hooks, and its functional failure still counts.**

## Historical and technical precedent

Autopkgtest uses status 77 for a runtime skip and warns test authors to reserve it for conditions that genuinely make the test inapplicable; other statuses retain their normal success/failure meaning. GNU `timeout` returns 124 when the command exceeds its time limit. Those conventions support the candidate's split between authoritative child failure and neutral budget exhaustion:

- Debian autopkgtest test specification: https://sources.debian.org/src/debian-policy/4.7.2.0/autopkgtest.md
- GNU `timeout` exit status: https://www.gnu.org/software/coreutils/timeout

The broader testing lesson is fixture compatibility: setup should provide the conditions required by the case, instead of consuming the capability the case intentionally removes.

## Candidate source changes

The retained patch changes three temporary source-copy files:

- `coverage.txt` — labels `root-without-cap-sys-admin` with the new metadata;
- `coverage.py` — accepts the field and skips that class during host-hook execution;
- `debian/tests/testsuite` — adds the separate hook-free hard-failure phase.

The imported source remains unchanged.

## Executable evidence

The focused regressions prove:

- parser acceptance of the metadata;
- host-hook exclusion;
- absence of `sourcesfilter` and `file-mirror-automount` in the hard phase;
- result mapping `0→0`, `1→1`, `2→2`, and `124→77`;
- empty selection fails before child execution;
- exhausted time returns 77 before child execution;
- the original `capsh`, `/proc/self/fd`, tar creation, and archive comparisons remain present;
- patch application, Python compilation, and shell syntax;
- temporary-directory cleanup and repeat execution.

PR #72 owns the disposable Debian sid composition run that applies this patch together with the Deb822 source-filter candidate. The focused branch proves the scheduling and classification logic; the contained sid run proves that the real package test reaches the intended case.

## Evidence boundary

This candidate changes package-test scheduling and result classification. It does not change mmdebstrap product behavior, hook behavior, historical Debian bug ownership, or the package-test time budget.

A green focused matrix cannot replace the contained Debian sid run. Until that run reaches and classifies `root-without-cap-sys-admin`, the disposition remains `HOLD`.

## Human decision

Confirm that this capability test should run without host APT hooks while ordinary statuses remain hard failures. After the contained sid run completes, decide whether the four-file scheduling record is ready to merge locally.

No external contact is included or authorized. Refs #153, merged #158, PR #171, and PR #72.