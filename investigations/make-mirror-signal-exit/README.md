# make_mirror signal and proxy ownership

Tracking: issues #157 and #221; parent repair PR #205; current carrier PR #224.

## TL;DR

`make_mirror.sh` used cleanup-only signal traps and started each proxy in two shell steps: launch the child, then save `$!`. A signal accepted between those steps could run cleanup before the new child had an owner.

The candidate records the first INT/QUIT/TERM during each launch interval, registers the child PID, dispatches the retained first status if necessary, and restores ordinary terminating traps only after confirming that no signal is pending. It stops and waits for the owned child, keeps cache and QEMU cleanup tied to their real ownership states, preserves an active published cache, and exits with status 130, 131, or 143 after cleanup.

The exact head must pass repository CI after the ownership-state and first-signal repairs. Full mirror execution, proxy escalation, and the subshell-local `update_cache()` trap remain separate.

## Explain like I'm five

The script starts a helper and writes down its number. A stop signal could arrive after the helper starts but before the number is written down.

The repair temporarily writes “stop requested,” records the helper's number, then stops and waits for that exact helper. If a second stop request arrives, the first request still decides the exit status.

There are also two different cleanup moments:

```text
launch one, before readiness:
  proxy exists
  private cache deletion is not yet owned
  stop owner + proxy
  retain pre-readiness cache state for the next preflight

launch two, during QEMU work:
  proxy exists
  private cache is already owned
  stop owner + proxy
  delete private cache and active temporary state
```

## Why care

An unowned proxy can retain port 8080, interfere with an immediate rerun, and leave a mirror command reporting cancellation while its child survives.

Cleanup overclaims are also dangerous. Calling cache deletion before ownership begins can hide retained state. A test that forces post-readiness ownership into the first launch can pass while proving a lifecycle the product never has.

## Intent and precedent

The source comment promises that cancellation must never leave the active cache unusable. The existing two-cache design distinguishes an active published cache from a private candidate cache.

The candidate therefore separates:

- child ownership and reaping;
- private cache deletion;
- QEMU temporary-directory cleanup;
- active published-cache preservation;
- signal-derived exit status.

This is a design choice inferred from the source lifecycle and existing cache marker, rather than a claim about external upstream intent.

## Source boundary

- imported source: `upstream/mmdebstrap/make_mirror.sh`
- candidate patch: `0001-preserve-signal-exit-status.patch`
- combined regression: `tests/test_make_mirror_signal_exit.py`
- independent ownership-state regression: `tests/test_make_mirror_proxy_launch_ownership.py`

The original source starts each proxy with:

```sh
./caching_proxy.py ... &
PROXYPID=$!
```

Before first readiness, `CLEANUP_PROXY_CACHE` remains `no`. After readiness the script creates its marker and owns cleanup of the private new cache. The QEMU relaunch occurs later under that owned state.

## Candidate

The patch introduces:

- `handle_launch_signal STATUS`: retain only the first signal accepted during launch registration and dispatch that retained status as soon as the child PID is owned;
- `launch_proxy`: install launch handlers, start the child, save `$!`, dispatch any retained first signal, then restore ordinary terminating traps;
- `stop_proxy`: signal if alive, always wait, and clear the PID;
- `cleanup_owner`: stop the proxy, remove active QEMU temporary state when owned, and delete only a private unpublished cache when owned;
- `signal_exit STATUS`: clear traps, clean once, and exit 130, 131, or 143;
- active-symlink inspection so a cache already published through `shared/cache` survives late cleanup.

Normal successful proxy stops use `stop_proxy()` without invoking failed-cache cleanup. Keeping the launch handler active through pending-signal dispatch closes the trap-handoff interval in which a later signal could otherwise overtake the first one.

## Reproduction

Focused commands:

```sh
python3 -m unittest -v tests/test_make_mirror_signal_exit.py
python3 -m unittest -v tests/test_make_mirror_proxy_launch_ownership.py
```

Both tests apply the exact patch to a disposable source copy and check `/bin/sh -n`.

### Combined matrix

The main regression proves:

- the cleanup-only baseline resumes and exits 0 after parent-only TERM;
- the candidate exits 143, omits later work, stops and reaps the proxy;
- an ordinary rerun exits 0 and cleans through EXIT once;
- a cache already published through `shared/cache` is preserved;
- both PID-registration intervals dispatch owner-only TERM after child ownership;
- launch one uses `CLEANUP_PROXY_CACHE=no`, calls `cleanup_owner()` once, stops the proxy once, and performs zero cache-deletion calls;
- launch one's retained pre-readiness state is removed by an immediate rerun before the new run completes normally;
- launch two uses `CLEANUP_PROXY_CACHE=yes`, calls `cleanup_owner()` once, reaches `stop_proxy()` twice including the completed first proxy, and deletes the private cache once;
- TERM delivered before PID assignment remains the winning status when INT arrives after assignment and before ordinary trap restoration.

The separate ownership-state regression independently checks the two ownership states, cleanup counts, proxy removal, unsignaled reruns, and source order around first readiness and the QEMU relaunch.

“Cleanup once” means one `cleanup_owner()` dispatch. Owner cleanup, proxy stops, and state-specific cache deletion are counted separately.

## Results

Earlier exact heads established the parent repair and active-cache preservation:

- Linux Fieldwork CI `30577821799`: repaired patch carrier;
- Linux Fieldwork CI `30578032937`: code/test head with published-cache ownership repair.

Issue #221 identified the remaining launch-to-PID intervals. The first current carrier head added deterministic stopped-owner controls but modeled cache-deletion ownership as `yes` for both launches. Independent review classified that as a test-fidelity overclaim and added the ownership-specific regression.

Complete review then found a trap-handoff race: ordinary traps were restored before the pending first signal was dispatched, allowing a later signal to decide the status. The combined repair keeps the launch handler active through dispatch and adds a deterministic TERM-then-INT control.

Seven main-regression tests pass twice consecutively on the combined local tree. The separate ownership-state suite and exact-head hosted CI are rerun after every combined-head change.

## Interpretation

**Demonstrated by tests:** cleanup-only traps can resume later work and report false success; the candidate terminates with signal-derived status and reaps the proxy.

**Product repair:** first-signal handling closes both child-launch/PID-registration intervals and preserves first-signal precedence through trap handoff.

**Test repair:** owner cleanup is common to both launches; cache deletion belongs only to the later owned state; retained launch-one state is checked by immediate rerun.

**Open question:** full mirror execution may expose additional timing or retained-state behavior outside the reduced shell harnesses.

## Evidence boundary

The regressions use disposable directories, symlinks, logs, and `sleep` children. They do not run a mirror, APT, QEMU, network listener, package operation, or privileged mount.

The patch does not add escalation for a proxy that ignores TERM. Parent-only delivery may still be deferred while the shell waits for an unrelated foreground command. Signal termination is represented as conventional `128 + signal` exit status rather than kernel-level re-raising.

The subshell-local trap inside `update_cache()` remains outside this top-level owner repair.

## Next step

`HOLD` until the five-file combined candidate has:

- exact-head repository CI;
- both focused regressions;
- complete patch/source review;
- cleanup/rerun receipt and overlap check;
- external-contact state recorded.

## Authority

Internal Linux Fieldwork work only. No Debian or other external issue, email, patch, merge request, comment, or review is authorized or included.
