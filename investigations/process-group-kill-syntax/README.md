# Process-group SIGINT delivery across current kill syntax

## TL;DR

The real Debian sid mmdebstrap carrier reached `sigint-during-customize-hook` and failed before testing mmdebstrap signal behavior. Its `/bin/kill --signal INT -- -<pgid>` command printed usage, delivered no signal, and allowed the customize hook to finish.

This investigation compares external and shell-builtin spellings against a disposable parent/descendant process group, with an owner-only negative control, a Python `os.killpg` positive control, unrelated-process containment, cleanup verification, and immediate rerun.

No compatibility patch is proposed until the exact sid matrix identifies a stable whole-group spelling.

## Explain like I'm five

The test wanted to ring the alarm for everyone in one room. It wrote the room number in a way the current alarm tool did not understand, so nobody heard the alarm.

The probe creates a pretend room with a parent and child, plus an unrelated person elsewhere. It tries several ways to ring the alarm and records exactly who receives it.

## Why care

Checking only a command's exit status would be weak evidence:

- a parser may reject the target;
- only the parent may receive SIGINT while the descendant continues;
- an overbroad signal may reach an unrelated process;
- the fixture may leak a descendant and make the next run unreliable.

The intended mmdebstrap test requires whole-group delivery, not merely a successful `kill` command.

## Exact observed boundary

Owning issue: #320.

Source run: Linux Fieldwork PR #72 at `4ba6bde06decd5f69c3ac88ca391ad74dcfd4f2c`.

Workflow run: `30589690319` / 692.

Artifact:

- ID: `8780048699`;
- SHA-256: `6b02d6f7b4f1e0145b4ec738161685dc5d58dd42efc7879be0cc4c912f2ab116`;
- retained files: 26.

First failed test:

```text
(171/284) sigint-during-customize-hook
pgid=-207687
/bin/kill --signal INT -- -207687
Usage: kill [options] <pid> [...]
```

The customize hook then printed its completion marker. SIGINT was not delivered.

The sid artifact reports:

- `procps` 2:4.0.6-3;
- `bash` 5.3-3;
- `util-linux` 2.42.2-2.

## Preliminary local controls

The assistant container has procps 4.0.4, not the sid version from run 692.

Observed locally:

- external `/bin/kill --signal 0 -- -999999` parsed the group target and reported no such process;
- Bash accepted both `kill -0 -- -999999` and `kill -s 0 -- -999999`;
- dash rejected `kill -0 -- -999999` as an illegal number;
- dash accepted `kill -s 0 -- -999999` and reached the no-such-process result.

Those parser checks make `kill -s INT -- "$pgid"` through the shell builtin a plausible candidate, but version and topology differ. They are not sufficient for a repair.

## Exact candidate matrix

`tools/probe_process_group_kill.py` creates for each case:

- an isolated session and process group;
- a parent process with a SIGINT marker;
- a child in the same group with its own marker;
- an unrelated process in another session;
- disposable temporary state.

It exercises:

1. external owner PID only — required negative control;
2. `/bin/kill --signal INT -- -PGID` — exact failed spelling from run 692;
3. `/bin/kill -s INT -- -PGID`;
4. `/bin/kill -INT -- -PGID`;
5. dash builtin `kill -s INT -- -PGID`;
6. Python `os.killpg(PGID, SIGINT)` — required positive topology control.

Each result records:

- exact command;
- return status, stdout, and stderr;
- parent, child, and unrelated signal markers;
- whether each process remained running before cleanup;
- one explicit classification.

Classifications distinguish:

- parser or target rejection;
- no delivery;
- owner-only delivery;
- whole-group delivery;
- overbroad delivery;
- partial or unexpected delivery.

## Cleanup authority

The owner-only negative control intentionally terminates the group leader while leaving the descendant alive.

Cleanup therefore cannot depend on `parent.poll()` or a live group leader. The probe always sends SIGKILL to the recorded process group, waits for the parent, verifies the child no longer runs, and separately terminates the unrelated process. Cleanup failure is authoritative and causes the case to fail.

The complete probe selects a candidate only when:

- both parent and child recorded SIGINT;
- neither remained running;
- the unrelated process received no signal and remained running.

Candidate preference is:

1. dash builtin short spelling;
2. external short spelling;
3. external compact spelling;
4. external long spelling.

The preference favors the shell builtin form already supported by dash's parser without making it an expected result before sid execution.

## Focused repository regression

`tests/test_process_group_kill_probe.py` covers:

- explicit classifier boundaries;
- exact command inventory and argument placement;
- owner-only and Python group controls twice, proving cleanup and immediate rerun;
- complete probe schema, inventory, selected-candidate topology, and unrelated-process containment.

## Dedicated sid workflow

`.github/workflows/probe-process-group-kill.yml`:

- checks out the exact proposed repository state;
- runs a read-only repository mount inside `debian:sid-slim`;
- installs current sid `dash`, `procps`, and `python3`;
- records exact package and command versions;
- runs the complete topology matrix twice;
- explicitly validates JSON schema, case inventory, owner-only and Python controls, selected-candidate topology, and rerun stability;
- uploads both JSON records, stdout/stderr, package versions, and command versions.

The workflow does not force the observed failed spelling to remain broken. A future sid version that accepts it is a changed observation, not a reason to falsify the matrix. It does require at least one tested spelling to deliver whole-group SIGINT correctly.

## Why this approach

A text-only replacement would assume the parser result and would not prove signal reach. Changing the expected test status would hide the fact that the hook was never interrupted. Sending SIGINT only to the parent would leave descendants running and test the wrong lifecycle.

A disposable topology matrix identifies parser, ownership, containment, and cleanup independently before any integration patch is selected.

## Evidence boundary

This unit characterizes current Linux command behavior and process topology. It does not yet establish:

- an upstream mmdebstrap test defect;
- a procps or dash defect;
- the most portable spelling across every supported host;
- a product-source repair;
- a new Debian submission.

Any compatibility override first belongs only in PR #72's disposable integration carrier. Product or upstream ownership requires separate review.

## Disposition

`INVESTIGATE` until exact-head repository CI and the dedicated sid workflow pass and the artifact identifies the stable whole-group spelling on current sid.

If a candidate is stable across both immediate runs, the next unit may apply it only to the disposable PR #72 source copy and rerun the real package matrix. If no candidate succeeds, stop and redesign the signal-delivery fixture rather than weakening the test.

## Authority

Internal Linux Fieldwork work only. No external contact is included or authorized.
