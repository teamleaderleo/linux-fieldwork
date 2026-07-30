# Package tests must gate background services on readiness

## Principle

Starting a process in the background proves only that the shell created a child. It does not prove that the child stayed alive, bound its socket, opened its files, or became usable.

A package test that depends on a background service should separate four states:

1. the process was launched;
2. the process is still alive;
3. the required endpoint is ready;
4. the process is stopped and reaped during every exit path.

## Startup contract

Retain the service's stderr instead of redirecting it to `/dev/null`. After launch, poll a bounded readiness condition while checking the child PID on every iteration.

For a local HTTP service, transport reachability can be enough when the document root is intentionally absent or replaced during setup. Use at least two successful probes separated by a short delay when another process could already own the port; this reduces the chance of mistaking an unrelated listener for the new child.

Classify these separately:

- child exited before readiness;
- readiness deadline expired while the child remained alive;
- bind or configuration failure reported by retained stderr;
- later workload failure after readiness was established.

## Cleanup contract

Cleanup should:

- tolerate a process that already exited;
- signal a live child;
- wait for the child so it is reaped;
- run from the shell's exit trap;
- preserve signal-derived exit behavior rather than swallowing termination.

A blind `kill "$pid"` trap can create a secondary error, skip reaping, or obscure the original startup failure.

## Regression shape

Use synthetic local processes rather than the full package test to assert:

- delayed startup becomes ready within the bound;
- immediate exit is diagnosed before dependent work begins;
- an occupied port retains the bind error;
- a live but non-listening process times out explicitly;
- cleanup works for both live and already-exited children;
- no process or listener survives the test.

## mmdebstrap example

The mmdebstrap autopkgtest launches `python3 -m http.server` for its local mirror, discards stderr, and immediately starts mirror construction. A bounded readiness gate makes HTTP-server startup the owning operation instead of collapsing it into a later generic `make_mirror.sh failed` result.
