# Shell cleanup re-entry audit

Date: 2026-07-31  
Tracking: issue #271  
Owner: Helper F adjacent research  
External contact authorized: `false`

## TL;DR

Two Linux Fieldwork TMPDIR harnesses installed the same cleanup function for `EXIT`, `INT`, and `TERM`:

```bash
trap cleanup EXIT INT TERM
```

A signal handler that only cleans and returns does not terminate the script. A parent-only signal can therefore run cleanup, continue into later work, and invoke cleanup a second time through `EXIT`.

The candidate gives ordinary exit and signals separate handlers. It clears all related traps before cleanup, preserves an existing primary failure over cleanup failure, reports cleanup failure after ordinary success, and terminates INT/TERM as 130/143.

## Explain like I'm five

The stop alarm told the worker to clean the room, but it never told the worker to stop. The worker cleaned, kept working, and cleaned the room again while leaving.

The repair turns the alarm into: remember why we are stopping, switch off the duplicate alarm, clean once, and leave with the right result.

## Why care

These are repository-owned evidence harnesses. Wrong signal handling can make an interrupted run appear successful, execute later assertions or writes after cancellation, repeat recursive cleanup, or replace the first useful failure with a cleanup result.

The candidate changes no imported mmdebstrap product source. It repairs the evidence-producing scripts that own their disposable runtime directories.

## Exact source boundary

Baseline source on `main` before this candidate:

- `investigations/mmdebstrap-unwritable-tmpdir/run.sh`, blob `b7eed613f9aa05d953598a208ced9b6af2f4e0f8`;
- `investigations/mmdebstrap-unwritable-tmpdir/deep_review.sh`, blob `edc12be9ba3cf6475e387aa48574b91633cdbbd2`.

Both scripts used Bash strict mode, a cleanup function ending in recursive removal of their fixed runtime directory, and one cleanup-only `EXIT INT TERM` trap.

Related already-owned findings remain separate:

- issue #231 / PR #267 owns `make_mirror.sh` `update_cache()` process and proxy ownership;
- issue #269 / PR #270 owns `run_qemu.sh` result precedence and cleanup;
- issue #170 and its composed QEMU-builder work own imported image-builder signal lifecycle;
- issue #130 / PR #250 owns chrootless-environment harness path authority and imported-source mode preservation.

## Baseline behavior

The executable reduction uses a disposable event log and a cleanup function that only records `cleanup`.

Baseline lifecycle:

```bash
trap cleanup EXIT INT TERM
kill -TERM "$$"
printf 'later\n' >>"$log"
exit 0
```

Observed contract expected from the baseline model:

```text
status: 0
events: cleanup, later, cleanup
```

The TERM handler returns, later work runs, and EXIT invokes cleanup again.

## Candidate

Both harnesses now use:

```bash
finish() {
  local primary_status=$1 cleanup_status=0
  trap - EXIT INT TERM
  cleanup || cleanup_status=$?
  if [[ $primary_status -ne 0 ]]; then
    exit "$primary_status"
  fi
  exit "$cleanup_status"
}

exit_cleanup() {
  finish "$?"
}

trap exit_cleanup EXIT
trap 'finish 130' INT
trap 'finish 143' TERM
```

The precedence rule is:

```text
primary failure or signal > cleanup failure > success
```

This keeps a primary status such as 42 authoritative even when cleanup returns 74. When ordinary work succeeds and cleanup returns 74, the script reports 74 rather than false success. INT and TERM remain 130 and 143 regardless of cleanup failure.

## Executable regression

`tests/test_unwritable_tmpdir_signal_cleanup.py` checks:

- both exact repository scripts contain the reviewed lifecycle block once;
- the old cleanup-only trap falls through, runs later work, and cleans twice;
- primary 42 remains authoritative over cleanup 74;
- ordinary success surfaces cleanup 74;
- INT/TERM terminate as 130/143, clean once, and omit later work;
- an immediate clean rerun succeeds and cleans once;
- both complete scripts pass `bash -n`.

The model uses only temporary files and self-signals its own short-lived Bash process. It does not run mmdebstrap, touch mounts, use network access, contact a public target, or signal unrelated processes.

## Interpretation

This is the additional controlled true positive required by issue #271 beyond the two earlier review repairs. The defect belongs to Linux Fieldwork harness lifecycle, not to the TMPDIR product behavior being measured.

The repeated pattern supports one reusable rule:

> A signal trap that performs cleanup must clear overlapping traps and terminate with the signal-derived status. An EXIT trap must capture the primary status before cleanup and define cleanup-failure precedence.

## Evidence boundary

The focused regression models the exact trap and status logic while replacing recursive removal with an event counter. Full TMPDIR package runs remain governed by their existing hosted workflows. Bash signal delivery can be deferred while a foreground command runs; the repair controls what happens when the handler runs, not kernel or foreground-child delivery latency.

The candidate does not add HUP or QUIT handling, change the runtime paths, alter product assertions, or claim that every lexical trap match is defective.

## Cleanup and rerun

Every regression case creates its own temporary directory and process. The self-signaled process terminates before the temporary directory is removed. The final case runs a signaled candidate followed immediately by a successful candidate and requires one cleanup event in each run.

## Disposition

Execute exact-head repository CI, inspect the complete four-file diff, and then choose `MERGE LOCALLY` if the matrix passes unchanged.

No Debian or external upstream issue, email, patch, merge request, comment, or review is authorized or made by this record.
