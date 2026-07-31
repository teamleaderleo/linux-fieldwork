# Process-group SIGINT delivery across current kill syntax

State: `composed carrier repaired — patched exact-head repository and sid gates pending`

Tracking: issue #320, PR #326, motivating PR #72.

## TL;DR

The real Debian sid mmdebstrap carrier reached `sigint-during-customize-hook` and failed before testing mmdebstrap signal behavior. Its `/bin/kill --signal INT -- -<pgid>` command printed usage, delivered no signal, and allowed the customize hook to finish.

This investigation compares external and dash-builtin spellings against a disposable parent/descendant process group, with an owner-only negative control, Python `os.killpg` positive control, unrelated-process containment, cleanup verification, and immediate rerun.

The first probe head failed inside its own lifecycle after SIGINT delivery. The repaired probe waits past marker publication until signaled processes exit, explicitly reaps the directly owned group leader, treats zombies as exited, waits through create-before-write marker publication, and sends unused fixture streams to `DEVNULL`.

A later review found that the dedicated sid workflow executed that repaired topology probe **without applying** the retained zero-command-status selection patch. The current carrier now applies the exact patch to a disposable copy with zero fuzz and zero offset, compiles and hashes the transformed source, runs it twice, and requires status 0 for both controls and the selected whole-group spelling.

No compatibility spelling is promoted into the real package carrier until this patched exact sid matrix passes and identifies one stable zero-status whole-group command.

## Explain like I'm five

The test wanted to ring the alarm for everyone in one room. It wrote the room number in a way the current alarm tool did not understand, so nobody heard it.

The first measuring device later rang the alarm correctly but looked at the parent while its alarm handler was still finishing. The repaired device waits for that exit before deciding whether anyone stayed behind.

The next measuring run checked which button reached the whole room, but forgot to install the rule that the button must also report success. The current run installs that exact rule before choosing a button.

## Why care

Command status alone cannot prove delivery, and delivery alone cannot prove safe shell integration:

- a parser may reject the target;
- only the parent may receive SIGINT while the descendant continues;
- an overbroad signal may reach an unrelated process;
- a delivering command may still return nonzero and abort the real `set -e` test;
- a marker may exist before its contents or exit path finish;
- an unreaped zombie may be mistaken for a live process;
- leaked capture pipes can corrupt rerun evidence;
- a green workflow can execute the predecessor source instead of the retained candidate.

The intended mmdebstrap test needs whole-group delivery, status 0 from the delivery command, and complete cleanup.

## Exact motivating boundary

Source run: Linux Fieldwork PR #72 at `4ba6bde06decd5f69c3ac88ca391ad74dcfd4f2c`.

Workflow run: `30589690319` / 692.

Artifact:

- ID `8780048699`;
- SHA-256 `6b02d6f7b4f1e0145b4ec738161685dc5d58dd42efc7879be0cc4c912f2ab116`;
- 26 retained files.

First failed test:

```text
(171/284) sigint-during-customize-hook
pgid=-207687
/bin/kill --signal INT -- -207687
Usage: kill [options] <pid> [...]
```

The customize hook then printed its completion marker. The sid artifact names procps `2:4.0.6-3`, bash `5.3-3`, and util-linux `2.42.2-2`.

## First probe failure classification

Initial PR #326 head `7bd6ae6f6d548d5aadf42eafbced4a1963d70e5d` failed:

- Linux Fieldwork CI `30630034785` / 910;
- dedicated sid probe `30630034998` / 1.

The repository log showed the Python positive control recording SIGINT 2 for both parent and child and classifying `whole-group-delivery`. The child had exited. The parent marker was written before the handler's final 0.05-second delay, so the probe sampled `parent_running=True` before the owner exited. Four unused `PIPE` handles per case also emitted `ResourceWarning` records.

The result rejects the original carrier lifecycle. It does not reject Python group delivery or any tested `kill` spelling because candidate selection never completed.

## Topology lifecycle repair contract

