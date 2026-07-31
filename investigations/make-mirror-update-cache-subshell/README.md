# make_mirror update_cache subshell signal ownership

State: `landed baseline — cleanup-time signal successor active`

## TL;DR

`update_cache()` runs in a pipeline subshell. The imported source used one cleanup-only `EXIT INT TERM` trap that killed the cache proxy owned by the top-level process. A signal delivered only to the subshell could kill the wrong owner's child, clean twice, resume later work, and return success.

The focused repair landed through PR #286. The worker now cleans only its APT root, leaves proxy stop/wait to the top-level owner, reports INT/QUIT/TERM as 130/131/143, routes every completion path through one finalizer, runs cleanup once, and preserves ordinary or signal failure over cleanup failure.

Signals arriving *during* that bounded cleanup are a separate lifecycle boundary. Clean current-main PR #324 carries that successor investigation and must be reviewed and landed independently.

## Explain like I'm five

A worker owns a temporary desk and borrows a robot from its manager. The worker cleans only its desk. The manager switches off the robot.

Every ordinary finish or stop request now uses one checkout counter, so the desk is cleaned once and the strongest result survives. A separate follow-up checks what happens when another stop request arrives while the desk is already being cleaned.

## Why care

Cross-owner cleanup can convert cancellation into success, kill shared state from the wrong process, and interfere with reruns. Duplicate cleanup after a first cleanup failure can repeat partially destructive work and hide the operation that failed first.

The final record must also distinguish the landed baseline from later cleanup-time signal work. Otherwise a reader could assume that every signal ordering was already proved by PR #286.

## Canonical landed result

- owning issue: #231, closed with final receipt;
- parent top-level lifecycle: PR #224, merge `386f5c8dbb01e5de1af45ac0eb325ee8567722e3`;
- canonical worker-lifecycle carrier: PR #286;
- exact reviewed PR head: `2c85afa8c947ff040b4c6d876d9b88cf545dbb59`;
- merge commit on `main`: `782774b01002abf37878d834a54d0bbf8b226397`;
- exact-head Linux Fieldwork CI: `30624335126` / 842, success;
- repository discovery: 249 tests, success;
- imported source blob: `6c4be092edcf23b56b63a3befe238c099c45f590`;
- changed unit: exactly five declared files;
- external contact: unauthorized and none.

Historical construction carriers #238, #259, #260, and #267 are not landing surfaces. Their unique mechanism and evidence were transferred into PR #286. PRs #259 and #260 were closed after the final merge; #267 had already been retired.

## Source and ownership boundary

`update_cache()` is the last command in a pipeline and therefore runs in its own process. It creates and owns `$rootdir`. The top-level shell starts, records, stops, and waits for `$PROXYPID`.

The imported trap crossed those owners:

```sh
trap 'kill "$PROXYPID" || :;cleanupapt' EXIT INT TERM
```

The handler also lacked a terminating action, so deferred delivery could resume later work.

## Landed mechanism

The landed patch uses one completion function:

```sh
update_cache_finish() {
  status=$1
  trap - EXIT INT QUIT TERM
  cleanup_status=0
  cleanupapt || cleanup_status=$?
  if [ "$status" -ne 0 ]; then
    exit "$status"
  fi
  exit "$cleanup_status"
}
```

Wrappers pass ordinary `$?` or explicit signal status. The successful path calls `update_cache_finish 0` directly.

The landed precedence is:

```text
ordinary or signal failure > cleanup failure > success
```

The complete landed contract is:

- implicit EXIT preserves the incoming status;
- INT/QUIT/TERM return 130/131/143;
- no worker path signals `$PROXYPID`;
- successful completion clears traps before cleanup;
- cleanup runs once;
- successful work plus cleanup failure reports that cleanup status;
- an existing ordinary or signal failure remains authoritative;
- top-level `set -e` receives a nonzero pipeline result;
- the top-level owner alone stops and waits for the proxy;
- immediate unsignaled reruns remain clean.

## Executed evidence

Exact-head CI for PR #286 established:

- baseline worker-only TERM returned 0, executed later work, cleaned twice, and killed the parent-owned proxy;
- candidate worker-only INT, QUIT, and TERM returned 130, 131, and 143;
- signal paths omitted later work, cleaned APT state once, and let the parent reap the proxy;
- ordinary failure 42 and TERM 143 survived cleanup status 74;
- successful work plus cleanup failure returned 74 after one cleanup;
- immediate unsignaled reruns succeeded;
- zero-fuzz patch application and complete `/bin/sh -n` passed;
- each focused ownership case ran once after the test-helper import repair.

## Cleanup-time signal successor

PR #324 adds three files directly on the landed PR #286 source generation:

- `0002-retain-signals-through-cleanup.patch`;
- `CLEANUP_SIGNALS.md`;
- `tests/test_make_mirror_update_cache_cleanup_signals.py`.

That successor asks whether the first INT/QUIT/TERM arriving during ordinary cleanup should be retained while later handled signals are ignored and bounded cleanup completes. It also checks whether an already-selected ordinary or explicit-signal failure remains ahead of a cleanup-time signal.

Historical PR #305 prepared the same three blobs on the pre-merge PR #286 branch. Retargeting it replayed the squashed baseline, so it was closed after exact transfer to PR #324.

PR #324 is separate from the landed baseline. It requires exact-head execution, complete three-file review, and a clean current-main landing decision.

## Cleanup and safety

Focused tests use disposable directories, `/bin/sh`, owned subprocesses, signals, waits, and files. Signals target only test-created processes. No APT, mirror download, QEMU, network, root operation, or complete multi-architecture loop runs.

Foreground descendant cancellation latency was investigated separately in issue #263 / PR #264 and stopped without source expansion.

## Evidence boundary

The landed reductions prove shell trap behavior, result precedence, cleanup ownership, proxy reaping, and immediate rerun for the extracted worker lifecycle. They do not run the full mirror loop, prove prompt foreground-descendant cancellation, cover permanently blocking cleanup, or settle signals arriving during cleanup itself.

The next useful action is exact-head CI and complete review for PR #324's zero-fuzz two-patch composition and deterministic signal matrix.

Internal Linux Fieldwork work only. External contact authorized: `false`.
