# mmdebstrap-autopkgtest-build-qemu signal exit semantics

## In simple words

The QEMU image builder used one cleanup-only shell trap for ordinary exit and for `INT`, `TERM`, and `QUIT`. A parent-only cancellation signal could remove the temporary work directory and then resume later image construction instead of terminating.

This candidate preserves the existing normal EXIT cleanup and gives each signal a terminating action with the conventional status.

## Canonical records

- Issue: #170
- Focused candidate: PR #172
- Integration candidate: issue #193 / PR #195
- Imported source: `upstream/mmdebstrap/mmdebstrap-autopkgtest-build-qemu`
- Candidate patch: `0001-preserve-signal-exit-status.patch`
- Regression: `tests/test_qemu_builder_signal_exit.py`

## Source boundary

The imported helper contains:

```sh
cleanup() {
  test -n "$WORKDIR" && rm -Rf "$WORKDIR"
}

trap cleanup EXIT INT TERM QUIT
```

The script then performs a long `mmdebstrap | mke2fs` pipeline, EFI section construction, partition/image mutation, and final metadata work.

A shell trap returns to interrupted control flow unless it exits or re-raises. With parent-PID-only delivery while the shell waits for a foreground command, the trap can be deferred until that command returns. Cleanup then removes `WORKDIR`, returns, and the shell continues.

## Candidate

```sh
signal_exit() {
  status=$1
  trap - EXIT INT TERM QUIT
  cleanup || :
  exit "$status"
}

trap cleanup EXIT
trap 'signal_exit 130' INT
trap 'signal_exit 131' QUIT
trap 'signal_exit 143' TERM
```

Normal EXIT cleanup is unchanged. Signal cleanup ignores its own error only in the signal path so a removal failure cannot replace the cancellation status. Clearing traps prevents the EXIT action from running cleanup a second time.

## Negative and candidate matrix

The regression applies the patch to an exact temporary source copy and checks `sh -n`. It extracts the exact cleanup/trap lifecycle into a reduced real `/bin/sh` harness whose `WORKDIR` is disposable.

A parent-PID-only SIGTERM is delivered while the shell waits for a foreground child:

- baseline: the work directory is removed, the later marker executes, and the wrapper exits 0;
- candidate: the work directory is removed, the later marker is absent, and the wrapper exits 143.

An unsignaled candidate rerun must execute the later marker, exit 0, and remove the work directory through the ordinary EXIT trap.

Source assertions require distinct EXIT, INT, QUIT, and TERM actions plus trap clearing and cleanup-error containment.

## Execution record

The first retained patch declared a `6 -> 18` hunk while containing 16 candidate lines. Linux Fieldwork CI run `30555056090` therefore failed all three focused tests during patch parsing with `malformed patch at line 21`. That run is patch-packaging evidence; no signal scenario executed.

Helper C corrected the hunk count without changing product semantics. Exact code-and-patch head `22690dd6b4f0cfe0cbf8714b44c671b40e4f1848` passed Linux Fieldwork CI run `30577643383`.

The broader final-check unit is PR #195. It composes this mechanism with private atomic image publication, adds HUP status 129, makes cleanup-failure precedence explicit, preserves existing final output, and tests signals before and after publication.

## Cleanup and safety

The dynamic harness uses only `sleep`, marker files, and a work directory below `TemporaryDirectory`. It signals only a wrapper subprocess it created and waits for it. No root filesystem, image, mount, package mutation, QEMU process, external network, or persistent output is created.

## Evidence boundary

The repair preserves cancellation status after the foreground operation returns. It does not make parent-only cancellation prompt or forward signals into `mmdebstrap`, `mke2fs`, `objcopy`, or other foreground commands.

The script's output image is outside `WORKDIR`; this focused candidate alone does not preserve a caller-selected IMAGE on failure. PR #195 owns that composition boundary.

## Disposition

**READY FOR FINAL HUMAN CHECK as a focused mechanism record.** Use PR #195 as the canonical combined landing candidate. No Debian or external upstream contact is included or authorized.
