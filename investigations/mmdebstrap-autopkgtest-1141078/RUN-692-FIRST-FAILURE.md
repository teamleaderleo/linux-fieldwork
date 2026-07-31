# Run 692 first-failure receipt and Packet B ordering decision

## TL;DR

The broad Debian sid carrier finally passed its temporary proxy setup and reached real mmdebstrap package tests. It ran 99 tests and then failed at `sigint-during-customize-hook` because the test invoked util-linux `kill` with a negative process-group argument in an option spelling that the current command rejected.

Packet B's `root-without-cap-sys-admin` case was correctly skipped while host APT hooks were active, but its dedicated hook-free hard-failure phase was scheduled after the broad matrix and therefore never executed.

The next carrier generation keeps the landing candidate unchanged and applies an integration-only ordering transformation: run the exact hook-free hard phase first, then the broad matrix, then the existing soft transition phase.

## Explain like I'm five

The special test was waiting behind a long line. A different test near the front broke first, so the special test never got its turn.

For the integration experiment only, we move the special test to the front. After it runs, the ordinary line continues and the other broken test is still allowed to fail.

## Why care

A focused candidate can be correct while its broad integration carrier never executes it. Calling the whole run merely “red” would lose two useful facts:

1. the proxy and source-compatibility repairs now reach real package execution;
2. Packet B remains untested in real sid because of phase order, not because its own case failed.

The ordering experiment separates those facts without changing the proposed landing behavior.

## Exact run boundary

Pull request: #72. Exact head: `4ba6bde06decd5f69c3ac88ca391ad74dcfd4f2c`.

Workflow run: `30589690319` / 692.

Jobs:

- Linux Fieldwork repository job: success;
- `reproduce-mmdebstrap`: failure;
- final container status: 6;
- autopkgtest testsuite status: 1.

Artifact:

- name: `mmdebstrap-reproduction-gha-30589690319-1`;
- artifact ID: `8780048699`;
- size: 502,789 bytes;
- SHA-256: `6b02d6f7b4f1e0145b4ec738161685dc5d58dd42efc7879be0cc4c912f2ab116`;
- retained files: 26, including complete autopkgtest log, suite stdout/stderr, package versions, patch receipts, source provenance, and result summary.

## What run 692 established

The carrier successfully:

- checked out and compiled the repository branch;
- passed repository unit tests;
- created the sid mirror and temporary installed-command wrapper;
- applied the Deb822 sourcesfilter compatibility patch;
- applied the Packet B scheduling patch;
- executed real package tests for about 33 minutes;
- completed 99 tests before the first hard failure;
- preserved a complete artifact with exact hashes and package versions.

Earlier relative-path, source-copy permission, and self-copy proxy failures did not recur.

## Packet B observation

The real log includes:

```text
(41/284) root-without-cap-sys-admin
skipped because of test cannot use host apt config
```

That is expected in the broad host-hook phase after applying `Needs-Hook-Free-APT-Config`.

The landing patch schedules the dedicated hook-free hard phase after the broad matrix. Because test 171 failed first, the later phase did not run. Run 692 therefore validates the skip boundary but neither supports nor refutes the real hook-free execution result.

## First hard failure

The first failed named case was:

```text
(171/284) sigint-during-customize-hook
```

The relevant log sequence was:

```text
pgid=-207687
/bin/kill --signal INT -- -207687
Usage: kill [options] <pid> [...]
```

The command returned usage instead of delivering SIGINT. The customize hook continued, completed successfully, and the test ended as failure after about 20 seconds.

This is a broad test/tool compatibility boundary. It is not a Packet B failure and is not repaired by the integration-order unit.

## Integration-only ordering candidate

`tools/reorder_mmdebstrap_hook_free_phase.py` operates only on the disposable temporary source copy after the exact Packet B patch applies.

It requires exactly one of each marker:

- broad matrix;
- hook-free hard phase;
- soft transition phase.

It requires the hook-free block to retain:

- `Needs-Hook-Free-APT-Config` selection;
- `CMD="mmdebstrap"` without host hooks;
- `exit "$ret"` hard-failure propagation.

It accepts only the landing order:

```text
broad < hook-free hard < soft transition
```

and writes the integration order:

```text
hook-free hard < broad < soft transition
```

The tool preserves every line, moves exactly one block, records original and reordered SHA-256 values, and fails if markers, order, selector, command, or hard-failure semantics drift.

## Focused controls

`tests/test_mmdebstrap_hook_free_integration_order.py` covers:

- exact movement with complete line preservation;
- missing, duplicate, and already-reordered marker rejection;
- selector, hook-free command, and hard-failure contract rejection;
- non-mutating `--check` mode;
- exact write-mode output and digest reporting.

## Why this approach

Changing the product candidate to run Packet B first would let integration-carrier limitations dictate landing behavior. Silently skipping the broad matrix after Packet B would hide the known SIGINT defect.

A disposable ordering transformation answers the focused integration question while preserving the broad matrix as an independent failure detector.

## Expected next interpretation

A new run can produce several decision-changing outcomes:

- Packet B passes, then SIGINT fails: real sid supports Packet B; open/continue the separate SIGINT compatibility unit.
- Packet B fails hard: classify that first failure as candidate, environment, or package behavior.
- Packet B times out or budget is exhausted: neutral result; adjust only the integration budget if justified.
- ordering transformation fails before execution: source or candidate drift; do not classify product behavior.
- broad matrix proceeds past SIGINT: record changed tool behavior and continue to the next first failure.

## Evidence boundary

The ordering override is not a landing proposal and changes no imported source in the repository. It exists only in the disposable integration carrier.

Run 692 did not execute Packet B's hook-free phase. The next exact hosted artifact remains required.

## Disposition

PR #72 remains `REPAIR` as a broad integration carrier. The next exact head should run repository CI and the real sid workflow with the ordering receipt retained.

PR #268 remains the focused current-main landing carrier and does not include this integration-only transformation.

## Authority

Internal Linux Fieldwork work only. No external contact is included or authorized.
