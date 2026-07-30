# make_mirror signal and proxy ownership

Tracking: issues #157 and #221; parent repair PR #205; current carrier PR #224.

## TL;DR

`make_mirror.sh` used cleanup-only signal traps and started each proxy in two shell steps: launch the child, then save `$!`. A signal accepted between those steps could run cleanup before the new child had an owner.

The candidate records the first INT/QUIT/TERM during each launch interval, registers the child PID, restores terminating traps, then dispatches the recorded status through one owner-cleanup path. Independent review also repaired the proof boundary: launch one has no cache-deletion authority before readiness, while launch two owns a private cache and temporary QEMU state.

The exact head must pass repository CI after the ownership-state regression. Full mirror execution, proxy escalation, and the subshell-local `update_cache()` trap remain separate.

## Explain like I'm five

The script starts a helper and writes down its number. A stop signal could arrive after the helper starts but before the number is written down.

The repair temporarily writes “stop requested,” records the helper's number, then stops and waits for that exact helper.

There are also two different cleanup moments:

```text
launch one, before readiness:
  proxy exists
  new cache marker does not exist
  stop owner + proxy
  do not claim cache deletion

launch two, during QEMU work:
  proxy exists
  private cache is already owned
  stop owner + proxy
  delete private cache and active temporary state
```

## Why care

An unowned proxy can retain port 8080, interfere with an immediate rerun, and leave a mirror command reporting cancellation while its child survives.

Cleanup overclaims are also dangerous. Calling cache deletion before the marker exists can fail or hide retained state. A test that forces post-readiness ownership into the first launch can pass while proving a lifecycle the product never has.

## Intent and precedent

The source comment promises that cancellation must never leave the active cache unusable. The existing two-cache design distinguishes an active published cache from a private candidate cache.

The candidate therefore separates:

- child ownership and reaping;
- private cache deletion;
- QEMU temporary-directory cleanup;
- active published-cache preservation;
- signal-derived exit status.

This is a design choice inferred from the source lifecycle and existing cache marker, not a claim about external upstream intent.

## Source boundary

- imported source: `upstream/mmdebstrap/make_mirror.sh`
- candidate patch: `0001-preserve-signal-exit-status.patch`
- original regression: `tests/test_make_mirror_signal_exit.py`
- ownership-state regression: `tests/test_make_mirror_proxy_launch_ownership.py`

The original source starts each proxy with:

```sh
./caching_proxy.py ... &
PROXYPID=$!
```

Before first readiness, no `mmdebstrapcache` marker exists. After readiness the script creates that marker and owns cleanup of the private new cache. The QEMU relaunch occurs later under that owned state.

## Candidate

The patch introduces:

- `record_signal STATUS`: retain the first signal accepted during launch registration;
- `launch_proxy`: install recording traps, launch, save `$!`, restore terminating traps, dispatch any recorded status;
- `stop_proxy`: signal if alive, always wait, and clear the PID;
- `cleanup_owner`: stop the proxy, remove active QEMU temporary state when owned, and delete only a private unpublished cache when owned;
- `signal_exit STATUS`: clear traps, clean once, and exit 130, 131, or 143;
- active-symlink inspection so a cache already published through `shared/cache` survives late cleanup.

Normal successful proxy stops use `stop_proxy()` without invoking failed-cache cleanup.

## Reproduction

Focused commands:

```sh
python3 -m unittest -v tests/test_make_mirror_signal_exit.py
python3 -m unittest -v tests/test_make_mirror_proxy_launch_ownership.py
```

Both tests apply the exact patch to a disposable source copy and check `/bin/sh -n`.

### Original matrix

The original regression proves:

- cleanup-only baseline resumes and exits 0 after parent-only TERM;
- candidate exits 143, omits later work, stops and reaps the proxy;
- ordinary rerun exits 0 and cleans through EXIT once;
- a cache already published through `shared/cache` is preserved;
- both PID-registration intervals record owner-only TERM and later dispatch it.

### Ownership-state repair

The additional regression instruments the exact candidate functions but preserves the real states:

- launch one: `CLEANUP_PROXY_CACHE=no`, no cache marker, one owner cleanup, one proxy stop, zero cache-deletion calls;
- launch two: `CLEANUP_PROXY_CACHE=yes`, private cache state present, one owner cleanup, two proxy stops including the completed first proxy, one cache-deletion call;
- both signaled cases exit 143, omit later work, and leave no proxy;
- both immediate unsignaled reruns exit 0 and preserve the same ownership-specific cleanup counts;
- source-order assertions require cache ownership to change only after first launch/readiness and before the QEMU relaunch.

The test counts owner cleanup and proxy stop separately from cache deletion. “Cleanup once” now means one `cleanup_owner()` dispatch, not that every lifecycle owns the same resources.

## Results

Earlier exact heads established the parent repair and active-cache preservation:

- Linux Fieldwork CI `30577821799`: repaired patch carrier;
- Linux Fieldwork CI `30578032937`: code/test head with published-cache ownership repair.

Issue #221 identified the remaining launch-to-PID intervals. The first current carrier head added deterministic stopped-owner controls but modeled cache-deletion ownership as `yes` for both launches. Independent review classified that as a test-fidelity overclaim and added the ownership-specific regression on the successor head.

Exact-head hosted CI after that repair remains authoritative.

## Interpretation

**Demonstrated by existing tests:** cleanup-only traps can resume later work and report false success; the candidate terminates with signal-derived status and reaps the proxy.

**Product repair:** first-signal recording closes both child-launch/PID-registration intervals.

**Test repair:** owner cleanup is common to both launches; cache deletion belongs only to the later owned state.

**Open question:** full mirror execution may expose additional timing or retained-state behavior not represented by reduced shell harnesses.

## Evidence boundary

The regressions use disposable directories, symlinks, logs, and `sleep` children. They do not run a mirror, APT, QEMU, network listener, package operation, or privileged mount.

The patch does not add escalation for a proxy that ignores TERM. Parent-only delivery may still be deferred while the shell waits for an unrelated foreground command. Signal termination is represented as conventional `128 + signal` exit status rather than kernel-level re-raising.

The subshell-local trap inside `update_cache()` remains outside this top-level owner repair.

## Next step

The reviewer is deciding whether the five-file current candidate is sufficiently proved to merge locally after:

- exact-head repository CI;
- both focused regressions;
- complete patch/source review;
- confirmation that launch-one claims do not imply cache deletion;
- cleanup/rerun receipt and external-contact state.

## Authority

Internal Linux Fieldwork work only. No Debian or other external issue, email, patch, merge request, comment, or review is authorized or included.
