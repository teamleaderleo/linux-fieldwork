# Delayed signal handlers must retain cancellation intent

## In simple words

Some programs cannot exit immediately when they receive a signal because they first need to reap a child, close pipes, unmount filesystems, or finish another cleanup step.

Logging the signal is not enough. The handler must retain the cancellation request in state that the normal control flow checks after cleanup. Otherwise the program can acknowledge `SIGINT`, `SIGHUP`, or `SIGTERM`, finish its child successfully, and then return success as though cancellation never happened.

## What I learned

A delayed signal handler has two responsibilities:

1. record the signal or cancellation state without doing unsafe work in the handler;
2. ensure the owner checks that state after the protected child or cleanup section settles and before reporting success.

When several signals arrive, retaining the **first** signal gives a stable account of the cancellation that started the shutdown sequence. Later signals may still be logged, but they should not silently replace the original reason.

The regression must signal only the owning parent PID as well as the whole process group. Process-group termination can hide an owner-state defect because the child dies too and makes the overall operation fail for a different reason.

A useful cancellation test checks more than exit status:

- the signal was logged;
- the parent did not write or return a success marker;
- the final status was nonzero or reflected the recorded signal contract;
- descendants were reaped;
- the process group became empty;
- locks, sockets, mounts, descriptors, and temporary paths were released where relevant;
- and an immediate unsignaled rerun still succeeded.

## Source and provenance

- Project: imported Debian `mmdebstrap`
- Source file and function: `upstream/mmdebstrap/mmdebstrap`, `run_progress()`
- Investigation: LF-23 cancellation and subprocess cleanup
- Filed defect: issue #30
- Candidate repair: pull request #24

## Example

Problematic pattern:

```perl
my $got_signal = 0;
my $handler = sub {
    info "received signal $_[0]; waiting for child";
};

# ... wait for the child ...

if ($got_signal) {
    error "received signal: $got_signal";
}
```

The later check is unreachable because the handler never changes `$got_signal`.

A bounded repair records the first signal:

```perl
$got_signal = $_[0] if !$got_signal;
```

The normal post-child path can then finish cleanup and fail instead of reporting success.

## Validation

The LF-23 repair probe includes a negative control against the unmodified source and a repaired matrix for owner-only `SIGINT`, `SIGHUP`, `SIGPIPE`, and `SIGTERM`. It also sends `SIGTERM` followed by `SIGHUP` and requires the final error to retain `TERM` as the first signal.

Every case checks the final process group and an immediate unsignaled rerun.

## Environment and assumptions

- Linux process and signal semantics.
- Perl signal handlers in the imported `mmdebstrap` source.
- A child process that remains alive long enough to distinguish parent-only delivery from process-group delivery.
- The current dedicated regression runs in a privileged Debian sid container.

## Limits

This lesson does not choose a universal external contract between returning a nonzero status and re-raising the original signal. That is a separate CLI compatibility decision. It also does not prove behavior on non-Linux systems, under every shell supervisor, or during every possible cleanup phase.

## Related work

- Related issue: #30
- Related pull requests: #16 and #24
- Related lane: LF-23 cancellation and subprocess cleanup
- Source: `upstream/mmdebstrap/mmdebstrap`
