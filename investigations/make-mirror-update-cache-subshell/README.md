# make_mirror update_cache subshell signal ownership

## TL;DR

`update_cache()` runs in a pipeline subshell but used one cleanup-only `EXIT INT TERM` trap that killed the cache proxy owned by the top-level mirror process. A TERM delivered only to the subshell could kill that shared proxy, clean the subshell APT root twice, resume later work, and return status 0.

The retained candidate gives the subshell ownership of only its APT root. Ordinary EXIT cleanup preserves the incoming status. Executed INT, QUIT, and TERM cases clean once and exit 130, 131, or 143. The top-level pipeline receives that nonzero result and its own EXIT cleanup stops and waits for the proxy.

## Explain like I'm five

A worker has a temporary desk and borrows a robot owned by its manager. The old stop rule made the worker clean its desk, switch off the manager's robot, then continue working and report success.

The candidate makes the worker clean only its desk and stop. The manager sees the failure and switches off the manager-owned robot.

## Why care

The old ownership can turn cancellation into success, kill a shared proxy from the wrong process, perform cleanup twice, and make the top-level mirror continue until a later unrelated failure. A surviving or prematurely killed proxy can also interfere with an immediate rerun.

## Canonical records

- issue: #231;
- top-level parent lifecycle: PR #224;
- imported source: `upstream/mmdebstrap/make_mirror.sh` blob `6c4be092edcf23b56b63a3befe238c099c45f590`;
- candidate patch: `0001-confine-update-cache-signal-cleanup.patch`;
- ownership regression: `tests/test_make_mirror_update_cache_signal_ownership.py`;
- complete signal matrix: `tests/test_make_mirror_update_cache_signal_matrix.py`;
- stacked branch: `investigation/make-mirror-update-cache-subshell`.

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

## Candidate

The retained patch installs two subshell-local helpers:

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

The handlers produce these contracts:

- ordinary implicit EXIT: clean the APT root while preserving the primary status;
- INT/QUIT/TERM: clean once and exit 130/131/143;
- no subshell path signals `$PROXYPID`;
- ordinary success still calls `cleanupapt` explicitly and clears every subshell trap;
- pipeline failure reaches the top-level `set -e` owner, whose own cleanup stops and waits for the proxy.

Cleanup errors remain secondary on failure and signal paths. The candidate deliberately leaves cleanup-error reporting after an otherwise successful explicit `cleanupapt` unchanged.

## Executed local model gates

Commands:

```text
python3 -m unittest -v tests/test_make_mirror_update_cache_signal_ownership.py
python3 -m unittest -v tests/test_make_mirror_update_cache_signal_matrix.py
```

The original focused gate observed four passing tests in 1.562 seconds against a minimal source fixture carrying the exact imported trap and end-of-function contexts.

The dynamic `/bin/sh` matrices prove:

- baseline subshell-only TERM returns 0, executes both later markers, cleans twice, and kills the parent-owned proxy;
- candidate subshell-only INT, QUIT, and TERM return 130, 131, and 143 through the parent pipeline;
- every executed signal omits both later markers, cleans the APT state once, and lets the parent stop and wait for the proxy once;
- immediate unsignaled rerun after each signal succeeds, cleans once, and leaves no APT marker or proxy;
- ordinary failure 42 remains 42 when cleanup returns 74;
- TERM 143 remains 143 when cleanup returns 74;
- the retained patch applies to the exact fixture and the candidate passes `/bin/sh -n`;
- source assertions remove proxy signaling from the complete `update_cache()` block and require explicit INT/QUIT/TERM mappings.

Repository CI is the exact imported-source gate. It must apply the retained patch to blob `6c4be092…`, run `/bin/sh -n` on the complete script, and execute both focused matrices.

## Cleanup and rerun

Every dynamic process and file lives below `TemporaryDirectory`. Signals target only worker shells created by the tests. The parent waits for its proxy child, candidate cleanup removes the APT-state marker, and each immediate rerun uses a fresh disposable runtime path successfully.

The baseline intentionally lets the subshell kill the parent-owned proxy; the parent still performs `wait()` during its EXIT cleanup so no zombie remains.

## Composition and overlap

PR #224 owns top-level proxy launch registration, first-signal retention, proxy reaping, cache-state ownership, and top-level cancellation. This candidate is stacked on that exact evidence head but changes a separate retained source region inside `update_cache()`.

The two mechanisms compose through the pipeline result:

1. the subshell exits with its own cancellation status;
2. the top-level `set -e` path exits with that status;
3. top-level EXIT cleanup stops and waits for the parent-owned proxy.

The focused PR #224 can finish independently. This follow-up should remain a separate source patch and review unit.

## Evidence boundary

The reduced matrix uses real `/bin/sh`, signals, pipelines, child processes, and files. It does not execute APT, mirror downloads, QEMU, network traffic, root operations, or the complete multi-architecture loop.

A signal delivered while the subshell waits for a foreground APT process may remain deferred until that process exits. The candidate does not forward signals to foreground commands, use process groups, add timeouts, or add TERM-to-KILL escalation.

The exact imported source patch and complete repository suite still require hosted execution. Public current-upstream composition and any external packet require a separate refresh and explicit authorization.

## Disposition

`EXECUTE` as a focused stacked evidence carrier. Promote only after exact-head repository CI, complete four-file review, cleanup/rerun confirmation on the published head, and reconciliation with PR #224's final state.

Internal Linux Fieldwork work only. No external contact is authorized or performed.
