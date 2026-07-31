# Run 932 zero-offset carrier preflight failure

State: `classified — zero package evidence`

PR: #72  
Exact head: `b85b92f9bcd0349186b2ce58a71a23c949540431`  
Workflow: `30632658053` / 932

## Result

The changed-patch validator accepted four patch files and eight hunk declarations. The stronger composition controls then rejected stale source positions before `autopkgtest` began.

Repository discovery ran 382 tests and reported five failures, all inside `test_mmdebstrap_process_group_kill_compat.py`:

```text
capability coverage.txt hunk   offset -1
capability coverage.py hunk 1 offset -1
capability coverage.py hunk 2 offset -2
signal fixture hunk            offset +1
signal hunk-count assertion    counted closing @@ in header text
```

The disposable job applied the Deb822 patch exactly, then stopped after the capability patch emitted offset receipts. It returned status 2 with classification `carrier-preflight-failure`.

Artifact:

- ID `8793980422`;
- ZIP digest `sha256:6ebfafe44388b01d747943d0fc00de3d9d5a0b5abdec7fc0d1a3f478ef0d91a9`;
- retained patch stdout/stderr, status, preflight reason, and result record;
- no autopkgtest console, package-case result, Packet B execution, or SIGINT execution.

## Classification

This run rejects the retained source positions and one brittle test assertion. It supplies no mmdebstrap package, Packet B, cleanup, or interruption result.

The unified-diff validator answered whether declared counts matched the patch text. The composition test answered the separate question of whether each valid diff still identified the exact imported source location.

## Repair

Correct exact source positions:

```text
coverage.txt metadata        -52,6  +52,7
coverage.py parser fields    -95,6  +95,7
coverage.py skip selection   -268,10 +269,11
SIGINT fixture               -8,6   +8,6
```

Retain the testsuite capability hunk at `-205,6 +205,28`; it emitted no offset.

Parse hunk headers with an anchored regular expression instead of counting the substring `@@ `, which occurs twice in a standard header with a trailing function label.

## Reopening boundary

Only a fresh exact head whose repository discovery and disposable four-patch composition pass with zero fuzz and zero offset may create package evidence.

## Authority

Internal Linux Fieldwork evidence only. External contact authorized: false.
