# runc sd-notify READY field ordering

## TL;DR

At exact-current upstream runc commit `7495faeac77318158e6d5faece1b0b0d53e6ced4`, `notifySocket.run()` splits an sd_notify datagram into newline-separated fields but tests `READY=` against the complete datagram (`got`) instead of the current field (`line`). The retained reduced probe already showed the consequence on the earlier source head: READY is recognized first and missed second.

The current source still contains the same predicate. This investigation is now executing a full-source Unix-datagram discriminator with three cases: READY first, READY second, and no READY. The candidate remains the one-line restoration from `got` to `line`.

Internal Fieldwork issue: #596.

## Explain like I'm five

A container can send several status facts to systemd in one message:

```text
STATUS=warming up
READY=1
```

runc reads those facts one line at a time. Current code asks whether the whole message begins with `READY=`. That makes the answer depend on which valid field came first.

```text
READY=1\nSTATUS=ok -> readiness found
STATUS=ok\nREADY=1 -> current code misses readiness
```

The candidate asks whether the current line begins with `READY=`.

## Why care

The runc sd_notify proxy sits between a container and the host service manager. A valid readiness notification can be ignored solely because another valid assignment appears first in the same datagram. The host can then keep waiting until another READY notification arrives or the watched process exits.

## Current state

- State: `EXECUTING`
- Exact current upstream head: `opencontainers/runc@7495faeac77318158e6d5faece1b0b0d53e6ced4`
- Upstream source owner: `notify_socket.go::notifySocket.run()`
- Internal Fieldwork issue: #596
- Fieldwork branch: `fieldwork/runc-sd-notify-ready-order`
- Distinguishing test carrier: `0001-test-ready-field-order.patch`
- Candidate carrier: `0002-fix-ready-field-order.patch`
- First incomplete step: hosted full-source baseline/candidate execution
- Cleanup state: test uses temporary Unix sockets and a short disposable `sleep` process
- Next safe action: execute the exact-source workflow and classify the first failure owner if any gate stops
- External-contact state: no upstream contact authorized or made

## Intent and precedent

The sd_notify proxy was introduced by [runc PR 1308](https://redirect.github.com/opencontainers/runc/pull/1308). Its original loop checked the current split field:

```go
for _, line := range bytes.Split(buf[0:r], []byte{'\n'}) {
    if bytes.HasPrefix(line, []byte("READY=")) {
        // forward readiness
    }
}
```

[runc PR 1807](https://redirect.github.com/opencontainers/runc/pull/1807) refactored create/start notification handling. The loop remained field-oriented, while the predicate changed to the complete datagram. That form remains on current main, now using `bytes.SplitSeq`.

systemd's sd_notify payload is a newline-separated list of variable assignments. `READY=1` and `STATUS=...` are both defined assignments; the payload contract does not require READY to be the first assignment.

## Question

Does current runc fail to proxy a valid sd_notify readiness datagram when `READY=...` follows another assignment, and does changing the predicate receiver from `got` to `line` restore field-order independence without accepting a datagram that has no READY assignment?

## Source

- Project: `opencontainers/runc`
- Original scout head: `0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`
- Refreshed exact current head: `7495faeac77318158e6d5faece1b0b0d53e6ced4`
- Relevant paths: `notify_socket.go`, `notify_socket_test.go`
- Current `go.mod`: Go 1.25.0
- Owned fork `teamleaderleo/runc` remains at the older scout head and is not being mutated for this gate

Current overlap search found no runc issue or pull request specifically carrying the READY-field ordering repair. Refresh again before any publication decision.

## Baseline behavior

The retained reduced parser probe established:

```text
ordering current first="READY=1" second=""
ordering intended first="READY=1" second="READY=1"
```

Current source refresh confirms the same expression remains:

```go
for line := range bytes.SplitSeq(got, []byte{'\n'}) {
    if bytes.HasPrefix(got, []byte("READY=")) {
        fileChan <- line
        return
    }
}
```

## Candidate

Minimal candidate:

```diff
- if bytes.HasPrefix(got, []byte("READY=")) {
+ if bytes.HasPrefix(line, []byte("READY=")) {
```

The candidate restores the historical field predicate. It does not alter the larger proxy policy: runc still forwards the READY assignment, sets MAINPID, performs the sd_notify barrier, and leaves interpretation of the READY value to the host service manager.

## Full-source discriminator

The test carrier adds `TestNotifySocketReadyOrder` as a new test file in the real runc `package main`.

It creates two local Unix datagram sockets:

- one acts as the container-side `NOTIFY_SOCKET` consumed by `notifySocket.run()`;
- one acts as the host notification socket consumed by `notifyHost()`.

A short `sleep` process supplies a real watched PID so the missing-READY path terminates cleanly after the process exits.

Cases:

1. `READY=1\nSTATUS=ok` -> expect `READY=1`, MAINPID, and barrier;
2. `STATUS=ok\nREADY=1` -> expect the same result;
3. `STATUS=ok` -> expect no host notification.

The workflow first runs cases 1 and 3 on baseline as controls. It then requires the complete baseline test to fail specifically in `ready-second`. The candidate must pass all three cases and the complete root package test.

## Reproduction

The hosted workflow:

```text
.github/workflows/runc-sd-notify-ready-order.yml
```

It performs:

```text
clone exact opencontainers/runc@7495fae...
create baseline and candidate worktrees
apply the test patch to both
apply the one-line source patch only to candidate
check patch whitespace and test gofmt
run baseline controls
require targeted baseline READY-second failure
run candidate focused test
run candidate root package test
retain logs and exact candidate diff
```

## Results

### Reduced parser level

Already demonstrated on the earlier exact source:

- READY first is recognized;
- READY second is missed;
- using `line` removes the order dependence.

### Current full-source level

Queued. The current-source workflow is the authoritative promotion gate.

## Interpretation

Source and history point to a narrow regression candidate. The loop variable exists to inspect assignments individually, the historical implementation checked that field, and the sd_notify payload contract is field-oriented.

The real-source test is important because it exercises the complete local path rather than only the parser expression: Unix datagram receive, READY extraction, host forwarding, MAINPID, barrier, watched-process lifetime, and the no-READY control.

## Evidence boundary

The reduced probe and source history make the mechanism high-confidence, but the current-runtime claim remains bounded until the hosted full-source test completes.

The current test does not require a systemd daemon or a container runtime. It uses the actual runc notification code with local Unix sockets and mocks the host side of the sd_notify protocol, including barrier acknowledgment.

Outside the current claim:

- real systemd service activation;
- container integration;
- sender credential filtering or PID identity policy;
- detached versus attached process lifetime;
- barrier descriptor lifetime;
- alternate sd_notify assignments beyond the three selected cases;
- upstream interaction.

## Next step

Execute the exact-current workflow. If baseline controls pass, READY-second fails, candidate passes, and the root package remains green, promote the record to a reproducible current defect with a proven one-line candidate and request human review.

## Authority

No upstream issue, pull request, email, comment, review, or patch submission was created by this investigation. Existing upstream history was read only. External contact remains unauthorized pending an explicit human decision.
