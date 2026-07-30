# mmdebstrap local mirror HTTP server readiness

## In simple words

The package-test entrypoint starts its local mirror HTTP server in the background, throws away its startup error output, and immediately begins mirror construction. It never proves that the child stayed alive or bound port 80.

A bind failure or startup race is therefore reported later as a generic mirror failure instead of naming the HTTP server as the owning operation.

## Canonical records

- Focused issue: #79
- Imported source: `upstream/mmdebstrap/debian/tests/testsuite`
- Candidate patch: `0001-verify-local-http-server.patch`
- Regression: `tests/test_mmdebstrap_http_server_readiness.py`
- Reusable note: `notes/debian/package-tests-must-gate-background-services-on-readiness.md`

## Baseline source boundary

The current entrypoint uses:

```sh
python3 -m http.server --directory="$AUTOPKGTEST_TMP/shared/cache" --bind 127.0.0.1 80 2>/dev/null &
HTTPD_PID=$!
trap "kill $HTTPD_PID" INT QUIT TERM EXIT
```

This loses the bind diagnostic, does not distinguish process creation from readiness, and does not wait for the child during cleanup.

## Candidate behavior

The retained patch adds three small shell helpers:

- `probe_http_server`: bounded local socket connection;
- `wait_for_http_server`: checks child liveness and requires two successful probes before continuing;
- `stop_http_server`: tolerates an already-dead child, signals a live child, and waits to reap it.

The server's stderr is retained in `$AUTOPKGTEST_TMP/http.server.log`. Startup exits with autopkgtest-neutral status `77` when the child exits or the readiness bound expires, before `make_mirror.sh` begins. Signal traps convert INT, QUIT, and TERM into exit statuses whose EXIT trap performs cleanup.

## Regression matrix

The executable regression applies the patch to an exact temporary source copy and requires:

1. candidate shell syntax is valid;
2. delayed startup becomes ready and is reaped;
3. immediate exit is classified before dependent work and its stderr is surfaced;
4. an occupied port surfaces `Address already in use` rather than connecting to the unrelated listener;
5. a live non-listening process reaches an explicit readiness timeout;
6. cleanup works for live and already-exited children;
7. no tested process survives cleanup.

The unmodified source is the negative control: it retains `2>/dev/null`, the blind `kill` trap, and no readiness helper.

## Evidence boundary

Static source reading proves the missing lifecycle checks. This candidate does not claim that historical Debian CI run `72574145` failed here; that run's actual owner is separately resolved in issue #84 and PR #86.

The synthetic regression validates the lifecycle mechanism without requiring root, port 80, package mutation, mirror downloads, mounts, or a multi-hour autopkgtest.

## Cleanup and safety

All dynamic cases use loopback ephemeral ports and temporary files. Each spawned process is stopped and waited for. No listener, process, mount, package state, or persistent root filesystem is retained.

## Disposition

Keep this as an independent package-test reliability candidate. No Debian or external upstream contact is included or authorized.
