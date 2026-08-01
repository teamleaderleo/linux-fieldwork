# Proposed upstream pull request draft

State: `DRAFT ONLY — DO NOT SEND WITHOUT EXPLICIT AUTHORIZATION`

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

Focused tests cover parent-only SIGINT after nested work starts across responsive null, QEMU-wrapper, and passwordless-sudo topologies. They distinguish the imported baseline, a status-only comparator, and the group-owned candidate; verify wrapper reap and absence of later work; and retain an ordinary unsignaled success control.

The claim stops at responsive work remaining inside the owned group. TERM-resistant descendants, repeated SIGINT during cleanup, timeout/escalation policy, and descendants that create another session remain separate follow-up questions.

## Test plan

Populate with current-upstream receipts before sending:

```text
Base: 77ec9be5417ee44c96343d2347145585da1b1f94
Patch application: PENDING
Python compilation: PENDING
Focused null matrix: PENDING
Focused QEMU-wrapper matrix: PENDING
Focused sudo matrix: PENDING
Unsignaled rerun: PENDING
Full upstream suite: PENDING
```

Historical Linux Fieldwork mechanism evidence exists at PR #313, but the upstream submission must carry exact current-base commands and output.

## Submission checklist

- [ ] controlled fork exists;
- [ ] candidate commit is based on exact current upstream `main`;
- [ ] retained patch applies with zero fuzz;
- [ ] focused tests pass on the exact candidate;
- [ ] cleanup and immediate rerun pass;
- [ ] full feasible upstream gates are recorded;
- [ ] explicit external-contact authorization is recorded;
- [ ] links and test receipts are refreshed.

No pull request has been opened from this workspace.
