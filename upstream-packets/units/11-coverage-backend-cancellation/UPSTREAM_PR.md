# Proposed upstream pull request draft

State: `READY DRAFT — DO NOT SEND WITHOUT EXPLICIT AUTHORIZATION`

## Title

`coverage: cancel the selected backend process group on SIGINT`

## Body

`coverage.py` now starts each selected backend in a dedicated session/process group. When SIGINT is delivered directly to the coverage driver, it sends SIGTERM to that owned group, waits for the backend wrapper, prints `interrupted by SIGINT`, and exits 130.

Previously, the handler terminated only the immediate wrapper and broke into the ordinary epilogue. That allowed two wrong outcomes:

- a cancelled matrix could return status 0;
- nested work behind the null, sudo, or QEMU wrapper could survive even after a status-only 130 repair.

The source change is intentionally bounded:

```python
proc = subprocess.Popen(argv, start_new_session=True)
...
try:
    os.killpg(proc.pid, signal.SIGTERM)
except ProcessLookupError:
    pass
proc.wait()
print("interrupted by SIGINT", file=sys.stderr)
raise SystemExit(130)
```

Focused tests cover parent-only SIGINT after nested work starts across responsive null, QEMU-wrapper, and passwordless-sudo topologies. They distinguish the imported baseline, a status-only comparator, and the group-owned candidate; verify wrapper reap and absence of later work; and retain ordinary foreground-group and unsignaled success controls.

The QEMU losing controls wait for an exact Python SIGINT-handler receipt before deliberately releasing the surviving operation. This removes an ordering race from the negative controls.

The claim stops at responsive work remaining inside the owned group. TERM-resistant descendants, repeated SIGINT during cleanup, timeout/escalation policy, and descendants that create another session remain separate follow-up questions.

## Test plan

Exact current-base receipt:

```text
Base: 77ec9be5417ee44c96343d2347145585da1b1f94
coverage.py blob: 9a522484aef05deae514a98e4b6adf5feb6c886d
run_null.sh blob: e0a8c106f9d3d636baea286d2ab33834748dffc9
run_qemu.sh blob: 426aeeb854173569b24e64d6eb85019f45bdf0b6
Patch application: success, --fuzz=0, twice
Python compilation: success
Focused packet matrix: 6/6, twice
Refined null/QEMU-wrapper/sudo matrix: 14/14, twice, no skips
Passwordless-sudo root-worker controls: executed
Unsignaled controls: success
Cleanup and immediate rerun: success
Linux Fieldwork Actions run: 30689911760
```

Retained artifacts:

```text
8815289674  unit-11-canonical-upstream-gate
sha256:25e62dec929f27e628816568d6264f2bee45474c00b00c3c047f53209608ef1d

8815290820  unit-11-canonical-refined-topology-gate
sha256:63634782bfd230129238ee71aa60ad83ae5b43dfcf3291123cfdbd0770bdf63e
```

Historical full-repository mechanism gate `30632491641` also passed all 359 discovered Linux Fieldwork tests, Python compilation, shell syntax, and command-help checks.

## Evidence limits

- real QEMU/debvm and prepared-mirror package operations were outside the focused wrapper controls;
- TERM-resistant or group-escaping descendants remain outside this patch;
- non-Linux behavior remains outside the project/runtime target;
- upstream CI and maintainer review begin only after authorized submission.

## Submission checklist

- [ ] explicit external-contact authorization recorded;
- [ ] controlled fork selected or created;
- [ ] candidate commit created from exact current upstream `main`;
- [x] retained patch applies with zero fuzz;
- [x] focused tests pass on exact canonical source;
- [x] cleanup and immediate rerun pass;
- [x] exact source, patch, test, run, and artifact identities recorded;
- [ ] links refreshed immediately before sending.

No upstream pull request has been opened from this workspace.
