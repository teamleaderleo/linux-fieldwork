# runc sd-notify READY field ordering

## TL;DR

At upstream runc commit `0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`, `notifySocket.run` splits an sd_notify datagram into newline-separated fields but tests `READY=` against the whole datagram instead of the current field. A reduced executable probe reproduces the distinction: `READY=1\nSTATUS=ok` is recognized, while the equally valid `STATUS=ok\nREADY=1` is missed.

History makes this look like a regression rather than a deliberate restriction. The original proxy checked each `line`; the 2018 create/start refactor changed the check to `got` while retaining the line loop. The next step is a focused runc test that proves both field orders, followed by the smallest restoration from `got` to `line` if the full source test reproduces the reduced result.

## Explain like I'm five

A program can tell systemd several things in one message:

```text
STATUS=warming up
READY=1
```

runc reads those lines one at a time. Today it asks whether the entire message starts with `READY=`. That means readiness is seen only when `READY=` happens to be the first field.

Literal example:

```text
READY=1\nSTATUS=ok -> readiness found
STATUS=ok\nREADY=1 -> readiness missed
```

## Why care

The runc sd_notify proxy sits between a container and the host service manager. A valid readiness notification can be ignored solely because another valid assignment appears first in the same datagram, leaving the host waiting for readiness until another notification arrives or the watched process exits.

## Current state

- State: `SCOPING`
- Exact working head: upstream runc `0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`; owned fork `teamleaderleo/runc` matches this head
- Latest authoritative gate or artifact: reduced executable parser probe, 2026-08-11
- First incomplete step: reproduce with a focused test inside the full runc source tree
- Cleanup state: disposable probe files only; no external state changed
- Next safe action: add a fork-only failing test covering `STATUS=...\nREADY=1` and a negative control without READY
- External-contact state: none authorized or made

## Intent and precedent

The sd_notify proxy was introduced by [runc PR 1308](https://redirect.github.com/opencontainers/runc/pull/1308). Its original loop checked the current split field:

```go
for _, line := range bytes.Split(buf[0:r], []byte{'\n'}) {
    if bytes.HasPrefix(line, []byte("READY=")) {
        // forward readiness
    }
}
```

[runc PR 1807](https://redirect.github.com/opencontainers/runc/pull/1807) refactored create/start notification handling. In that change the loop remained field-oriented, but the predicate became:

```go
for _, line := range bytes.Split(got, []byte{'\n'}) {
    if bytes.HasPrefix(got, []byte("READY=")) {
        fileChan <- line
        return
    }
}
```

That form persists through current main, now using `bytes.SplitSeq`.

systemd's `sd_notify` contract describes the state payload as a newline-separated list of variable assignments. `READY=1` and `STATUS=...` are both defined assignments. The source contract does not give READY a required first-field position.

## Question

Does current runc fail to proxy a valid sd_notify readiness datagram when `READY=...` appears after another assignment in the same datagram?

## Source

- Project: opencontainers/runc
- Requested revision: current upstream `main` during this scout
- Resolved commit: `0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`
- Candidate source commit: none yet
- Relevant paths: `notify_socket.go`, `notify_socket_test.go`
- Owned fork: `teamleaderleo/runc`, `main` at the same resolved commit
- Historical carriers:
  - [runc PR 1308](https://redirect.github.com/opencontainers/runc/pull/1308)
  - [runc PR 1807](https://redirect.github.com/opencontainers/runc/pull/1807)
  - [runc PR 3291](https://redirect.github.com/opencontainers/runc/pull/3291)

## Environment

Reduced source-level probe:

- Platform: Linux amd64 execution sandbox
- Go: `go1.23.2 linux/amd64`
- Privileges: ordinary local process; no container runtime or systemd required
- Full runc integration environment: not yet executed

## Baseline behavior

A standalone Go probe copied the current field loop exactly and compared it with the historical field predicate.

Observed output:

```text
ordering current first="READY=1" second=""
ordering intended first="READY=1" second="READY=1"
```

Where:

```text
first  = READY=1\nSTATUS=ok
second = STATUS=ok\nREADY=1
```

The current predicate therefore depends on datagram ordering.

## Hypothesis or candidate

Minimal candidate:

```diff
- if bytes.HasPrefix(got, []byte("READY=")) {
+ if bytes.HasPrefix(line, []byte("READY=")) {
```

This restores the original proxy behavior and leaves the larger policy untouched: runc still selects the READY assignment to forward and continues to let systemd interpret its value.

### Distinguishing test

The focused test should cover at least:

1. `READY=1\nSTATUS=ok` -> READY is found;
2. `STATUS=ok\nREADY=1` -> READY is found;
3. `STATUS=ok` -> no READY is found.

The third case is the negative control so the parser cannot simply treat every datagram as ready.

## Reproduction

Reduced probe logic:

```go
func currentReady(got []byte) []byte {
    for _, line := range bytes.Split(got, []byte{'\n'}) {
        if bytes.HasPrefix(got, []byte("READY=")) {
            return line
        }
    }
    return nil
}
```

Run the same inputs through a version whose predicate uses `line` to obtain the losing comparison above.

## Results

Demonstrated at the reduced parser level:

- a datagram beginning with READY is recognized;
- the same READY field after STATUS is missed;
- changing only the predicate receiver from the whole datagram to the current field removes the ordering dependence.

Source history independently shows that the original implementation used the current field and the 2018 refactor introduced the whole-datagram predicate.

## Interpretation

This is a high-confidence regression candidate. The implementation has a loop variable whose sole purpose is to inspect individual assignments, while the predicate reads a different variable. The historical implementation and the sd_notify payload contract agree on field-oriented parsing.

The strongest repair boundary appears to be the predicate itself. A larger parser redesign would add risk without improving the bounded contract under test.

## Evidence boundary

The reduced probe executes the exact parsing expression and proves its order dependence. It does not yet run runc's real Unix datagram loop, a container, or a systemd service. Timing, PID-liveness behavior, and host notification forwarding remain outside this claim.

No upstream issue or pull request search found a current carrier specifically for READY field ordering during the 2026-08-11 scout, but repository search is not proof that no overlapping work exists. Refresh before any publication decision.

## Next step

Add a focused test on the owned runc fork from exact head `0c87c02f...` that sends both field orders through the real `notifySocket.run` path or through a minimal extracted parser helper. Require the baseline to fail on READY-second and the negative control to remain non-ready. Then test the one-line candidate.

## Authority

No upstream contact is authorized or made. All work remains local or in `teamleaderleo/*` repositories unless a human explicitly authorizes publication.
