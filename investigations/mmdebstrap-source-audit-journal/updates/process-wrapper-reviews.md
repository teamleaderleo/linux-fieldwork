# Process-wrapper peer reviews — 2026-07-30

This journal update records reviews of two active mmdebstrap wrapper candidates. The focused PR reviews remain the canonical discussion threads.

## `gpgvnoexpkeysig` verifier-status candidate — PR #138

The baseline finding is valid: the imported POSIX-shell pipeline reports the final filter command's status, so verifier failure can become wrapper success.

The FIFO candidate at reviewed head `f226bd7a451ab8a9ae8084f0155e371ac1ddbf61` was held for revision because its process topology introduced two unproven status/lifecycle assumptions.

### Early filter failure can feed back into the verifier

The status filter is the FIFO's only reader. If it exits before draining the stream, a verifier writing enough status data can receive a broken pipe. The wrapper then sees an induced verifier failure and can lose the original filter status that should have won when the verifier itself was otherwise successful.

A local control used a fake filter that exited 7 immediately and a fake verifier that emitted more than a pipe buffer. The writer failed after the reader disappeared, and the wrapper did not return 7.

Required controls:

- verifier 0 plus early filter 7 returns 7;
- verifier 2 plus early filter 7 returns 2;
- status data exceeds pipe buffering;
- the verifier's original outcome cannot be changed merely because the output filter failed.

### Wrapper-only signals do not prove child cleanup

The shell runs the verifier in the foreground and records only the filter PID. Sending `TERM` to the wrapper PID can leave the shell waiting for the verifier and delay its trap. A sleeping fake verifier remained alive together with the wrapper beyond the bounded review interval.

Required controls:

- signal only the wrapper PID for HUP, INT, and TERM;
- require the documented wrapper outcome;
- require verifier and filter termination and reap;
- require the FIFO directory empty;
- exercise a real non-default status fd such as `--status-fd 3` and verify stdout, stderr, and status streams remain separate.

Review thread: PR #138, review `4819268276`.

## `proxysolver` child-status candidate — PR #134

The positive nonzero exit-code direction is valid. Waiting for the completed solver and exiting with status 7 prevents partial solver output plus child exit 7 from becoming wrapper success, while stdout and dump bytes remain unchanged.

The reviewed head `f453c2d48f2e7b26e9ccca58b45d7958a34462fa` was held for a narrower signal contract and lifecycle evidence.

### Negative Python return codes are not process exit statuses

`subprocess` represents signal termination as a negative return code. Raising `SystemExit(-15)` does not make the wrapper terminate by `SIGTERM`; it exits with shell-visible status 241.

A fake solver that terminated itself with `SIGTERM` reproduced this distinction.

The candidate must choose and document one policy:

- restore the default handler and re-raise the same signal; or
- map to `128 + signal` and state that convention.

### Wrapper termination needs a child-ownership test

The existing normal-completion tests do not prove that no child survives when the wrapper itself receives a signal. A long-running fake solver should record its PID; the test should signal only the wrapper PID and require the solver to terminate and be reaped within a bounded interval.

The regression should also assert solver stderr passthrough explicitly.

Review thread: PR #134, review `4819288597`.

## Reusable lessons

1. **Pipeline output ownership and status ownership are separate.** A filter can transform bytes without owning the producer's success status.
2. **A filter failure must not rewrite the producer's result through broken-pipe feedback.** Keep draining or decouple the streams.
3. **Shell exit codes, signal termination, and Python negative return codes are different contracts.** Choose one explicitly.
4. **Normal completion does not prove signal cleanup.** Signal the wrapper PID and observe every child.
5. **Dynamic file descriptors need dynamic tests.** A default-stdout test does not validate `eval`-constructed fd redirection.
6. **No-child-survives claims require PID evidence and bounded reap checks.** Cleanup of a temporary directory alone is insufficient.
7. **Preserve byte streams and process outcomes independently.** Compare stdout/dump bytes while separately asserting status and lifecycle.

No Debian or external upstream contact was made or authorized by these reviews.
