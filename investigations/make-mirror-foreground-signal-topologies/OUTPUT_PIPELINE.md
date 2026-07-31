# Output-capturing pipeline ownership discriminator

## Why this boundary matters

`update_cache()` computes the package list with a command substitution whose body is a three-stage pipeline:

```sh
pkgs=$(APT_CONFIG=... apt-get indextargets \
  | xargs ... \
  | grep-dctrl ...)
```

A prompt-cancellation repair cannot replace this with a simple asynchronous command helper. The worker must retain output, preserve command-substitution semantics, preserve the target shell's pipeline status rule, and stop every pipeline stage on cancellation.

## Naive final-PID ownership: rejected

The negative control starts three held stages in a background pipeline and stores `$!`, which identifies the final stage.

On worker-only TERM the signal handler:

1. kills the stored final PID;
2. calls `wait "$PIPEPID"`;
3. intends to remove the capture and exit 143.

Observed:

- the final stage exits;
- producer and middle stages remain alive;
- the worker remains blocked in `wait "$PIPEPID"` because the shell waits for the background pipeline job, not only the final process;
- cleanup and status 143 complete only after the test explicitly terminates the two upstream stages.

Conclusion: final-stage PID ownership is not enough for prompt cancellation or complete pipeline ownership. This eliminates a simple shell-only `capture_pipeline` helper built only around `$!`.

## Internally isolated pipeline group: viable model

The positive control runs the complete pipeline under:

```sh
setsid /bin/sh -c 'producer | middle | final > capture' &
PIPEPID=$!
```

The signal path uses an external group-aware `kill` against `-$PIPEPID`, waits for the group leader, removes the capture, and exits 143.

Observed:

- producer, middle, and final stages all terminate;
- worker exits 143 promptly;
- partial capture is removed;
- no stage survives.

This proves one viable ownership model on the current Linux runner. It adds exact dependencies and compatibility questions:

- `setsid` availability and behavior;
- an external `kill` implementation that accepts a negative process-group ID;
- safe group isolation;
- group-leader status and wait semantics;
- first-signal retention and launch/PID-registration closure.

## Ordinary output and status semantics

Three additional controls compare ordinary command substitution with an isolated grouped capture.

### Trailing newlines

Input pipeline output:

```text
alpha
beta


```

Both ordinary command substitution and grouped capture followed by `value=$(cat capture)` produce exact value bytes:

```text
alpha
beta
```

The grouped form therefore preserves command-substitution trailing-newline stripping in the executed model.

### Final-stage failure and partial output

A pipeline whose final stage copies partial output and exits 7 yields grouped wait status 7. The wrapper removes the capture and does not assign a value.

This provides an explicit rule that partial output from a failing pipeline cannot become an accepted package list.

### Upstream failure with final success

A pipeline whose first stage exits 9 while the final stage exits 0 produces status 0 in both the ordinary and grouped forms under the target shell. Both values are empty.

This preserves the source's current last-stage pipeline-status rule. Whether that rule itself should change is outside this cancellation investigation.

## Comparative consequence

The source-level ownership choices are now narrower:

1. **Final PID only:** rejected by executed leak/blocking control.
2. **Internal isolated group:** model-executed and semantically promising, but adds Linux utility and group-policy dependencies.
3. **Dedicated all-stage supervisor:** not yet executed; could make ownership explicit without shell job assumptions, at the cost of a helper-language/API boundary.
4. **Accept eventual cancellation:** retains the simpler merged/focused repairs and avoids a large mechanism for a bounded latency issue.

The next comparison should determine whether internal group dependencies are already guaranteed in the `make_mirror.sh` host environment and whether a bounded helper can cover direct commands, fallback attempts, and output capture without obscuring result precedence.

External contact authorized: `false`.
