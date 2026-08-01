# Unit 11 — coverage.py cancellation owns the selected backend group

State: `READY FOR AUTHORIZATION`  
Priority-zero issue: #397, unit 11  
Linux Fieldwork branch: `upstream/unit-11-coverage-backend-cancellation`  
Internal review surface: PR #401  
External contact authorized: `false`

## TL;DR

The selected candidate starts each chosen coverage backend in a dedicated session/process group. Parent-only SIGINT sends TERM to that group, waits for the wrapper, prints `interrupted by SIGINT`, and exits 130.

The clean candidate now exists in the controlled repository and passed an exact target-repository gate. The one-file target branch is byte-identical to the zero-fuzz packet-patch result. The six-control packet matrix and refined fourteen-control null/QEMU-wrapper/passwordless-sudo matrix each passed twice at the controlled target execution surface.

## Exact source identity

| Identity | Value |
| --- | --- |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Canonical branch | `main` |
| Exact canonical base | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Canonical/imported `coverage.py` blob | `9a522484aef05deae514a98e4b6adf5feb6c886d` |
| Canonical `run_null.sh` blob | `e0a8c106f9d3d636baea286d2ab33834748dffc9` |
| Canonical `run_qemu.sh` blob | `426aeeb854173569b24e64d6eb85019f45bdf0b6` |
| Controlled repository | `teamleaderleo/mmdebstrap` |
| Canonical snapshot branch | `linux-fieldwork/upstream-main-snapshot` |
| Clean source branch | `linux-fieldwork/unit-11-coverage-backend-cancellation` |
| Clean source head | `431614b3af58ba4f70791aa1d42cf5b71c965dd2` |
| Candidate `coverage.py` blob | `9e31f21cf37228257b5e0705d9ecb13b7a66e40f` |
| Clean diff | one commit; `coverage.py` only; 8 additions, 3 deletions |
| Retained patch blob | `f1a2c75adfa009b6f1ac29e5a31bef526400444f` |
| Historical mechanism head | `e90fc438f530f7bd78ffd6fd1ba24c665bd96913` |
| Historical evidence head | `dfc6d0503fb844f4c428ce16a567a9fdcd35280a` |
| Refined QEMU head | `8253ab2ef6fed22b34fc5f5d6d20cda75c25e2c7` |

The clean source branch contains no Linux Fieldwork notes, fixtures, receipts, or workflow files.

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

Responsive in-group work stops before later work can run. Ordinary unsignaled focused controls retain success.

## Controlled target execution

- internal controlled-fork PR: `teamleaderleo/mmdebstrap#2`
- PR base: `linux-fieldwork/upstream-main-snapshot@77ec9be5417ee44c96343d2347145585da1b1f94`
- runner branch/head: `linux-fieldwork/unit-11-coverage-backend-cancellation-runner@f0319d53f515174c3794237f34f76699182ac509`
- generated merge: `bf1f0cfde0ec6e0691c0dfb7d4656aafe3deab48`
- workflow run: `30706007117`
- result: success

### Candidate equivalence and null

- job `91385135488`: success
- exact source, patch, and candidate identities: verified
- zero-fuzz application: success
- materialized patch result byte-equal to clean target `coverage.py`
- target compilation: success
- packet matrix: 6/6 in 1.421 seconds
- immediate rerun: 6/6 in 1.420 seconds
- artifact `8820336271`
- SHA-256 `97eba28273b50dfcf51c32a2fe4cf49aa50da5634a3aaba6b052ad3728ae1ce8`

### Refined topology

- job `91385135449`: success
- exact PR #339 carrier and test blobs: verified
- null/QEMU-wrapper/passwordless-sudo matrix: 14/14 in 4.246 seconds
- immediate rerun: 14/14 in 4.367 seconds
- skips: none
- actual passwordless-sudo controls: executed
- artifact `8820337503`
- SHA-256 `8d72b079fa9e30ee92bdf28cf217e9df3e4ae7a5ffeb7374b76950313bf24614`

Both jobs uploaded receipts and completed orphan-process cleanup.

Durable receipt: [`artifacts/2026-08-01-controlled-target-run.md`](artifacts/2026-08-01-controlled-target-run.md).

## Canonical packet execution

Run `30689911760` passed on exact canonical source:

- zero-fuzz application and compilation twice;
- six-control packet matrix twice;
- fourteen-control refined topology matrix twice;
- no skips;
- cleanup and immediate rerun success.

Artifacts:

- `8815289674`, SHA-256 `25e62dec929f27e628816568d6264f2bee45474c00b00c3c047f53209608ef1d`;
- `8815290820`, SHA-256 `63634782bfd230129238ee71aa60ad83ae5b43dfcf3291123cfdbd0770bdf63e`.

Packet head `d232e4fdd67cf0592e129a60534e984dcbec6bfe` passed run `30690101504`. The current packet head is recorded by PR #401 and its latest exact-head run.

## Target test-layout decision

The canonical project uses `coverage.sh`, `coverage.py`, `coverage.txt`, and shell-template scenarios under `tests/`. `coverage.py` rejects non-dot `tests/` entries without matching `coverage.txt` records.

A guessed Python file under `tests/` would violate that inventory contract and be consumed through the wrong runner. No fake target-native test path is claimed. Before public submission, select one of:

1. integrate a deterministic scenario into the real `coverage.txt`/shell-template harness;
2. add an explicitly accepted separate self-test surface;
3. make a documented source-only submission decision while retaining the external reproducer.

## Scope and limits

Established:

- exact canonical base and clean target source head;
- zero-fuzz patch equivalence and target compilation;
- group-wide TERM delivery for tested responsive in-group work;
- status 130 and no later work for selected controls;
- unsignaled focused success;
- cleanup and immediate rerun.

Excluded:

- TERM-to-KILL escalation;
- repeated SIGINT policy;
- TERM-resistant, deferring, or group-escaping descendants;
- real QEMU/debvm and prepared-mirror package operations;
- direct `/dev/tty` and non-Linux execution;
- public upstream contact.

Issue #341 and closed PRs #347/#353 retain the stronger cleanup-policy comparison. No stronger product policy is selected.

## Remaining boundaries before public action

- select target-native regression integration or explicitly approve a source-only submission shape;
- run the project-declared mirror-backed/source ordinary gate at clean target head `431614b3...`;
- decide whether the isolated target workflow/PR is retained or retired after evidence transfer;
- obtain eligible independent complete clean-target-diff acceptance;
- refresh overlap and contribution-policy checks;
- grant explicit authorization for the exact public action.

## Packet navigation

- [`SOURCE_MAP.md`](SOURCE_MAP.md)
- [`DEEP_DIVE.md`](DEEP_DIVE.md)
- [`TESTS.md`](TESTS.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`HANDOFF.md`](HANDOFF.md)
- [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- [`UPSTREAM_PR.md`](UPSTREAM_PR.md)
- [`artifacts/2026-08-01-controlled-target-run.md`](artifacts/2026-08-01-controlled-target-run.md)

## Authority

Internal reads, branches, packet commits, tests, CI, and controlled-fork review are authorized. Canonical-upstream public interaction remains unauthorized and none occurred.
