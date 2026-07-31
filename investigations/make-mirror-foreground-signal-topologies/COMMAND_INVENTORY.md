# `update_cache()` cancellation command inventory

This inventory classifies imported `make_mirror.sh` blob `6c4be092edcf23b56b63a3befe238c099c45f590` for prompt-cancellation ownership work.

## TL;DR

The source grammar cannot be covered by one generic asynchronous helper without changing behavior. A complete prompt-cancellation implementation needs separate ownership for parent pipeline workers, simple commands and fallback attempts, and output-capturing pipelines.

All three shapes are technically modelled. The canonical investigation stops without a source patch because the remaining delay has not been measured as harmful and the complete mechanism adds substantial process-group, dependency, and launch-window complexity.

## Parent call shapes

The top-level owner invokes the worker in two synchronous pipeline forms.

### One-line producer

```sh
echo "deb [arch=$nativearch] $mirror $dist $components" \
  | update_cache "$dist" "$nativearch"
```

Properties:

- producer output is small and immediate;
- pipeline status is the final `update_cache` command's status under the target shell;
- the top-level owner stores no worker PID;
- a parent-only signal can be deferred until the worker returns.

### Heredoc producer

```sh
cat <<END | update_cache "$dist" "$nativearch"
...
END
```

Properties:

- the shell creates a separate pipeline producer;
- a source repair that backgrounds the pipeline and stores `$!` must prove that `$!` identifies the final worker;
- worker cancellation must not leave a blocked or surviving producer;
- ordinary input bytes and final status must remain unchanged.

Executed controls show that on the target shell `$!` equals the final worker PID for both shapes, complete input reaches the worker, and explicit wait preserves worker status 7.

## Worker command shapes

### Local shell and filesystem operations

Examples:

- `mkdir`, `cat` to local files, redirections, `rm`, `rmdir`;
- loops over source and preference files;
- diagnostic `echo` and `cat`.

These are short or local. Converting every operation to asynchronous ownership would add more lifecycle state than the observed latency justifies.

### Source-filter pipelines with ignored no-match status

Examples:

```sh
grep -v ... | grep -E ... >>file || :
```

The terminal `|| :` deliberately discards no-match failure. A generic child wrapper must not turn this into a primary failure or change redirection behavior.

### Simple foreground APT commands

Examples:

```sh
APT_CONFIG=... apt-get update --error-on=any
APT_CONFIG=... apt-get --option ... update
APT_CONFIG=... apt-get clean
```

Worker-local group ownership is technically viable:

1. launch in an isolated group;
2. retain the group leader PID;
3. wait explicitly without changing caller errexit state;
4. preserve child status;
5. clear ownership;
6. stop and wait the group during signal cleanup.

A launch/PID-registration first-signal interval would still need closure.

### Fallback command chain

```sh
APT_CONFIG=... apt-get --yes install $pkgs \
  || APT_CONFIG=... apt-get --yes install ... $pkgs
```

The seven-case matrix in `FALLBACK_CHAIN.md` proves:

- fallback runs only after ordinary first-attempt failure;
- fallback never runs after cancellation;
- the second result is authoritative when fallback runs;
- ordinary failure and signal beat cleanup failure;
- cleanup failure is authoritative after otherwise successful work;
- immediate rerun is clean;
- a helper must not toggle `set -e` around wait.

### Output-capturing command-substitution pipeline

```sh
pkgs=$(APT_CONFIG=... apt-get indextargets \
  | xargs ... \
  | grep-dctrl ...)
```

Final-stage PID ownership alone is rejected: upstream stages survive and the shell job remains blocked.

`OUTPUT_PIPELINE.md` proves one viable model using an isolated complete pipeline group plus a private capture file. It preserves:

- exact command-substitution output and trailing-newline behavior;
- final-stage pipeline status;
- the existing masking of upstream failure when the final stage succeeds;
- rejection of partial output after failure;
- worker-only TERM status 143;
- complete stage cleanup and immediate rerun.

## Minimum source primitives implied by the inventory

A source-level prompt-cancellation direction needs at least:

1. **parent pipeline-worker ownership** for both `echo` and heredoc call shapes;
2. **worker simple-child ownership** for direct APT commands and fallback attempts;
3. **worker output-capturing pipeline ownership** for `pkgs=$(...)`;
4. first-signal retention and PID-registration closure at parent and worker levels;
5. one result and cleanup precedence contract across all primitives.

## Comparative consequence

- Caller-owned group delivery is prompt only when an external caller guarantees a safe isolated group. The repository does not provide that contract.
- Worker-child ownership alone loses because parent-only delivery remains deferred.
- Final-stage pipeline PID ownership loses because upstream stages survive.
- Internal isolated groups make the complete direction technically viable, but add `setsid`, group-aware external `kill`, multiple ownership helpers, capture publication, and repeated launch windows.
- A dedicated all-stage supervisor would enlarge packaging and API surfaces further.

## Stop decision

The accepted top-level and worker repairs already provide eventual status correctness and correct cleanup ownership. The remaining promptness question has no measured real-workload impact.

Disposition: retain the executed negative and comparative evidence and `HOLD` broader source expansion.

Reopen when measured harmful latency, an explicit isolated-supervisor contract, accepted process-group dependencies, or contradictory lifecycle evidence changes the cost-benefit decision.

External contact authorized: `false`.
