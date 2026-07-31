# Output-capturing pipeline ownership result

Date: 2026-07-31

Tracking: issue #263 and PR #264.

## TL;DR

The `pkgs=$(apt-get indextargets | xargs | grep-dctrl)` boundary does not make explicit cancellation ownership impossible.

A reduced real-`/bin/sh` candidate launches the complete output-producing pipeline in a new session, stores the session leader PID, waits explicitly, writes stdout to a private capture file, and assigns the shell variable only after status 0. It preserves command-substitution output semantics, preserves the target shell's final-stage pipeline status rule, discards partial output on failure or TERM, stops every held pipeline stage, and reruns cleanly.

This keeps composed parent-worker plus worker-child ownership technically viable. It also confirms that the source design requires a distinct output-capture primitive rather than one universal child helper.

## Explain like I'm five

The worker asks three tools to make a package list. The old shell waits for the tools and collects their answer, but it cannot reliably stop all three tools when only the worker receives a stop signal.

The experiment gives the three tools their own clearly labelled room. The worker remembers that room's number. On success, it reads the completed answer. On failure or stop, it closes the whole room and throws away the unfinished answer.

## Why care

The package list controls later APT installation. A cancellation repair must not accept half a list, change which pipeline error counts, or subtly change how trailing newlines are removed by shell command substitution.

This result removes one major uncertainty from the source-level ownership direction while exposing its real compatibility cost.

## Exact model

Regression:

`tests/test_make_mirror_output_capture_pipeline_contract.py`

The candidate worker:

1. creates a private capture path;
2. launches `setsid /bin/sh pipeline.sh >capture &`;
3. stores the session leader PID;
4. waits explicitly;
5. on TERM, signals the negative process-group ID, waits, removes capture, and exits 143;
6. on ordinary nonzero status, removes capture and preserves that status;
7. on status 0, performs `CAPTURED=$(cat "$capture")`, removes capture, and publishes the resulting variable bytes.

The final local `cat` is deliberately outside the long-running pipeline. It exists only to reproduce command-substitution trailing-newline removal after the owned operation has completed.

## Executed controls

Local command:

```text
python3 tests/test_make_mirror_output_capture_pipeline_contract.py -v
```

Result: 4/4 tests passed.

### Exact output and trailing newlines

The original command-substitution form and candidate capture form produce identical variable bytes for:

- empty output;
- output without a trailing newline;
- one trailing newline;
- an internal newline without a trailing newline;
- several trailing newlines;
- output containing only newlines.

This demonstrates the shell rule that all trailing newlines are removed while internal newlines remain.

### Upstream failure with final success

The producer prints a package name and exits 9, while later stages succeed.

Observed in both original and candidate forms:

- status 0;
- captured value `packages`.

Interpretation: the target `/bin/sh` uses the final pipeline stage's status. A repair must preserve this masking behavior unless a separate policy change deliberately introduces pipefail-like semantics.

### Final-stage failure

The final stage writes `partial` and exits 7.

Observed:

- original command-substitution assignment returns 7 and contains partial output in the dying shell;
- candidate returns 7;
- candidate publishes no result file;
- private capture is removed.

Interpretation: later source logic cannot consume partial package output after an authoritative final-stage failure.

### Worker-only TERM

Three pipeline stages each pass one line, record their PID, and then remain held.

TERM is sent only to the worker.

Observed:

- worker exits 143 promptly;
- all three stage PIDs disappear;
- partial capture is removed;
- no result is published;
- an immediate clean rerun returns `clean`;
- no capture residue survives.

## Design consequence

The command-substitution boundary no longer makes option C lose.

The minimum source design still requires separate primitives:

1. parent ownership of each `update_cache` pipeline worker;
2. worker ownership of simple foreground commands;
3. worker ownership of output-capturing pipelines.

The output-capture primitive additionally requires:

- a private capture path below an already-owned runtime;
- an isolated process group or equivalent complete pipeline ownership;
- first-signal retention across launch and PID registration;
- explicit wait and status preservation;
- publication only after status 0;
- cleanup precedence and immediate rerun.

## Compatibility boundary

The prototype depends on Linux/GNU `setsid` and negative-process-group signaling. It does not establish that those tools are available in every supported mirror environment.

It preserves the target shell's final-stage status rule. It does not add pipefail semantics or identify failures in earlier pipeline stages when the final stage succeeds.

## Evidence boundary

The matrix uses real `/bin/sh`, pipelines, sessions, signals, waits, files, and processes. It does not run APT, parse real index targets, run the complete mirror loop, exercise INT/QUIT or competing signals, close launch-registration windows, test cleanup failure precedence, or prove parent-only delivery through the full two-level ownership chain.

## Next discriminator

Prototype the fallback install chain under the same active-child ownership contract:

```text
first attempt fails ordinarily -> fallback runs
first attempt succeeds -> fallback omitted
first attempt is cancelled -> fallback must not run
second attempt status -> authoritative
cleanup failure -> secondary to ordinary failure or signal
immediate rerun -> clean
```

Then combine the three primitives in one reduced source-shaped owner before selecting a retained patch.

## Authority

Internal Linux Fieldwork research only. No external contact is included or authorized.
