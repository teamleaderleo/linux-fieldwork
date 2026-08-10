# Bubblewrap PID 1 exposes the pre-transformation environment

## TL;DR

Current Bubblewrap main (`2f55bae38468d0c50cf5df87b1e481e882b63acb`) applies `--clearenv`, `--unsetenv`, and `--setenv` to libc's environment before the sandbox command is exec'd. In the ordinary `--unshare-pid` path, Bubblewrap also keeps a non-exec'd PID-1 helper. Linux `/proc/PID/environ` reads that process's exec-time environment region, so libc environment changes can disagree with what `/proc/1/environ` exposes.

A synthetic Linux control reproduced the representation split for all three transformations: `getenv()` reflected clear/unset/set while `/proc/self/environ` retained the original marker and did not gain the replacement marker. Upstream issue #725 independently reports the Bubblewrap `--clearenv` symptom. Exact-current Bubblewrap runtime execution is the first incomplete gate.

The likely defect boundary is broader than `--clearenv`: when a new procfs is mounted inside the PID namespace, a same-UID sandbox command can potentially observe the helper's pre-transformation launch environment through `/proc/1/environ`. The fixture uses only a harmless synthetic marker.

Internal Fieldwork issue: #565.

## Explain like I'm five

Bubblewrap changes the list of environment variables that the program will receive. With a PID namespace it also leaves a small Bubblewrap helper running as process 1.

Linux has two views here:

```text
program asks getenv("FIELDWORK_MARKER") -> transformed value
program reads /proc/1/environ          -> helper's original launch value
```

The helper never execs a new program, so its `/proc/1/environ` can keep the old bytes even after Bubblewrap calls `clearenv()`, `unsetenv()`, or `setenv()`.

## Why care

Environment options are commonly used to prevent launch-time values from reaching the sandbox command. If the sandbox can read a second copy of those original values from its PID-1 helper, the command-visible environment and procfs-visible environment disagree.

The practical consequence depends on caller behavior: a caller must use the PID-helper path, mount procfs into the sandbox, and have readable access to PID 1's environment. Current Bubblewrap deliberately marks the sandbox-side process dumpable after dropping privileges, which makes same-UID procfs inspection relevant to the exact-current probe.

This investigation uses a synthetic marker only. No credentials, private data, or live external system is involved.

## Current state

- State: `EXECUTING`
- Exact upstream head: `containers/bubblewrap@2f55bae38468d0c50cf5df87b1e481e882b63acb`
- Tracked probe: `investigations/bubblewrap-pid1-environ/repro_pid1_environ.py`
- Local model: passed for clearenv, unsetenv, and setenv
- First incomplete step: exact-current Bubblewrap execution under a namespace-capable runner
- Cleanup state: model children reaped; no retained process or modified external state
- Next safe action: run exact-current helper cases plus `--as-pid-1` control, then decide candidate boundary
- External-contact state: no upstream contact authorized or made

## Intent and precedent

### Original `--clearenv` intent

Commit `8f72ceb2c42a2d93c858b8775a88f13b891c8120` added `--clearenv` so variables could exist while running Bubblewrap itself but be cleared for the command in the container without enumerating each variable. Its test checks the exec'd command's `/usr/bin/env` output.

Primary source:

- https://redirect.github.com/containers/bubblewrap/commit/8f72ceb2c42a2d93c858b8775a88f13b891c8120

### Current implementation

At exact current main:

- `parse_args_recurse()` handles `--clearenv` by calling `xclearenv()`;
- `utils.c::xclearenv()` is a plain `clearenv()` wrapper;
- `--setenv` and `--unsetenv` use libc `setenv()` / `unsetenv()` wrappers;
- the PID namespace path forks a helper that runs `do_init()` instead of exec'ing the command;
- the command child later executes `execvp()` with the transformed libc environment;
- `drop_privs()` marks the sandbox-side process dumpable after dropping privileges.

The current environment tests assert only what the exec'd command sees. They do not compare the helper's procfs representation.

### Upstream report

Upstream issue #725 reports that `--unshare-pid --proc /proc --clearenv` leaves the original environment visible in `/proc/1/environ` unless `--as-pid-1` is used.

- https://redirect.github.com/containers/bubblewrap/issues/725

The issue remains open and has no comments at the investigation boundary.

## Question

At exact current Bubblewrap main, which environment transformations are visible through the PID-1 helper's `/proc/1/environ`, and does `--as-pid-1` remove the discrepancy by making the exec'd command itself PID 1?

## Source

- Project: `containers/bubblewrap`
- Requested revision: current default branch at investigation start
- Resolved commit: `2f55bae38468d0c50cf5df87b1e481e882b63acb`
- Candidate source commit: none
- Source access: exact GitHub revision through connector; hosted runtime will clone the same exact SHA
- Imported local source tree: none

## Environment

Local synthetic model:

- Distribution: Debian GNU/Linux 13 (trixie)
- Kernel: Linux 6.18.35
- Architecture: x86_64
- Python: 3.13.5
- Privileges: uid 0 in a disposable runner
- Marker: `FIELDWORK_MARKER=fieldwork-old-marker`

The model calls libc `clearenv()`, `unsetenv()`, or `setenv()` in a child process and compares libc `getenv()` with `/proc/self/environ`.

