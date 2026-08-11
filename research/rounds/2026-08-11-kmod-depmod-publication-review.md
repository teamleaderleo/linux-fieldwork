# 2026-08-11 kmod depmod publication review

## TL;DR

A current-source pass over `kmod-project/kmod` found that `depmod` detects stream finalization failure but publishes the temporary index before checking that error. A disposable local probe on kmod 34.2 confirmed the prior index is replaced and the command then exits with failure.

History prevents promoting this as a new tmpfile regression: the 2012 ENOSPC fix deliberately added error reporting while retaining publication order, and the 2025 tmpfile-helper refactor preserved it. Detailed evidence is in [`../../investigations/kmod-depmod-truncated-index-publication/README.md`](../../investigations/kmod-depmod-truncated-index-publication/README.md).

## Selection reason

The source initially matched several high-value lenses:

- temporary output plus rename publication;
- write/close failure near publication;
- retained prior artifact versus failed replacement;
- a recent 2025 temporary-file implementation change.

The history pass was decisive because it tested whether the apparent defect was actually introduced by the modern helper.

## Exact source

- Repository: `kmod-project/kmod`
- Revision: `65ac890492c96b88d10d8c92342a1b00ff603dba`
- Primary file: `tools/depmod.c`
- Helper: `shared/tmpfile.c`
- Tests: `testsuite/test-depmod.c`
- Historical anchors:
  - 2012 `a4fb97a71e336394e1a497c2b75ea42907937d1e`
  - 2025 `aae48bc9f73a1bce726871027f73cbc0543c65d4`

## Distinguishing result

Current source does:

```text
write -> ferror/fclose -> publish -> inspect finalization error
```

The local close-error model produced:

```text
old modules.dep sentinel -> close reports EIO -> temp published -> depmod exits 1
```

But the same publication-before-error-check sequence existed before the 2025 helper and survives from the old ENOSPC error-reporting design.

## Disposition

Retain a negative result for the claim that modern tmpfile work accidentally introduced this behavior.

A separate successor could ask whether 2026 kmod should prefer retaining a stale previous index over publishing a truncated new generation after a failed `depmod`. That is a consumer/failure-policy question and should not be smuggled into this source review as an obvious fix.

## External-contact state

Not authorized; none performed.
