# Tini startup lifecycle scout — 2026-08-11

## In simple words

This scout picked `krallin/tini` as a compact Linux process-lifecycle target and followed two adjacent startup timing questions into separate investigations. Both findings sit at commit `369448a167e8b3da4ca5bca0b3307500c3371828`, both have deterministic reduced Linux syscall evidence, and both still need a Tini-native exact-binary run before promotion to an upstream-ready candidate.

## Why Tini

Tini is small, Linux-specific in the relevant paths, and responsible for signal forwarding, process groups, zombie reaping, subreaper behavior, exit translation, tty ownership, and parent-death coupling. That creates high information density for the Fieldwork lifecycle lenses without requiring a broad source tree.

The selection heuristic fit was strong:

- exact operation owner in one C file;
- small distinguishing fixtures;
- multiple plausible startup orderings;
- clean steady-state controls already present upstream;
- bounded cleanup;
- results that directly change whether a source candidate is worth building.

## Exact source boundary

- Project: `krallin/tini`
- Canonical repository: https://github.com/krallin/tini
- Resolved commit: `369448a167e8b3da4ca5bca0b3307500c3371828`
- Main source reviewed: `src/tini.c`
- Main test orchestration reviewed: `test/run_inner_tests.py`
- Historical process-group feature: https://github.com/krallin/tini/pull/16
- Historical parent-death feature: https://github.com/krallin/tini/pull/114

## Finding 1 — process-group signal can lose at startup

Tracked investigation: [`../../../investigations/tini-process-group-startup-signal-race/README.md`](../../../investigations/tini-process-group-startup-signal-race/README.md)

Current source blocks forwarded signals, forks, lets only the child create the child PGID, then lets the parent wait and forward to `-child_pid`. A pending signal can therefore be consumed while the process group still does not exist.

Reduced signal-forwarding fixture, 10,000 iterations:

```text
current-order: iters=10000 forwarded=41 ESRCH=9959 other=0 child-died-SIGUSR1=41
parent-setpgid-order: iters=10000 forwarded=10000 ESRCH=0 other=0 child-died-SIGUSR1=10000
```

The current upstream process-group test waits for the full descendant tree before signaling, which is a useful steady-state control and explains why this startup ordering is outside current coverage.

## Finding 2 — parent-death event can be missed during startup

Tracked investigation: [`../../../investigations/tini-parent-death-startup-race/README.md`](../../../investigations/tini-parent-death-startup-race/README.md)

Current source installs `PR_SET_PDEATHSIG` only after argument parsing, environment parsing, and signal configuration. Linux does not synthesize a parent-death signal for a parent that already exited before the `prctl()`.

Reduced parent-lifecycle fixture, repeated five times:

```text
current-order: SIGUSR1-pending=0
ppid-check-order: SIGUSR1-pending=1
```

Each repetition produced the same pair. The existing upstream parent-death test exercises the steady-state case after Tini has fully installed the setting.

## Cross-context pass

Adjacent contexts checked before splitting the findings:

1. **Steady-state versus startup** — upstream tests prove the post-readiness mechanisms; both findings occur before those readiness points.
2. **Direct PID versus process group** — the startup PGID race is specific to `-g` / `TINI_KILL_PROCESS_GROUP`; direct-child forwarding names an existing PID and acts as the negative control.
3. **Kernel-generated versus compensated parent-death signal** — post-install parent death remains kernel-owned; only the pre-install identity change needs a candidate discriminator.
4. **Shared source owner** — both live in `src/tini.c`, but they have separate invariants, fixtures, candidate mechanisms, and stop conditions, so they were split into independent investigations.

## Environment and execution boundary

Local execution environment:

- Debian GNU/Linux 13
- Linux 6.18.35 x86_64
- GNU bash 5.2.37
- GCC 14.2.0
- disposable container, uid 0

Direct shell DNS access to `github.com` was unavailable, so the Tini repository could not be cloned into the execution container. Exact source and history were read through the connected GitHub repository; execution used reduced C fixtures reproducing the decisive Linux syscall orderings.

## Disposition

- Promote Tini to an active mapped target because two separate investigations now depend on the same source/test surfaces.
- Retain both findings as `REVIEW` candidates.
- Next useful work is Tini-native execution, starting with process-group startup signaling because its reduced fixture shows direct signal loss and a clean parent-side PGID discriminator.
- Keep upstream interaction closed until the human explicitly authorizes it.

## Outputs

- [`../../../targets/tini/map.md`](../../../targets/tini/map.md)
- [`../../../investigations/tini-process-group-startup-signal-race/`](../../../investigations/tini-process-group-startup-signal-race/)
- [`../../../investigations/tini-parent-death-startup-race/`](../../../investigations/tini-parent-death-startup-race/)

## Authority

No Tini issue, email, pull request, patch submission, comment, review, or other upstream interaction was authorized or made during this scout.