1. Signal marker creation does not equal completed marker contents; empty markers receive a bounded settle wait.
2. A signal marker proves delivery, then liveness waits until the recorded process exits.
3. The direct parent process receives an explicit `wait()` so a zombie cannot become a live-process observation.
4. `/proc/<pid>/stat` state `Z` remains an exited control.
5. Parent and unrelated fixture streams use `DEVNULL`; child streams inherit that closed capture policy.
6. Cleanup always targets the recorded process group even after the leader exits, verifies the child is gone, and terminates the unrelated process separately.
7. The dedicated sid workflow runs both complete matrices under `-W error::ResourceWarning`.
8. Owner-only and Python whole-group controls run twice in repository tests.

## Composed gate review failure

Head `1de7983839479cb05a29cfb2fba3ad54da57e843` passed:

- Linux Fieldwork CI `30634052878` / 946;
- dedicated sid probe `30634052871` / 5.

Repository CI applied `0001-require-zero-command-status.patch` inside the synthetic selection tests, so it validated the intended selection mechanism.

The dedicated workflow did not. It invoked `tools/probe_process_group_kill.py` directly from the read-only checkout, never applied the retained patch, omitted `tests/test_process_group_kill_zero_status_selection.py` from its path trigger, and accepted a selected candidate without checking its return code. Both sid runs happened to select `dash-builtin-short` with status 0, but that coincidence is topology provenance only. It does not prove that the patched fail-closed selector executed.

The current workflow repair:

1. installs `patch` in the disposable sid container;
2. copies the imported probe to an unprivileged disposable candidate tree;
3. applies the retained patch with `--fuzz=0` and rejects any fuzz or offset receipt;
4. compiles the complete transformed probe;
5. records source, patch, and candidate SHA-256 identities;
6. runs the transformed candidate twice under warning-as-error;
7. requires exact integer return codes;
8. requires status 0 for owner-only and Python controls and for the selected candidate;
9. triggers when either focused test, the workflow, probe, or retained investigation files change.

The predecessor sid result remains useful evidence for command topology. Fresh exact-head execution owns the zero-status selection claim.

## Exact candidate matrix

The probe exercises:

1. external owner PID only;
2. `/bin/kill --signal INT -- -PGID`;
3. `/bin/kill -s INT -- -PGID`;
4. `/bin/kill -INT -- -PGID`;
5. dash builtin `kill -s INT -- -PGID`;
6. Python `os.killpg(PGID, SIGINT)`.

Each record includes exact command, status, stdout, stderr, parent/child/unrelated markers, post-settle liveness, and one typed classification.

Candidate preference remains:

1. dash builtin short spelling;
2. external `-s INT` spelling;
3. external `-INT` spelling;
4. external `--signal INT` spelling.

The order is a review preference, not an expected result. The patched exact sid artifact owns selection.

## Focused verification

```sh
python3 -m unittest -v \
  tests.test_process_group_kill_probe \
  tests.test_process_group_kill_zero_status_selection
python3 -m py_compile \
  tools/probe_process_group_kill.py \
  tests/test_process_group_kill_probe.py \
  tests/test_process_group_kill_zero_status_selection.py
```

The dedicated workflow applies the patch to a disposable copy, runs the complete matrix twice in `debian:sid-slim`, validates exact schema, topology, and status, requires stable candidate selection across immediate reruns, and uploads package versions, patch receipt, source identities, both records, and streams.

## Evidence boundary

This unit characterizes current Linux command behavior and process topology. It does not establish an upstream mmdebstrap defect, a procps or dash defect, broad portability, product-source repair, or a Debian submission.

Any compatibility override first belongs only in PR #72's disposable source copy and requires the real package matrix to pass afterward.

## Stop rule

Stop and redesign the signal-delivery fixture when the repaired positive control, exact patch application, status authority, or cleanup fails. Select a spelling only after both patched exact sid runs agree on zero-status whole-group delivery with unrelated-process containment and clean rerun.

## Authority

Internal Linux Fieldwork work only. External contact authorized: false.