## Baseline behavior

The relevant representation chain is:

1. Bubblewrap starts with the caller's exec-time environment.
2. Argument parsing mutates libc's environment according to `--clearenv`, `--unsetenv`, or `--setenv`.
3. Bubblewrap later creates the PID-1 helper by `fork()` on the normal `--unshare-pid` path.
4. The helper does not `exec()`, so its process image still descends from Bubblewrap's original exec.
5. The command child later `execvp()`s the requested executable with the transformed environment.
6. A procfs mounted for the PID namespace presents the helper as `/proc/1`.

Linux libc environment mutation changes the environment vector used by `getenv()` and future `execve()` calls. The kernel's procfs environment view refers to the process's exec-time environment memory range unless that range is explicitly changed.

## Hypothesis or candidate

### Hypothesis

With a harmless initial marker `FIELDWORK_MARKER=fieldwork-old-marker`:

```text
--clearenv + helper:
  command getenv -> absent
  /proc/1/environ -> old marker present

--unsetenv FIELDWORK_MARKER + helper:
  command getenv -> absent
  /proc/1/environ -> old marker present

--setenv FIELDWORK_MARKER fieldwork-new-marker + helper:
  command getenv -> new marker
  /proc/1/environ -> old marker present, new marker absent

--clearenv + --as-pid-1 control:
  command getenv -> absent
  /proc/1/environ -> old marker absent
```

### Candidate boundary

No candidate is selected yet.

Possible repair families include changing the helper's process-image boundary or deliberately scrubbing the original environment storage when an option promises to remove or replace values. Any such candidate must preserve values Bubblewrap itself still needs during setup, preserve command environment ordering semantics, and avoid changing unrelated process-lifecycle behavior.

## Reproduction

### Synthetic Linux model

```sh
FIELDWORK_MARKER=fieldwork-old-marker \
  python3 investigations/bubblewrap-pid1-environ/repro_pid1_environ.py --model
```

Observed locally:

```text
clearenv: getenv=None proc_old=True proc_new=False
unsetenv: getenv=None proc_old=True proc_new=False
setenv: getenv='fieldwork-new-marker' proc_old=True proc_new=False
```

### Exact-current Bubblewrap probe

Prepared command:

```sh
python3 investigations/bubblewrap-pid1-environ/repro_pid1_environ.py \
  --bwrap /path/to/bwrap-built-from-2f55bae38468d0c50cf5df87b1e481e882b63acb
```

The probe runs four cases against a fresh procfs in the PID namespace:

```text
clearenv-helper
unsetenv-helper
setenv-helper
clearenv-as-pid-1-control
```

For each case it records the command's `getenv()` view and whether `/proc/1/environ` contains the old or replacement synthetic marker.

## Results

### Exact-current source review

Established:

- current `xclearenv()` delegates directly to libc `clearenv()`;
- current set/unset operations also mutate libc's environment rather than the kernel procfs environment bounds;
- the normal PID namespace helper is forked and does not exec;
- the command itself later execs with the transformed environment;
- current tests verify the command environment and leave the helper representation untested;
- `drop_privs()` sets `PR_SET_DUMPABLE` to 1 on the sandbox-side process after dropping privileges.

### Synthetic model

All three transformations produced the same representation class: libc `getenv()` changed while the procfs environment continued to contain the original marker. `setenv()` also failed to make the replacement value appear in procfs.

This demonstrates the underlying Linux process behavior independently of Bubblewrap.

### Product runtime

Pending exact-current hosted execution.

## Interpretation

The source and model identify a cross-representation contract drift: Bubblewrap's command environment and helper procfs environment can describe different launch environments.

The original `--clearenv` implementation and tests were written around the environment received by the exec'd command. PID-helper mode adds another command-visible process whose procfs representation survives the libc transformation. `--unsetenv` and `--setenv` appear to inherit the same mechanism even though the public upstream report names only `--clearenv`.

A current-runtime claim still requires execution of the exact Bubblewrap head because procfs visibility also depends on the PID namespace, proc mount, credentials, and dumpability in the complete product path.

## Evidence boundary

Established now:

- exact source mechanism at `2f55bae38468d0c50cf5df87b1e481e882b63acb`;
- original `--clearenv` intent and test scope;
- generic Linux clear/set/unset versus procfs representation behavior;
- upstream historical/current report for `--clearenv`.

Still open:

- exact-current Bubblewrap runtime outcome for all four cases;
- other libc implementations beyond the exact hosted environment;
- hidepid, LSM, ptrace, uid/gid, or procfs mount policy variants that could restrict reads;
- whether a viable repair should scrub original storage, change the helper exec boundary, or use another design;
- compatibility effects of any candidate.

## Next step

1. Build exact current Bubblewrap in hosted CI.
2. Run the four-case synthetic-marker probe in a namespace-capable disposable environment.
3. If reproduced, add a negative control where procfs access is unavailable or credentials differ only if it changes the repair boundary.
4. Test candidate families against command-visible environment behavior and helper-visible procfs behavior.
5. Keep any upstream packet internal until explicit authorization.

## Authority

No upstream issue, comment, pull request, email, patch submission, or review has been created or modified by this investigation. The upstream issue and commits are read-only evidence.