# Unit 11 — coverage.py cancellation owns the selected backend group

State: `READY FOR AUTHORIZATION`  
Priority-zero issue: #397, unit 11  
Internal packet review: `teamleaderleo/linux-fieldwork#401`  
Clean target review: `teamleaderleo/mmdebstrap#4`  
External contact authorized: `false`

## TL;DR

The selected source-only candidate starts each chosen coverage backend in a dedicated session/process group. Parent-only SIGINT sends TERM to that group, waits for the wrapper, prints `interrupted by SIGINT`, and exits 130.

The exact clean target branch passed focused target execution and a bounded project-native ordinary source slice. The clean one-file diff is ready for eligible independent review. No canonical-upstream contact occurred.

## Exact source identity

| Identity | Value |
| --- | --- |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Canonical branch | `main` |
| Exact canonical base | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Base `coverage.py` blob | `9a522484aef05deae514a98e4b6adf5feb6c886d` |
| Canonical `run_null.sh` blob | `e0a8c106f9d3d636baea286d2ab33834748dffc9` |
| Canonical `run_qemu.sh` blob | `426aeeb854173569b24e64d6eb85019f45bdf0b6` |
| Retained patch blob | `f1a2c75adfa009b6f1ac29e5a31bef526400444f` |
| Controlled repository | `teamleaderleo/mmdebstrap` |
| Snapshot branch | `linux-fieldwork/upstream-main-snapshot` |
| Clean source branch | `linux-fieldwork/unit-11-coverage-backend-cancellation` |
| Clean source head | `431614b3af58ba4f70791aa1d42cf5b71c965dd2` |
| Candidate `coverage.py` blob | `9e31f21cf37228257b5e0705d9ecb13b7a66e40f` |
| Clean diff | `coverage.py` only; 8 additions, 3 deletions |
| Clean internal review | `teamleaderleo/mmdebstrap#4`, ready for independent review |

The clean source branch contains no packet notes, fixtures, receipts, workflows, or unrelated source.

## Accomplished behavior

```python
proc = subprocess.Popen(argv, start_new_session=True)
try:
    proc.wait()
except KeyboardInterrupt:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    proc.wait()
    print("interrupted by SIGINT", file=sys.stderr)
    raise SystemExit(130)
```

## Focused controlled-target execution

Closed internal execution PR: `teamleaderleo/mmdebstrap#2`.

- run `30706007117`: success
- job `91385135488`: zero-fuzz application, byte equivalence, compilation, 6/6 twice
- job `91385135449`: refined null/QEMU-wrapper/passwordless-sudo matrix 14/14 twice, no skips
- actual sudo controls: executed
- cleanup and immediate rerun: success
- artifacts `8820336271` and `8820337503` with retained SHA-256 digests

See [`artifacts/2026-08-01-controlled-target-run.md`](artifacts/2026-08-01-controlled-target-run.md).

## Project-native ordinary source slice

Closed internal execution PR: `teamleaderleo/mmdebstrap#3`.

- run `30706633832`, job `91386769087`: success
- command: `./coverage.sh help man version`
- first pass: 3/3
- immediate rerun: 3/3
- real `coverage.py` inventory and `run_null.sh`: exercised
- artifact `8820528312`
- SHA-256 `13986015aebc37cd3624f5114baa2a599f3c3dccb01e838b367287b2585b8f55`

The exact base has a pre-existing source-check defect: Black wants to reformat unchanged canonical `tarfilter` blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`. The successful gate isolates only that exact blob and keeps real Black 26.5.1 enforcement for `coverage.py` and every other checked Python file.

See [`artifacts/2026-08-01-ordinary-source-slice.md`](artifacts/2026-08-01-ordinary-source-slice.md).

## Source-only submission shape

The target suite treats every non-dot `tests/` entry as a shell-template package scenario indexed by `coverage.txt`. Testing this outer orchestrator from inside that same harness would require a recursive miniature coverage tree substantially larger than the source correction.

The clean target contribution is deliberately source-only. The deterministic baseline/candidate reproducer and exact target receipts remain in this packet. A native recursive test is a reopen item if an eligible reviewer or upstream maintainer requires it.

See [`artifacts/2026-08-01-source-only-submission-shape.md`](artifacts/2026-08-01-source-only-submission-shape.md).

## Canonical and historical execution

Canonical packet run `30689911760` passed zero-fuzz application, compilation, 6/6 twice, and 14/14 twice. Packet head `d232e4fdd67cf0592e129a60534e984dcbec6bfe` passed run `30690101504`.

Historical repository gates:

- mechanism head `e90fc438f530f7bd78ffd6fd1ba24c665bd96913`: 359 tests passed;
- evidence head `dfc6d0503fb844f4c428ce16a567a9fdcd35280a`: 340 unique tests passed;
- refined QEMU head `8253ab2ef6fed22b34fc5f5d6d20cda75c25e2c7`: 269 tests passed.

## Scope and limits

Established:

- exact canonical base and clean target source identity;
- zero-fuzz patch and source byte equivalence;
- target compilation;
- group-wide TERM delivery for tested responsive in-group work;
- status 130 and no later work for selected controls;
- unsignaled focused success;
- project-native ordinary source/interface success twice;
- cleanup and immediate rerun.

Limits:

- TERM-resistant, deferring, or group-escaping descendants;
- repeated-SIGINT and escalation policy;
- full prepared-mirror 283-entry package matrix;
- real QEMU/debvm package operations;
- non-Linux behavior;
- public upstream CI and maintainer acceptance.

## Remaining internal gate

The clean source PR `teamleaderleo/mmdebstrap#4` requires eligible independent complete-diff acceptance. Same-account self-review found no blocking defect but does not satisfy that gate.

After independent acceptance, refresh overlap and contribution-policy checks and obtain explicit authority for the exact public action.

## Navigation

- [`SOURCE_MAP.md`](SOURCE_MAP.md)
- [`DEEP_DIVE.md`](DEEP_DIVE.md)
- [`TESTS.md`](TESTS.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`HANDOFF.md`](HANDOFF.md)
- [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- [`UPSTREAM_PR.md`](UPSTREAM_PR.md)
- [`artifacts/`](artifacts/)

## Authority

Internal reads, branches, packet commits, tests, CI, and controlled-fork review are authorized. Canonical-upstream public interaction remains unauthorized and none occurred.
