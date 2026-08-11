# Current-source review — runc sd_notify READY field ordering

Date: 2026-08-11

Internal tracking: `teamleaderleo/linux-fieldwork#596`

## TL;DR

Current runc `main` at `7495faeac77318158e6d5faece1b0b0d53e6ced4` still carries the READY-ordering regression in `notify_socket.go`.

`notifySocket.run()` reads one Unix datagram into `got`, splits it into newline-separated `line` values, then checks `bytes.HasPrefix(got, []byte("READY="))`. The loop variable is therefore ignored by the predicate. A valid sd_notify datagram with another assignment first, such as `STATUS=warming\nREADY=1`, is not recognized as ready.

History pins the regression. The 2017 sanitization commit `c8593c4d61b169d5a3942fb5fe5904466f82a3b1` intentionally checked each split `line` for `READY=`. The 2018 create/start refactor in PR 1807 retained the field loop but changed the predicate receiver from `line` to `got`. That exact form persists on current main, now using `bytes.SplitSeq`.

A fresh reduced Go discriminator confirms the one-line restoration:

```text
input="READY=1\nSTATUS=ok"               current="READY=1" candidate="READY=1"
input="STATUS=warming\nREADY=1"           current=""        candidate="READY=1"
input="STATUS=warming\nERRNO=0"           current=""        candidate=""
input="STATUS=warming\nREADY=1\nMAINPID=99" current=""        candidate="READY=1"
```

The owned fork now has a one-commit, one-file source candidate:

- branch: `teamleaderleo/runc:linux-fieldwork/sd-notify-ready-order`
- base: `7495faeac77318158e6d5faece1b0b0d53e6ced4`
- head: `8779ed35a3a567a2ddd18fb5bf0d4ba095cf65ba`
- diff: `notify_socket.go`, +1/-1
- change: `bytes.HasPrefix(got, ...)` -> `bytes.HasPrefix(line, ...)`

Internal draft PR `teamleaderleo/runc#8` is retargeted to the controlled exact-base branch `linux-fieldwork/upstream-2026-08-11`, so its review diff is exactly one commit and one file. Hosted `ci` and `validate` workflows were queued on the candidate head at this checkpoint.

No upstream interaction was made.

## Explain like I'm five

systemd notifications can contain several lines in one datagram:

```text
STATUS=warming
READY=1
```

runc walks those lines one by one, but current code asks whether the whole message starts with `READY=` instead of asking whether the line it is currently looking at starts with `READY=`.

Changing the predicate back to the current line restores the behavior the original implementation had.

## Why care

The proxy can suppress a valid readiness notification solely because another valid sd_notify assignment is ordered first. For a service manager waiting on readiness, that can delay or suppress the transition until another READY datagram arrives or the watched process exits.

The repair does not broaden the forwarding policy: runc still forwards only the READY assignment, then MAINPID and the existing barrier handshake.

## Exact source boundary

- Project: `opencontainers/runc`
- Current upstream main: `7495faeac77318158e6d5faece1b0b0d53e6ced4`
- `notify_socket.go` blob: `0e73098bc619479f5a6dc34027ebfaa89739b974`
- `notify_socket_test.go` blob: `81210851d3bbcd2272c596874f88fb08ba650e63`
- Current Go requirement: `go 1.25.0`
- Owned fork: `teamleaderleo/runc`
- Candidate branch/head: `linux-fieldwork/sd-notify-ready-order@8779ed35a3a567a2ddd18fb5bf0d4ba095cf65ba`
- Controlled review base: `linux-fieldwork/upstream-2026-08-11@7495faeac77318158e6d5faece1b0b0d53e6ced4`
- Internal draft PR: `teamleaderleo/runc#8`

## Current implementation

The relevant current loop is:

```go
got := buf[0:r]
for line := range bytes.SplitSeq(got, []byte{'\n'}) {
    if bytes.HasPrefix(got, []byte("READY=")) {
        fileChan <- line
        return
    }
}
```

Because the predicate reads `got`, the outcome depends on the first bytes of the complete datagram.

If `got` begins with `READY=`, the first loop iteration forwards the first field and returns. If `got` begins with `STATUS=`, `ERRNO=`, or another assignment, no later field can satisfy the predicate because `got` never changes.

## Existing tests

Current `notify_socket_test.go` exercises `notifyHost()` directly: it checks forwarding of one READY payload, the MAINPID message, and the barrier protocol.

It does not send a multi-field datagram through `notifySocket.run()` and therefore does not distinguish READY-first from READY-later ordering.

That missing integration seam explains why the field-selection regression can survive while the downstream forwarding/barrier test remains green.

## Intent/history

### 2017 sanitization

Commit `c8593c4d61b169d5a3942fb5fe5904466f82a3b1` changed the proxy from forwarding the entire untrusted container datagram to forwarding only READY assignments.

