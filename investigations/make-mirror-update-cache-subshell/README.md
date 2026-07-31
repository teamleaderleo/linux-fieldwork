# make_mirror update_cache subshell signal ownership

State: `repair-executed-locally-by-contract — exact-head gate pending`

## TL;DR

`update_cache()` runs in a pipeline subshell. The imported source used one cleanup-only `EXIT INT TERM` trap that killed the cache proxy owned by the top-level process. A signal delivered only to the subshell could kill the wrong owner's child, clean twice, resume later work, and return success.

The candidate confines the subshell to its APT root, reports INT/QUIT/TERM as 130/131/143, preserves ordinary failure, and lets the top-level owner stop and wait for the proxy.

Exact-head review `4824871557` found a second cleanup path: successful work called `cleanupapt` before clearing the EXIT trap. A cleanup failure under `set -e` entered the EXIT handler and ran cleanup again. The repaired candidate now routes ordinary completion, implicit EXIT, and signals through one `update_cache_finish` function. Cleanup runs once; an existing command or signal failure wins; otherwise cleanup failure becomes final.

## Explain like I'm five

A worker owns a temporary desk and borrows a robot from its manager. The worker cleans only its desk. The manager switches off the robot.

When the worker finishes, stops, or discovers a cleanup failure, every path now uses the same checkout counter. The desk gets cleaned once and the most useful result survives.

## Why care

Cross-owner cleanup can turn cancellation into success, kill a shared proxy from the wrong process, and interfere with reruns. Duplicate cleanup after a first cleanup failure can repeat partially destructive work and cover the operation that failed first.

## Canonical records

- issue: #231;
- merged top-level parent lifecycle: PR #224, merge `386f5c8dbb01e5de1af45ac0eb325ee8567722e3`;
- historical stacked carrier: PR #238;
- first clean restack: PR #259;
- current carrier: PR #267;
- PR base: `da52cbfdabe84744017d1a5286314620d4d3286e`;
- exact head: `70bd1e4719f0b4e6e5956a4dc65744915432e383`;
- imported source blob: `6c4be092edcf23b56b63a3befe238c099c45f590`;
- repair review: `4824871557`;
- superseded queued run: `30596903218` / 772 on prior head `c066db4046626cbed0b1c186cb52b9dffa72554a`.

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

The new regression applies the patch with zero fuzz, checks the complete script with `/bin/sh -n`, executes successful work followed by cleanup status 74, requires one cleanup call and final status 74, and performs an immediate clean rerun.

## Retained evidence

Earlier focused execution established:

- baseline subshell-only TERM returns 0, executes later work, cleans twice, and kills the parent-owned proxy;
- candidate worker-only INT, QUIT, and TERM return 130, 131, and 143;
- signal paths omit later work, clean APT state once, and let the parent reap the proxy;
- ordinary failure 42 and TERM 143 survive cleanup status 74;
- immediate unsignaled reruns succeed;
- exact patch application and complete shell syntax pass.

The new exact head must rerun all retained controls plus the successful-cleanup-failure case.

## Cleanup and safety

Focused tests use disposable directories, `/bin/sh`, owned subprocesses, signals, waits, and files. Signals target only test-created processes. No APT, mirror download, QEMU, network, root operation, or complete multi-architecture loop runs.

Foreground descendant cancellation latency was investigated separately in issue #263 / PR #264 and stopped without source expansion.

## Current disposition

`REPAIR COMPLETE — EXECUTE` on exact head `70bd1e47...`.

Promotion requires:

1. fresh Linux Fieldwork CI on this exact head;
2. zero-fuzz patch application to the complete imported source;
3. `/bin/sh -n` and all three focused modules;
4. repository discovery without duplicate cases;
5. fresh complete five-file review;
6. current head/base relation suitable for internal landing;
7. retirement of historical duplicate carriers after evidence transfer.

Internal Linux Fieldwork work only. External contact authorized: `false`.
