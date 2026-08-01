# HANDOFF — unit 11 coverage backend cancellation

Date: 2026-08-01  
State: `READY FOR AUTHORIZATION`  
Linux Fieldwork packet: `teamleaderleo/linux-fieldwork#401`  
Clean target review: `teamleaderleo/mmdebstrap#4`  
External contact authorized: `false`  
External contact made: `none`

## Exact stopping point

The source unit is technically complete for its bounded TERM-responsive claim.

Completed:

- exact canonical base and source identity;
- clean one-file controlled target branch;
- zero-fuzz patch and source byte equivalence;
- focused target execution twice;
- refined null/QEMU-wrapper/passwordless-sudo execution twice with no skips;
- project-native ordinary source/interface slice twice;
- source-only submission-shape decision;
- complete same-account clean-diff self-review;
- clean PR ready for eligible independent review;
- polished upstream draft;
- no canonical-upstream contact.

First incomplete step:

- eligible independent complete-diff acceptance on `teamleaderleo/mmdebstrap#4`.

## Exact target identity

- canonical repository: `https://gitlab.mister-muffin.de/josch/mmdebstrap`;
- exact base: `77ec9be5417ee44c96343d2347145585da1b1f94`;
- base `coverage.py` blob: `9a522484aef05deae514a98e4b6adf5feb6c886d`;
- controlled repository: `teamleaderleo/mmdebstrap`;
- snapshot branch: `linux-fieldwork/upstream-main-snapshot`;
- clean source branch: `linux-fieldwork/unit-11-coverage-backend-cancellation`;
- clean source head: `431614b3af58ba4f70791aa1d42cf5b71c965dd2`;
- candidate `coverage.py` blob: `9e31f21cf37228257b5e0705d9ecb13b7a66e40f`;
- changed files: `coverage.py` only;
- diff: 8 additions, 3 deletions;
- patch blob: `f1a2c75adfa009b6f1ac29e5a31bef526400444f`;
- clean review surface: `teamleaderleo/mmdebstrap#4`, ready for independent review.

## Selected mechanism

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

## Focused target receipt

Run `30706007117`: success.

- job `91385135488`: zero-fuzz application, byte equivalence, compilation, 6/6 twice;
- job `91385135449`: 14/14 twice, no skips, actual sudo controls;
- artifacts `8820336271` and `8820337503` with retained SHA-256 digests;
- cleanup and immediate rerun succeeded.

See `artifacts/2026-08-01-controlled-target-run.md`.

## Ordinary project-native receipt

Run `30706633832`, job `91386769087`: success.

- command: `./coverage.sh help man version`;
- first pass: 3/3;
- immediate rerun: 3/3;
- real `coverage.py` inventory and `run_null.sh` executed;
- artifact `8820528312`;
- SHA-256 `13986015aebc37cd3624f5114baa2a599f3c3dccb01e838b367287b2585b8f55`.

The exact base has a proven unrelated Black failure on unchanged canonical `tarfilter` blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`. The successful gate isolates only that exact blob and retains normal Black checks for the changed source.

See `artifacts/2026-08-01-ordinary-source-slice.md`.

## Source-only decision

The clean target diff contains no native regression file.

The target suite treats each non-dot `tests/` entry as a `coverage.txt`-indexed shell-template package scenario. A native test of the outer coverage orchestrator would require a recursive miniature coverage tree substantially larger than the source correction.

The deterministic external reproducer and exact target receipts are retained. Reopen this decision if eligible review or upstream policy requires a recursive native test.

See `artifacts/2026-08-01-source-only-submission-shape.md`.

## Latest distinguishing result

| Variant | Status | Later work |
| --- | ---: | --- |
| imported baseline | 0 after deliberate release | yes |
| status-only predecessor | 130 after release | yes |
| selected group candidate | 130 | no |

## Evidence limits

- arbitrary TERM-resistant or group-escaping descendant drain;
- repeated-SIGINT and escalation policy;
- full prepared-mirror 283-entry package matrix;
- real QEMU/debvm package operations;
- non-Linux behavior;
- public upstream CI and maintainer review.

These remain visible limits, not contradictions of the selected responsive-topology result.

## Next safe action

An eligible non-author reviews the complete one-file diff on `teamleaderleo/mmdebstrap#4` and either:

- accepts it;
- requests a concrete source or claim change;
- requires a recursive native test;
- requires broader prepared-mirror execution;
- records a specific hold condition.

Do not assign an unrelated account merely to clear the gate.

## After independent acceptance

1. refresh canonical `main` and compare it with `77ec9be...`;
2. refresh overlap, contribution policy, and AI-disclosure requirements;
3. update exact public links and source identity if the base moved;
4. request explicit authority for the exact public action;
5. submit only the authorized surface;
6. record the public reference and submitted identity in all packet surfaces.

## Recovery guide

Read in this order:

1. `README.md`;
2. `TESTS.md`;
3. `artifacts/2026-08-01-controlled-target-run.md`;
4. `artifacts/2026-08-01-ordinary-source-slice.md`;
5. `artifacts/2026-08-01-source-only-submission-shape.md`;
6. `UPSTREAM_PR.md`;
7. clean target PR `teamleaderleo/mmdebstrap#4`;
8. packet PR `teamleaderleo/linux-fieldwork#401`.

## Authority

Internal review and packet maintenance may continue. Public canonical-upstream interaction requires explicit authorization. None occurred.
