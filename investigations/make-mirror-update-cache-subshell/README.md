# make_mirror update_cache subshell signal ownership

State: `delivery-gate-ready`

## TL;DR

`update_cache()` runs in a pipeline subshell but the imported source used one cleanup-only `EXIT INT TERM` trap that killed the cache proxy owned by the top-level mirror process. A TERM delivered only to the subshell could kill that shared proxy, clean the subshell APT root twice, resume later work, and return status 0.

The retained candidate gives the subshell ownership of only its APT root. Ordinary EXIT cleanup preserves the incoming status. INT, QUIT, and TERM clean once and exit 130, 131, or 143. The top-level pipeline receives that nonzero result and its own EXIT cleanup stops and waits for the proxy.

This directory is the second clean current-main generation. The retained patch and both executable tests are byte-identical to historical PRs #238 and #259. Only this README changes to record the new base and delivery state.

## Canonical records

- issue: #231;
- merged top-level parent lifecycle: PR #224, merge commit `386f5c8dbb01e5de1af45ac0eb325ee8567722e3`;
- historical stacked carrier: PR #238 at `f6966f0ccd6c3ea91ae39c260f23e6e416b5c601`;
- first clean restack: PR #259 at `d270f558fa7c32569ea380fd614c34edaf60b3b3`;
- current source-generation base: Linux Fieldwork main `b8a85215844a28db0d8f23e56822eda46445ba53`;
- current branch: `restack/make-mirror-update-cache-main-20260731-r2`;
- imported source blob: `6c4be092edcf23b56b63a3befe238c099c45f590`;
- candidate patch blob: `f09f666a39a135ec8beb4b612618b2d54ec4f998`;
- ownership regression blob: `c3fa92f4d29a445e410d086dd0ee0685fec424a0`;
- signal-matrix blob: `bbff77d45dd889704840417fdea7631a6e352ed0`.

## Source and ownership boundary

`update_cache()` is parenthesized because it is the last command in pipelines such as:

```sh
echo "deb ..." | update_cache "$dist" "$nativearch"
```

The subshell creates and owns `$rootdir`. The top-level shell starts, records, stops, and waits for `$PROXYPID`. The imported trap crossed those owners:

```sh
trap 'kill "$PROXYPID" || :;cleanupapt' EXIT INT TERM
```

The trap contains no terminating action. On shells that defer a trap while waiting for a foreground command, the handler can return to ordinary commands after cleanup.

## Candidate contract

The patch installs two subshell-local helpers:

```sh
update_cache_exit_cleanup() {
  status=$?
  trap - EXIT INT QUIT TERM
  cleanupapt || :
  exit "$status"
}

update_cache_signal_exit() {
  status=$1
  trap - EXIT INT QUIT TERM
  cleanupapt || :
  exit "$status"
}
```

The contract is:

- ordinary implicit EXIT cleans the APT root while preserving the primary status;
- INT/QUIT/TERM clean once and exit 130/131/143;
- no subshell path signals `$PROXYPID`;
- ordinary success still calls `cleanupapt` explicitly and clears every subshell trap;
- the nonzero last-command pipeline result remains fatal under top-level `set -e`;
- top-level owner cleanup stops and waits for the proxy;
- cleanup errors remain secondary to an existing failure or signal.

## Retained execution

Historical local execution established:

- baseline subshell-only TERM returns 0, executes later work, cleans twice, and kills the parent-owned proxy;
- candidate worker-only INT, QUIT, and TERM return 130, 131, and 143 through the parent pipeline;
- every executed signal omits later markers, cleans APT state once, and lets the parent stop and wait for the proxy once;
- immediate unsignaled reruns succeed and leave no APT marker or proxy;
- ordinary failure 42 remains 42 when cleanup returns 74;
- TERM 143 remains 143 when cleanup returns 74;
- the patch applies to the pinned source and the candidate passes `/bin/sh -n`.

Exact current-generation hosted CI must apply the same patch to the complete imported script, execute both focused matrices, and pass repository discovery.

## Complete-diff identity

The current generation is directly based on `b8a85215…` and adds exactly four files:

1. retained source patch;
2. this investigation record;
3. ownership/precedence regression;
4. direct signal matrix.

The patch and both tests use the exact blob identities from #259. Current-main drift since merged #224 affected coordination files and separate file-mirror records, not the imported `make_mirror.sh` blob or this technical unit.

## Cleanup and safety

Every dynamic process and file in the focused tests lives below `TemporaryDirectory`. Signals target only subprocesses created by the tests. The parent waits for its proxy child, candidate cleanup removes the APT-state marker, and immediate reruns use fresh disposable state.

The baseline intentionally lets the worker kill the parent-owned proxy; the parent still waits during EXIT cleanup so no zombie remains.

## Evidence boundary

The matrices use real `/bin/sh`, signals, pipelines, child processes, waits, and files. They do not execute APT, mirror downloads, QEMU, network traffic, root operations, or the complete multi-architecture loop.

Prompt cancellation of foreground APT descendants, process-group delivery, timeout, and escalation were investigated separately in issue #263 / PR #264 and stopped without a source expansion.

Public current-upstream composition requires a separate refresh and explicit authorization.

## Current disposition

`delivery-gate-ready` / `EXECUTE` on the exact current-main generation. Promote to `land-ready` only after:

1. exact-head Linux Fieldwork CI passes the complete imported source and both focused matrices;
2. complete four-file review confirms the direct diff and blob identities;
3. the head and base relationship remain current enough for landing;
4. historical #238 and #259 are retired after evidence transfer.

Internal Linux Fieldwork work only. External contact authorized: `false`.
