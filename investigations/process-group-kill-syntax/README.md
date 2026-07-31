# Process-group SIGINT delivery across current kill syntax

State: `carrier repaired — exact-head repository and sid gates pending`

Tracking: issue #320, PR #326, motivating PR #72.

## TL;DR

The real Debian sid mmdebstrap carrier reached `sigint-during-customize-hook` and failed before testing mmdebstrap signal behavior. Its `/bin/kill --signal INT -- -<pgid>` command printed usage, delivered no signal, and allowed the customize hook to finish.

This investigation compares external and dash-builtin spellings against a disposable parent/descendant process group, with an owner-only negative control, Python `os.killpg` positive control, unrelated-process containment, cleanup verification, and immediate rerun.

The first probe head failed inside its own lifecycle after SIGINT delivery. The repaired carrier waits past marker publication until signaled processes exit, explicitly reaps the directly owned group leader, treats zombies as exited, waits through create-before-write marker publication, and sends unused fixture streams to `DEVNULL`.

No compatibility patch is selected until the repaired exact sid matrix passes twice and identifies one stable whole-group spelling.

## Explain like I'm five

The test wanted to ring the alarm for everyone in one room. It wrote the room number in a way the current alarm tool did not understand, so nobody heard it.

The first measuring device later rang the alarm correctly but looked at the parent while its alarm handler was still finishing. The repaired device waits for that exit before deciding whether anyone stayed behind.

## Why care

Command status alone cannot prove delivery:

- a parser may reject the target;
- only the parent may receive SIGINT while the descendant continues;
- an overbroad signal may reach an unrelated process;
- a marker may exist before its contents or exit path finish;
- an unreaped zombie may be mistaken for a live process;
- leaked capture pipes can corrupt rerun evidence.

The intended mmdebstrap test needs whole-group delivery plus complete cleanup.

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

## Repair contract

1. Signal marker creation does not equal completed marker contents; empty markers receive a bounded settle wait.
2. A signal marker proves delivery, then liveness waits until the recorded process exits.
3. The direct parent process receives an explicit `wait()` so a zombie cannot become a live-process observation.
4. `/proc/<pid>/stat` state `Z` remains an exited control.
5. Parent and unrelated fixture streams use `DEVNULL`; child streams inherit that closed capture policy.
6. Cleanup always targets the recorded process group even after the leader exits, verifies the child is gone, and terminates the unrelated process separately.
7. The dedicated sid workflow runs both complete matrices under `-W error::ResourceWarning`.
8. Owner-only and Python whole-group controls run twice in repository tests.

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
2. external short spelling;
3. external compact spelling;
4. external long spelling.

The order is a review preference, not an expected result. The exact sid artifact owns selection.

## Focused verification

```sh
python3 -m unittest -v tests.test_process_group_kill_probe
python3 -m py_compile \
  tools/probe_process_group_kill.py \
  tests/test_process_group_kill_probe.py
python3 -W error::ResourceWarning tools/probe_process_group_kill.py
```

The dedicated workflow runs the complete matrix twice in `debian:sid-slim`, validates exact schema and topology, requires stable candidate selection across immediate reruns, and uploads package versions plus both records and streams.

## Evidence boundary

This unit characterizes current Linux command behavior and process topology. It does not establish an upstream mmdebstrap defect, a procps or dash defect, broad portability, product-source repair, or a Debian submission.

Any compatibility override first belongs only in PR #72's disposable source copy and requires the real package matrix to pass afterward.

## Stop rule

Stop and redesign the signal-delivery fixture when the repaired positive control or cleanup fails. Select a spelling only after both exact sid runs agree on whole-group delivery with unrelated-process containment and clean rerun.

## Authority

Internal Linux Fieldwork work only. External contact authorized: false.
