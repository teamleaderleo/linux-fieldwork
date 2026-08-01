# Deep dive — coverage backend cancellation

## Mechanism

`coverage.py` chooses one backend command for each generated test: `run_null.sh`, `run_null.sh SUDO`, or `run_qemu.sh`. The imported implementation launches that wrapper in the driver's process group. A SIGINT sent only to the driver raises `KeyboardInterrupt` in Python, after which the driver terminates only the wrapper PID, waits it, and breaks into the success epilogue.

Two independent wrong results follow:

1. the original implementation can exit 0 after cancellation;
2. the status-only repair can exit 130 while nested backend work survives and performs later work.

The selected candidate establishes ownership before execution:

```python
proc = subprocess.Popen(argv, start_new_session=True)
```

The wrapper becomes leader of a new session and process group. On parent-only SIGINT, the driver targets that owned PGID:

```python
try:
    os.killpg(proc.pid, signal.SIGTERM)
except ProcessLookupError:
    pass
proc.wait()
print("interrupted by SIGINT", file=sys.stderr)
raise SystemExit(130)
```

This keeps the conventional cancellation status while widening signal delivery from one wrapper PID to the selected backend group.

## Exact observed distinctions

The historical matrices distinguish three variants under parent-only SIGINT after nested work starts:

| Variant | Driver result | Backend before deliberate release | Later work |
| --- | ---: | --- | --- |
| imported baseline | 0 | nested work alive | yes |
| merged status-only predecessor | 130 | nested work alive | yes |
| selected group candidate | 130 | no live in-group work in tested responsive topology | no |

The null model exercises a direct wrapper pipeline. The QEMU model keeps the expensive payload synthetic while preserving wrapper and foreground-operation ordering. The sudo model records UID and group identities through actual passwordless sudo.

## Why a caller-owned group

Process-group ownership is created by the caller before backend code executes. The driver therefore has a stable boundary independent of shell pipeline details inside the wrapper. `start_new_session=True` also prevents ordinary foreground-terminal SIGINT from being conflated with the supervisor-targeted parent-only case under test.

`ProcessLookupError` is accepted because the selected group may disappear between interruption and `killpg()`. The driver still waits the wrapper and publishes status 130.

## Approaches retained and rejected

### Immediate-child termination

Retired as incomplete. It repairs neither nested wrapper pipelines nor QEMU/sudo descendants. PR #204 remains useful as the status-only comparison control.

### Group TERM plus immediate wrapper wait

Selected for this unit. It has direct green evidence for responsive null, QEMU-wrapper, and sudo groups and keeps the source delta small.

### Ignore later SIGINT without an independent cleanup bound

Rejected. Synthetic evidence showed the first result could remain pending until cooperative release while later work continued.

### Bounded diagnostics without escalation

Rejected as a cleanup policy. It reports surviving PIDs while leaving the group alive.

### TERM grace followed by KILL

Technically sufficient in the synthetic resistant matrix and deliberately unselected. No real mmdebstrap backend has supplied evidence that KILL is necessary, proportional, or compatible with backend cleanup.

### Restore SIGINT before final result publication

Rejected for any future bounded policy. A later SIGINT can replace the retained result after cleanup and before durable publication. This remains follow-up evidence, outside the selected product patch.

## Compatibility analysis

- `start_new_session` is supported by Python's POSIX `subprocess.Popen` and matches mmdebstrap's Linux test environment.
- The candidate changes process membership for all selected backends. Tests that intentionally rely on sharing the coverage driver's process group would change behavior; existing focused unsignaled controls stayed green.
- Group TERM reaches only processes remaining in the owned group. A descendant that calls `setsid()` or changes groups escapes this boundary.
- Waiting only for the wrapper proves wrapper settlement. Complete group quiescence requires topology-specific evidence; the unit claims it only for the executed responsive models.
- PGID reuse was outside the historical tests. The narrow handler calls `killpg()` immediately after interruption while the wrapper is still the tracked child, minimizing the race without claiming a formal reuse proof.

## Current rebase observation — 2026-08-01

The canonical Forgejo repository advertises `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`. Its tree reports `coverage.py` last changed by the 2024 formatting commit. Linux Fieldwork `main` still carries imported blob `9a522484aef05deae514a98e4b6adf5feb6c886d` and the exact original launch/handler block.

The retained product hunk therefore has exact local context. A clean application to a fetched canonical worktree at `77ec9be...` remains the first execution gate because this session had repository API access but no network-capable shell worktree.

## Open discriminators

1. Does the upstream-root patch apply with zero fuzz to exact canonical head `77ec9be...`?
2. Does `python3 -m py_compile coverage.py` pass on that candidate?
3. Which minimal regression style will upstream accept: a dedicated Python lifecycle test, a coverage-suite test fixture, or a smaller helper-level test?
4. Do current upstream CI runners permit `start_new_session`, `killpg`, `/proc` inspection, and passwordless sudo controls?
5. Has any real backend shown TERM resistance or session escape? Until that evidence exists, escalation stays outside this unit.

## External boundary

No public issue, pull request, review, email, or comment was created. Upstream contact requires explicit authorization.