Its implementation explicitly did:

```go
for _, line := range bytes.Split(buf[0:r], []byte{'\n'}) {
    if bytes.HasPrefix(line, []byte("READY=")) {
        ...
    }
}
```

This is direct intent evidence for field-oriented matching.

### 2018 create/start refactor

Merged PR 1807 (`167e33ca5086018828be753b57a7bd1f4d5a1edb`) moved socket reading into a goroutine and introduced the PID-liveness ticker so `runc create/start` would not hang on notify handling.

During that refactor the code became:

```go
for _, line := range bytes.Split(got, []byte{'\n'}) {
    if bytes.HasPrefix(got, []byte("READY=")) {
        fileChan <- line
        return
    }
}
```

The refactor's stated goal was lifecycle/nonblocking behavior. No field-order policy change is described in its PR purpose. The retained loop also continued to name and forward `line`.

This supports classifying `got` as a mechanical regression rather than a deliberate requirement that READY appear first.

## Fresh reduced discriminator

The local execution sandbox has Go 1.23.2, while current runc requires Go 1.25.0 and uses `bytes.SplitSeq`, which is unavailable in the local toolchain.

The fresh probe therefore used `bytes.Split` with the same field partition and compared only the decision predicate. That is exact-logic execution, not a full current-tree test.

Inputs and results:

| Datagram | Current predicate | Candidate predicate |
| --- | --- | --- |
| `READY=1\nSTATUS=ok` | `READY=1` | `READY=1` |
| `STATUS=warming\nREADY=1` | none | `READY=1` |
| `STATUS=warming\nERRNO=0` | none | none |
| `STATUS=warming\nREADY=1\nMAINPID=99` | none | `READY=1` |

The no-READY row is the negative control: changing the predicate to `line` does not turn arbitrary state datagrams into readiness.

## Candidate

The source candidate restores the historical predicate:

```diff
- if bytes.HasPrefix(got, []byte("READY=")) {
+ if bytes.HasPrefix(line, []byte("READY=")) {
```

No parser helper, new state, error policy, socket behavior, or host-notification behavior is added.

## Review carrier freshness

The owned fork's default `main` was behind current upstream. The first internal draft PR therefore initially showed unrelated upstream commits in its comparison.

That review-base error was repaired without rewriting the product branch:

1. preserve candidate branch at exact current upstream base;
2. create controlled base branch `linux-fieldwork/upstream-2026-08-11` at `7495fae...`;
3. retarget internal PR #8 to that base.

After retargeting, GitHub reports one commit, one changed file, +1/-1.

This is review-carrier hygiene, not product behavior.

## Next regression test

The strongest source test should exercise the real Unix-datagram `notifySocket.run()` path rather than only a parser helper.

Positive rows:

1. `READY=1\nSTATUS=ok` -> host receives `READY=1\n`, then `MAINPID=...`, then barrier;
2. `STATUS=warming\nREADY=1` -> same result.

Negative row:

3. `STATUS=warming\nERRNO=0` -> no READY reaches the host before `run()` exits on a deliberately nonexistent watched PID.

The existing `expectRead()` and `expectBarrier()` helpers can be reused for the positive rows. A negative test can give the host socket a bounded read deadline and use an intentionally nonexistent PID so `run()` terminates via its existing liveness ticker.

Keep this as product regression coverage if it compiles cleanly under the project's Go 1.25 toolchain.

## Evidence boundary

Established:

- exact current source still has the whole-datagram predicate;
- existing current tests do not cover READY field ordering in `run()`;
- original accepted implementation checked each field;
- the 2018 lifecycle refactor introduced `got` in the predicate while retaining the field loop;
- fresh reduced execution distinguishes READY-first, READY-later, and no-READY cases;
- owned candidate is one current-base commit changing one predicate;
- internal draft PR comparison is exact after base retargeting.

Pending at this checkpoint:

- current-tree Go 1.25 unit/integration regression for READY-second;
- candidate test covering the real `notifySocket.run()` Unix-datagram path;
- final hosted CI/validate conclusions;
- project DCO/sign-off packaging if a human later decides to submit anything.

## Current disposition

- State: `REPAIR / VALIDATING`
- Exact upstream base: `7495faeac77318158e6d5faece1b0b0d53e6ced4`
- Candidate head: `8779ed35a3a567a2ddd18fb5bf0d4ba095cf65ba`
- Product scope: one file, +1/-1
- Internal carrier: `teamleaderleo/runc#8`
- Hosted gates: queued at this checkpoint
- Next safe action: inspect hosted gates, then add/execute the real-datagram regression on a review variant and rebuild to one clean source commit if it survives
- External-contact state: no upstream comment, issue, PR, review, reaction, email, or patch submission authorized or made
