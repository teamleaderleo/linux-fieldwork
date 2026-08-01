# Unit 05 — mmdebstrap `run_qemu.sh` result precedence

State: `HOLD`  
Priority-zero issue: #397, unit 05  
Worker or variant: `GPT-5.6 Thinking upstream extraction and complete-diff repair`  
Linux Fieldwork branch: `upstream/unit-05-run-qemu-result-precedence`  
External contact authorized: `false`

## TL;DR

The controlled mirror base is exact, the candidate is a five-commit one-file series, and the retained lifecycle matrix is green. Complete-diff review found two deterministic signal-handler setup windows in the earlier four-commit candidate; commit `6efe6945f9f89cff57fe84086ede7bda747c3879` closes both windows without changing the selected result order.

```text
repository: teamleaderleo/mmdebstrap
base: 574048f2a720057b75e56622003932f344dc700a
branch: linux-fieldwork/unit-05-run-qemu-result-precedence
head: 6efe6945f9f89cff57fe84086ede7bda747c3879
relation: five commits ahead, zero behind
changed files: run_qemu.sh only
final blob: 1fc816d6fe982351f6519fd1458329112eebdcfb
bytes: 3095
SHA-256: 434e7b6b9c32e30b506ea6af121608414c42b668c329e6395e75e19dc09ff276
```

Selected result order:

```text
captured host failure
> completed guest or protocol failure
> first signal received during ordinary cleanup
> first cleanup failure
> success
```

The unit is on `HOLD` for two named gates: reconcile against current canonical Salsa `master` and active equivalent work; then run mmdebstrap's current QEMU-classified project tests on the exact rebased head. The user has no fetch or setup task.

## Explain like I'm five

The wrapper can learn several bad outcomes while shutting down: the host command failed, the guest failed, someone interrupted it, or cleanup failed. It must remember the first outcome that already owned the result and still finish cleaning up.

The earlier candidate did that after each handler was fully set up, but a second signal could arrive during the few commands used to enter a handler. The fifth commit closes those entry windows before other handler work begins.

## Why care

Without explicit precedence, a timeout can become a generic guest failure, a completed guest failure can become a later signal, or a second signal can replace the first. Those results point debugging at the wrong owner. Interrupting cleanup can also leave temporary state behind.

## Accomplished behavior

`run_qemu.sh` now:

- captures the host result before cleanup;
- separates ordinary EXIT cleanup from explicit INT and TERM cleanup;
- preserves host failure ahead of guest, signal, and cleanup outcomes;
- treats completed nonzero, malformed, unreadable, or missing guest status as failure 1 when the host succeeded;
- retains the first INT or TERM received during ordinary cleanup;
- disables overlapping INT/TERM handling in each signal trap action before entering the handler;
- marks ordinary cleanup in the same assignment-only command that captures `$?`;
- prevents an early cleanup signal from bypassing completed guest precedence;
- prevents a second explicit signal from replacing the first during handler entry;
- retains the first cleanup failure while later cleanup actions continue;
- runs cleanup once and supports an immediate clean rerun.

## Exact identities

| Identity | Value |
| --- | --- |
| Canonical repository | `https://salsa.debian.org/debian/mmdebstrap.git` |
| Intended canonical branch | `master` |
| Controlled mirror | `https://github.com/teamleaderleo/mmdebstrap` |
| Controlled base | `574048f2a720057b75e56622003932f344dc700a` |
| Base `run_qemu.sh` blob | `426aeeb854173569b24e64d6eb85019f45bdf0b6` |
| Candidate branch | `linux-fieldwork/unit-05-run-qemu-result-precedence` |
| Candidate head | `6efe6945f9f89cff57fe84086ede7bda747c3879` |
| Candidate `run_qemu.sh` blob | `1fc816d6fe982351f6519fd1458329112eebdcfb` |
| Candidate SHA-256 | `434e7b6b9c32e30b506ea6af121608414c42b668c329e6395e75e19dc09ff276` |
| Candidate size | 3,095 bytes |
| Linux Fieldwork branch | `upstream/unit-05-run-qemu-result-precedence` |
| Delivery method | Salsa merge request after explicit authorization |

## Candidate commits

1. `614fb26a4f0724618a5eecd3ce1bee12454ff7de` — preserve primary result through cleanup.
2. `cb6ef6d6c2b1368b3603b2ec06635c3815f31e11` — retain the first handled signal through cleanup.
3. `13cf34fd87d44b4d37c6767fdbd153b2ef535a57` — retain signals during ordinary EXIT cleanup.
4. `457095c6f89655ab12b7055307f519e71bb0dbca` — preserve completed guest failure before cleanup signal.
5. `6efe6945f9f89cff57fe84086ede7bda747c3879` — close explicit-signal and ordinary-EXIT handler setup windows.

Compare against controlled `master`: five commits ahead, zero behind, one modified file, 64 additions, and 10 deletions.

## Demonstrated

- The controlled base file is exactly the imported Linux Fieldwork source blob.
- Patches 1–4 apply without fuzz or offsets; patch 5 is retained as the complete-diff repair.
- `/bin/sh -n` succeeds on the exact fifth-commit source.
- The established controlled-fork lifecycle matrix passes 58/58 checks.
- Four predecessor policies retain deterministic losing controls.
- Four-commit candidate setup windows lose first-signal and completed-guest precedence.
- Fifth-commit widened controls return 143, 1, and 143 as required while cleanup completes.
- Immediate rerun remains clean in the reduced `/bin/sh` fixtures.

Receipts:

- [`artifacts/2026-08-01-controlled-fork-lifecycle-matrix.txt`](artifacts/2026-08-01-controlled-fork-lifecycle-matrix.txt)
- [`artifacts/2026-08-01-handler-setup-window-repair.txt`](artifacts/2026-08-01-handler-setup-window-repair.txt)

## Scope

Included: `run_qemu.sh` result selection, handler transitions, once-only bounded cleanup, first-writer signal retention, exact fork commits, reduced lifecycle fixtures, cleanup, and rerun.

Excluded: QEMU command construction, timeout duration, HUP/QUIT policy, process-group escalation, guest-image content, networking, mounts, package installation, and public upstream contact.

## HOLD gates

1. Resolve current canonical Salsa `master` and `run_qemu.sh` identities and search current issues, branches, and merge requests for equivalent work.
2. Rebase when required and run current mmdebstrap QEMU-classified focused/ordinary tests through `coverage.py` or `coverage.sh` on the exact candidate head.
3. Execute the checked-in `tests/test_run_qemu_handler_setup_windows.py` from a complete Linux Fieldwork checkout or hosted CI and retain its exact run identity.
4. Refresh the final draft after those gates and rerun cleanup and focused controls on the exact resulting head.

## Next human decision

No publication decision is requested yet. After the HOLD gates, choose authorization, further hold, split, or retirement if canonical upstream already contains equivalent work.

## Authority

Internal reads, branches, commits, reduced tests, packet updates, and issue checkpoints are authorized. No upstream issue, merge request, comment, review, email, or mailing-list message has been authorized or created.
