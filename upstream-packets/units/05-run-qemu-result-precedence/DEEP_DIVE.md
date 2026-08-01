# Deep dive — `run_qemu.sh` result and cleanup precedence

## Original mechanism

The imported script installed one function for three distinct events:

```sh
trap cleanup INT TERM EXIT
```

That function captured `$?`, removed temporary state, read `shared/exitstatus.txt`, converted any guest failure to 1, and exited. The mechanism mixed five independently owned outcomes:

1. host/QEMU/timeout result;
2. guest or protocol result;
3. explicit INT or TERM;
4. INT or TERM received during ordinary cleanup;
5. cleanup failure.

The shared handler also retained its EXIT trap while handling INT or TERM, permitting cleanup re-entry when the handler called `exit`.

## Proven predecessor failures

### Host failure overwritten by guest result

A captured timeout 124 or host failure 42 could become generic guest failure 1. The final code then pointed investigation toward the guest despite an earlier host-owned failure.

### Explicit signal identity lost

The shared handler derived its result from `$?` and the guest file. Parent-only INT or TERM could therefore return 0 or 1 instead of 130 or 143.

### EXIT cleanup re-entry

Calling `exit` from the signal-invoked cleanup could trigger the still-installed EXIT trap. The canonical negative control recorded cleanup as `rm, rmdir, rm`.

### Later signal replaced the first

Patch 1 initially restored default INT and TERM behavior before cleanup. TERM could start cleanup, then INT could terminate the shell by signal 2 after only the first cleanup action. The temporary directory remained.

### First signal during ordinary cleanup disappeared

Patch 2 ignored INT and TERM at ordinary EXIT cleanup entry before any signal result had been selected. Successful work followed by TERM during cleanup could complete cleanup and return 0.

### Later cleanup signal replaced completed guest failure

Patch 3 initially promoted the cleanup-time signal ahead of the guest result. A guest failure already written and completed before host cleanup plus later TERM returned 143. Event order required 1.

## Selected ownership and event order

The final order is:

```text
captured host failure
> completed guest or protocol failure
> first cleanup-time signal
> first cleanup failure
> success
```

The ordering follows when each result becomes authoritative:

1. the host command status is captured before ordinary EXIT cleanup;
2. the guest worker writes its result, unmounts the shared location, and powers off before `debvm-run` returns;
3. a signal recorded by the ordinary EXIT handler arrives during host cleanup;
4. cleanup status becomes final as cleanup actions run.

A cleanup-time signal still reports cancellation after successful work. It cannot replace a host or guest failure that had already completed.

## Patch mechanics

### Patch 1 — preserve the primary result

Patch 1 introduces `finish()`, `cleanup_exit()`, and `cleanup_signal()`.

`finish()` receives the already-captured host or explicit signal status, reads the guest result safely, retains the first cleanup failure, attempts all cleanup actions, and selects host before guest before cleanup.

The two handlers separate ordinary EXIT from explicit INT and TERM. EXIT is cleared before `finish()` so cleanup runs once.

### Patch 2 — retain the first handled signal

Patch 2 changes handler trap transitions from restoring default INT/TERM behavior to ignoring those signals during bounded cleanup:

```sh
trap '' INT TERM
trap - EXIT
```

The order closes the window where a later signal could terminate cleanup before EXIT was cleared.

### Patch 3 — retain the first signal during ordinary cleanup

Ordinary EXIT cleanup has no signal status yet. Patch 3 adds one initialized slot and a first-writer recorder:

```sh
cleanup_signal_status=0

record_cleanup_signal() {
  if [ "$cleanup_signal_status" -eq 0 ]; then
    cleanup_signal_status=$1
  fi
}
```

`cleanup_exit()` installs recording traps for INT and TERM. `finish()` switches them to ignored after cleanup and before final result selection. Explicit signal cleanup keeps ignoring later signals because its status has already been supplied directly.

### Patch 4 — preserve completed guest failure

Patch 4 changes only final result selection. It moves the recorded cleanup-time signal below the completed guest result:

```text
host, guest, cleanup-time signal, cleanup
```

Signal capture, first-writer behavior, cleanup actions, and trap transitions stay unchanged.

## Rejected alternatives

### Last failure wins

The original behavior allowed whichever outcome cleanup inspected last to replace earlier results. This loses ownership and event order.

### Signal always wins

This reports cancellation correctly after success, yet it replaces a completed guest failure with a later cleanup event. PR #304 retained the `signal > guest` policy as the losing comparison.

### Ignore all signals during cleanup

This stabilizes explicit signal handling, yet ordinary EXIT cleanup can begin without any selected signal result. Ignoring the first signal there produces false success.

### Restore default signal handling during cleanup

A second signal can terminate the shell, replace the first signal identity, and interrupt cleanup. Bounded cleanup uses ignored later signals after the first result is retained.

### One squashed patch

The four-patch series preserves a useful review trail. Each patch has a specific negative control and each intermediate policy explains why the next patch exists.

## Fixture ownership lesson

PR #290 exposed two test-harness defects:

- generated candidate shells omitted `cleanup_signal_status=0` and `record_cleanup_signal()`;
- substring extraction could confuse `cleanup_signal()` with `record_cleanup_signal()`.

The canonical #282 head adopted exact line-boundary function extraction and conditional recorder composition. #290 remains historical fixture evidence and contributes no product patch to the final series.

## Extraction performed on 2026-08-01

The exact imported source and four canonical patch blobs were reconstructed in a disposable local Git repository. The worker ran `git apply --check`, then `git apply`, for every patch in order. All eight operations returned zero. The final script passed `/bin/sh -n`.

Exact receipt:

- imported source Git blob: `426aeeb854173569b24e64d6eb85019f45bdf0b6`;
- imported source SHA-256: `da89b51df80786f4e379b2ba5b033aab6c4e1d7acc8ba17cf57e67159a32e300`;
- imported source size: 2,029 bytes;
- composed source SHA-256: `8d2b0fdef2c93fcd3d97f296dfe58d3cbe198e8a02ac85930aa8c3c89aedb90f`;
- composed source size: 2,924 bytes;
- shell syntax result: success.

## Current upstream compatibility analysis

The canonical contribution destination is the mmdebstrap Salsa repository on `master`. Debian Sources currently publishes version `1.5.7-3`, and its directory listing shows `run_qemu.sh` at 2,029 bytes. The tag page identifies `debian/1.5.7-3` with abbreviated commit `6fde9997`.

Equal file size suggests the imported base may still match the published package. A byte comparison and full live commit identity remain required. GitLab raw/API retrieval and direct cloning were unavailable from this execution environment, so this packet deliberately stops before claiming a clean application to current Salsa `master`.

## Reopen triggers

Revisit the selected policy when any of these become true:

- the guest result remains provisional when host cleanup begins;
- guest publication can fail after `debvm-run` returns;
- cleanup becomes long-running or unbounded and requires escalation;
- upstream adopts process-group signal delivery or a different child ownership model;
- current upstream already contains an equivalent or stronger correction.
