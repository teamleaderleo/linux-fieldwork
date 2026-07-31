# make_mirror update_cache subshell signal ownership

State: `carrier repaired — exact-head gate pending`

## TL;DR

`update_cache()` runs in a pipeline subshell. The imported source used one cleanup-only `EXIT INT TERM` trap that killed the cache proxy owned by the top-level process. A signal delivered only to the subshell could kill the wrong owner's child, clean twice, resume later work, and return success.

The candidate confines the subshell to its APT root, reports INT/QUIT/TERM as 130/131/143, preserves ordinary failure, and lets the top-level owner stop and wait for the proxy.

A later review found a second cleanup path: successful work called `cleanupapt` before clearing the EXIT trap. A cleanup failure under `set -e` entered the EXIT handler and ran cleanup again. The repaired candidate routes ordinary completion, implicit EXIT, and signals through one `update_cache_finish` function. Cleanup runs once; an existing command or signal failure wins; otherwise cleanup failure becomes final.

Current-main review then found a carrier-only duplicate-discovery defect: the signal-matrix module imported the helper `TestCase` class directly, so repository discovery executed the ownership suite twice. The current carrier imports the helper module instead. Product patch bytes are unchanged.

## Explain like I'm five

A worker owns a temporary desk and borrows a robot from its manager. The worker cleans only its desk. The manager switches off the robot.

When the worker finishes, stops, or discovers a cleanup failure, every path uses the same checkout counter. The desk gets cleaned once and the most useful result survives. The test helper is now used as a helper instead of being mistaken for a second copy of the test suite.

## Why care

Cross-owner cleanup can turn cancellation into success, kill a shared proxy from the wrong process, and interfere with reruns. Duplicate cleanup after a first cleanup failure can repeat partially destructive work and cover the operation that failed first.

Duplicate test discovery is a separate evidence problem: a green count can look broader than the unique behavior actually exercised. The current gate must show each focused case once.

## Canonical records

- issue: #231;
- merged top-level parent lifecycle: PR #224, merge `386f5c8dbb01e5de1af45ac0eb325ee8567722e3`;
- historical stacked carrier: PR #238;
- first clean restack: PR #259;
- repaired predecessor carrier: PR #267;
- current carrier: PR #286;
- current branch: `restack/make-mirror-update-cache-current-main-v3`;
- imported source blob: `6c4be092edcf23b56b63a3befe238c099c45f590`;
- live exact head and current base relation: PR #286 body.

## Source and ownership boundary

`update_cache()` is the last command in a pipeline and therefore runs in its own process. It creates and owns `$rootdir`. The top-level shell starts, records, stops, and waits for `$PROXYPID`.

The imported trap crossed those owners:

```sh
trap 'kill "$PROXYPID" || :;cleanupapt' EXIT INT TERM
```

The handler also lacked a terminating action, so deferred delivery could resume later work.

## Candidate contract

The repaired patch uses one completion function:

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

Wrappers pass ordinary `$?` or explicit signal status. The normal successful path calls `update_cache_finish 0` directly.

The precedence is:

```text
ordinary or signal failure > cleanup failure > success
```

The complete contract is:

- ordinary implicit EXIT preserves the incoming status;
- INT/QUIT/TERM clean once and exit 130/131/143;
- no subshell path signals `$PROXYPID`;
- ordinary successful completion clears traps before cleanup;
- a successful operation plus cleanup failure reports the cleanup status;
- an existing ordinary or signal failure remains authoritative;
- top-level `set -e` receives the nonzero pipeline result;
- the top-level owner alone stops and waits for the proxy;
- immediate unsignaled reruns remain clean.

## Five-file fence

1. retained source patch;
2. this investigation record;
3. ownership/precedence regression;
4. direct INT/QUIT/TERM matrix;
5. successful-work cleanup-failure regression.

The regressions apply the patch with zero fuzz, check the complete script with `/bin/sh -n`, execute successful work followed by cleanup status 74, require one cleanup call and final status 74, and perform an immediate clean rerun.

## Executed evidence

Pre-repair current-main head `705935835a879e7f692fd0a7e666fb3747e30b5b` passed Linux Fieldwork CI `30623483339` / 824. The intended `lab-tools` job ran 245 tests, and the focused mechanism cases passed:

- baseline subshell-only TERM returned 0, executed later work, cleaned twice, and killed the parent-owned proxy;
- candidate worker-only INT, QUIT, and TERM returned 130, 131, and 143;
- signal paths omitted later work, cleaned APT state once, and let the parent reap the proxy;
- ordinary failure 42 and TERM 143 survived cleanup status 74;
- successful work plus cleanup failure returned 74 after one cleanup;
- immediate unsignaled reruns succeeded;
- zero-fuzz patch application and complete shell syntax passed.

That run also exposed the helper ownership suite twice under two module names. It is authoritative for the unchanged mechanism but does not satisfy the unique-discovery landing gate.

## Cleanup and safety

Focused tests use disposable directories, `/bin/sh`, owned subprocesses, signals, waits, and files. Signals target only test-created processes. No APT, mirror download, QEMU, network, root operation, or complete multi-architecture loop runs.

Foreground descendant cancellation latency was investigated separately in issue #263 / PR #264 and stopped without source expansion.

## Evidence boundary

The reductions prove shell trap, result precedence, cleanup ownership, proxy reaping, and immediate rerun for the extracted lifecycle. They do not run the full mirror loop or prove foreground descendant cancellation latency. Signals arriving during the cleanup routine itself are not separately characterized by this carrier.

## Current disposition

`CARRIER REPAIRED — EXECUTE`.

Promotion requires:

1. fresh Linux Fieldwork CI on the exact head named by PR #286;
2. zero-fuzz patch application to the complete imported source;
3. `/bin/sh -n` and all three focused modules;
4. repository discovery with each ownership case exactly once;
5. fresh complete five-file review;
6. current head/base relation suitable for internal landing;
7. retirement of historical duplicate carriers after evidence transfer.

Internal Linux Fieldwork work only. External contact authorized: `false`.
