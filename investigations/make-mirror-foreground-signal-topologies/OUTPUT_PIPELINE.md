# Output-capturing pipeline ownership discriminator

Date: 2026-07-31

Tracking: issue #263 and PR #264.

## TL;DR

The output-capturing command substitution in `update_cache()` does not make explicit cancellation ownership impossible.

A final-stage PID alone is insufficient: killing it leaves upstream stages alive and the shell job can remain blocked. A complete pipeline launched in an isolated session can instead be stopped as one owned group. A private capture file plus assignment only after status 0 preserves the target shell's output and final-stage-status rules, rejects partial output on failure or cancellation, and reruns cleanly.

This keeps the composed parent-worker plus worker-child direction technically viable. It also proves that the source needs a distinct output-capture primitive rather than one universal child helper.

## Explain like I'm five

The worker asks three tools to make a package list. Remembering only the last tool is not enough because the first two can keep running.

The viable model gives all three tools their own labelled room. The worker remembers the room number. On success, it reads the completed list. On failure or stop, it closes the whole room and throws away the unfinished list.

## Why care

The package list controls later APT installation. A cancellation repair must not accept half a list, change which pipeline error counts, or change shell command substitution's trailing-newline behavior.

## Exact source boundary

`update_cache()` computes the package list with a three-stage command-substitution pipeline:

```sh
pkgs=$(APT_CONFIG=... apt-get indextargets \
  | xargs ... \
  | grep-dctrl ...)
```

A simple asynchronous command helper cannot update `pkgs` in the worker shell. The source needs a separate capture-and-publish operation.

## Executable records

- negative and positive ownership topology:
  `tests/test_make_mirror_output_capture_pipeline_ownership.py`;
- complete output, status, cancellation, cleanup, and rerun contract:
  `tests/test_make_mirror_output_capture_pipeline_contract.py`.

Local commands:

```text
python3 tests/test_make_mirror_output_capture_pipeline_ownership.py -v
python3 tests/test_make_mirror_output_capture_pipeline_contract.py -v
```

The new contract matrix passed 4/4 locally. Hosted exact-head execution remains required.

## Naive final-PID ownership: rejected

The negative control starts three held stages in a background pipeline and stores `$!`, which identifies the final stage.

On worker-only TERM the handler kills the stored PID and waits.

Observed:

- the final stage exits;
- producer and middle remain alive;
- the worker remains blocked until the test explicitly terminates those upstream stages;
- cleanup and status 143 complete only afterward.

Conclusion: final-stage PID ownership does not provide prompt cancellation or complete pipeline ownership.

## Internally isolated pipeline group: viable model

The positive model runs the complete pipeline under:

```sh
setsid /bin/sh pipeline.sh >capture &
PIPEPID=$!
```

The worker signals `-$PIPEPID` through external `/bin/kill`, waits for the session leader, and removes the private capture.

Observed under worker-only TERM:

- producer, middle, and final all terminate;
- worker exits 143 promptly;
- partial capture is removed;
- no result is published;
- an immediate clean rerun returns the expected value;
- no capture residue survives.

## Output compatibility

The original command-substitution form and grouped-capture candidate produce identical variable bytes for:

- empty output;
- output without a trailing newline;
- one trailing newline;
- an internal newline without a trailing newline;
- several trailing newlines;
- output containing only newlines.

The candidate writes raw stdout to the private capture, waits for status 0, then performs:

```sh
CAPTURED=$(cat "$capture")
```

The short local `cat` occurs only after the long owned pipeline has completed. It preserves command substitution's removal of all trailing newlines while retaining internal newlines.

## Status compatibility

### Final-stage failure

The final stage writes `partial` and exits 7.

Observed:

- original assignment status: 7;
- candidate status: 7;
- candidate publishes no result;
- private capture is removed.

Partial package output therefore cannot become accepted state after an authoritative final-stage failure.

### Upstream failure with final success

The producer prints `packages` and exits 9; the later stages succeed.

Observed in both original and candidate forms:

- status 0;
- value `packages`.

The target `/bin/sh` uses the final pipeline stage's status. A cancellation repair must preserve this masking behavior unless a separate policy change deliberately introduces pipefail-like semantics.

## Design consequence

The command-substitution boundary no longer makes the source-level ownership direction lose.

The minimum source design still needs three separate primitives:

1. parent ownership of each `update_cache` pipeline worker;
2. worker ownership of simple foreground commands;
3. worker ownership of output-capturing pipelines.

The output-capture primitive additionally needs:

- a private capture path below an already-owned runtime;
- an isolated process group or equivalent all-stage supervisor;
- first-signal retention across launch and PID registration;
- explicit wait and status preservation;
- publication only after status 0;
- cleanup precedence and immediate rerun.

## Compatibility boundary

The executed group model depends on Linux/GNU `setsid` and an external `kill` accepting a negative process-group ID. The repository does not yet prove those dependencies across every supported mirror host.

A dedicated all-stage supervisor remains an alternative. It would make stage ownership explicit without shell job assumptions, at the cost of a helper-language and API boundary.

## Evidence boundary

The matrices use real `/bin/sh`, pipelines, sessions, signals, waits, files, and processes. They do not run APT, parse real index targets, execute the complete mirror loop, exercise INT/QUIT or competing signals, close launch-registration windows, test cleanup-failure precedence, or prove the complete two-level owner chain.

## Next discriminator

Prototype the fallback install chain under the same active-child contract:

```text
first attempt fails ordinarily -> fallback runs
first attempt succeeds -> fallback omitted
first attempt is cancelled -> fallback must not run
second attempt status -> authoritative
cleanup failure -> secondary to ordinary failure or signal
immediate rerun -> clean
```

Then combine parent-worker ownership, simple-child ownership, and output-capture ownership in one reduced source-shaped model before selecting a retained patch.

## Authority

Internal Linux Fieldwork research only. No external contact is included or authorized.
