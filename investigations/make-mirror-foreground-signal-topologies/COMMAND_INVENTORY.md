# `update_cache()` cancellation command inventory

This inventory classifies the exact imported `make_mirror.sh` blob `6c4be092edcf23b56b63a3befe238c099c45f590` for prompt-cancellation ownership work. It is not an implementation plan by itself.

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

- producer output is still small, but the shell creates a separate pipeline producer;
- a source repair that backgrounds the pipeline and stores `$!` must prove that `$!` identifies the final worker on the target `/bin/sh`;
- worker cancellation must not leave a blocked or surviving producer;
- ordinary input bytes and final status must remain unchanged.

## Worker command shapes

### Local shell and filesystem operations

Examples:

- `mkdir`, `cat` to local files, redirections, `rm`, `rmdir`;
- loops over source and preference files;
- diagnostic `echo` and `cat`.

These are short or local. Converting every operation to asynchronous ownership would add more lifecycle state than the observed cancellation latency justifies.

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

These are the cleanest worker-child ownership candidates:

1. launch asynchronously;
2. retain the exact child PID;
3. wait explicitly;
4. preserve the child status;
5. clear ownership;
6. let worker signal handlers stop/wait the active child.

A launch/PID-registration first-signal interval must be closed just as for the proxy launches.

### Fallback command chain

```sh
APT_CONFIG=... apt-get --yes install $pkgs \
  || APT_CONFIG=... apt-get --yes install ... $pkgs
```

Each attempt can use a simple child-owner helper, but the chain must preserve:

- fallback only after the first ordinary nonzero result;
- cancellation must not start the fallback;
- the second result remains authoritative when the fallback runs;
- cleanup failure remains secondary.

### Output-capturing command-substitution pipeline

```sh
pkgs=$(APT_CONFIG=... apt-get indextargets \
  | xargs ... \
  | grep-dctrl ...)
```

This is the hardest worker boundary.

A simple asynchronous helper cannot update `pkgs` in the parent shell. A source repair needs a distinct output-capture primitive, likely a disposable file or controlled pipe, and must preserve:

- exact stdout bytes and trailing-newline command-substitution semantics;
- final pipeline status under the target shell;
- ownership of every pipeline process or a justified terminal-process/SIGPIPE rule;
- cancellation cleanup of the capture artifact;
- no partial output becoming an accepted package list;
- ordinary error and signal precedence.

Backgrounding a brace group is insufficient by itself: killing the group shell can reproduce the same deferred-foreground-child problem one level lower.

## Minimum source primitives implied by the inventory

One generic `run_child` helper cannot cover the exact grammar without semantic expansion. A source-level prompt-cancellation direction needs at least:

1. **parent pipeline-worker ownership** for both `echo` and heredoc call shapes;
2. **worker simple-child ownership** for direct APT commands and each fallback attempt;
3. **worker output-capturing pipeline ownership** for `pkgs=$(...)`.

Each primitive needs first-signal retention, PID registration, waiting, status preservation, and cleanup/rerun controls.

## Comparative consequence

- Option B, worker-child ownership alone, already loses as a complete solution because parent-only delivery remains deferred.
- A single-helper form of option C also loses: the command-substitution pipeline requires a separate capture and pipeline-ownership mechanism.
- A multi-primitive option C remains technically possible, but its scope is materially larger than the current two-layer status/cleanup repairs.
- Option A, isolated process-group delivery, remains the smallest mechanism only if actual caller/session authority proves the group is safe and intentional.

## Next discriminators

Before any retained source patch:

- prove `$!` is the final worker PID for both parent call shapes on the target shell;
- prove ordinary heredoc bytes and final worker status survive background/wait conversion;
- characterize producer survival when the final worker is cancelled;
- prototype the output-capturing pipeline and require exact output/status/cancellation controls;
- inventory actual caller/session topology for a supported isolated process-group contract.

No implementation direction is selected yet. External contact authorized: `false`.
