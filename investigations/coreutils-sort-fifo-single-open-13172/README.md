# uutils `sort`: preserve one stream session without losing preflight

## TL;DR

The named-FIFO hang is not an unterminated-line parser bug. `sort` opens each named input for validation, drops the handle, and later opens it again for real sorting. For a FIFO, the first open owns the writer session; dropping it discards unread bytes and the real pass waits for another writer.

A first controlled candidate skipped preflight when pathname metadata identified a FIFO. That fixes the headline behavior but is now **held**: pathname metadata is not the right owner for descriptor lifetime and can race with replacement.

The stronger design must open nonblocking, classify seekability from the opened handle, retain only non-seekable readers, clear nonblocking mode before consumption, and close/reopen ordinary files.

## Explain like I'm five

A writer brings one envelope to a pipe. `sort` sends a temporary reader first, accepts the envelope, throws it away, and leaves. The real reader then waits forever.

The correct reader should be opened once and kept. But ordinary books should still be checked and closed so `sort` does not run out of file handles.

## Why care

The current behavior loses a real writer session and can hang indefinitely. A careless repair can introduce two other regressions:

- block on an early FIFO before discovering a later missing file;
- retain every ordinary input descriptor and reach `EMFILE` on large argument lists.

## Current state

- State: `HOLD / REDESIGN`
- Issue: `uutils/coreutils#13172`
- Canonical source base originally inspected: `89bdbb86627670afb6794f762bed5bd94372f331`
- Current fork main: `21d4e9635b07a04f262cd8a5386f2987bca6cfef`
- Controlled held branch: `teamleaderleo/coreutils:fieldwork/sort-fifo-single-open-13172`
- Controlled draft PR: `teamleaderleo/coreutils#6`
- Canonical overlapping PR: `uutils/coreutils#13494`
- Source promotion: disabled
- External-contact state: no canonical-upstream contact authorized or made

## Baseline operation

```text
for every named input:
    open input
    drop handle

later:
    open input again
    read and sort
```

For a FIFO, opening is a synchronization and consumption boundary, not a harmless availability check.

## GNU 9.7 behavior receipt

Black-box probes establish:

- one FIFO writer sending `hello` without a newline produces `hello\n`;
- regular file plus FIFO is sorted together;
- two FIFO operands use one writer session each;
- normal and merge modes report a later missing ordinary input before waiting on a FIFO, even when the FIFO is listed first;
- check mode rejects extra operands before input consumption.

Deleting preflight entirely is therefore not compatible.

## First candidate and why it is held

The staged candidate uses `metadata(path).file_type().is_fifo()` to skip the disposable open only for FIFOs.

Focused tests cover the headline FIFO case and missing-file ordering. However:

- the path can change between metadata and the real open;
- file type is inferred from a pathname rather than behavior of the opened object;
- non-FIFO non-seekable inputs remain outside the model;
- symlink and replacement behavior depends on two separate path resolutions.

The workflow is read-only and cannot promote this implementation.

## Review of canonical PR #13494

That PR moves toward handle-based detection by seeking the opened reader and retaining non-seekable handles. This is directionally better than path metadata.

The reviewed revision still raises two concrete concerns:

1. **Error ordering:** it disables ordinary preflight in normal and merge paths, so `sort FIFO missing` appears to wait for the FIFO rather than report the missing operand first.
2. **Descriptor budget:** it retains every opened ordinary input, potentially undoing the original reason for close-and-reopen and reaching `EMFILE` under a low descriptor limit.

Read-only exact-head workflows were added to test both claims rather than relying solely on diff inspection.

## Stronger candidate direction

### Preparation phase

For every named Unix input:

1. open with `O_NONBLOCK` so a FIFO without a writer does not stall validation;
2. attempt a descriptor operation such as `seek(Current(0))` to determine seekability;
3. if seekable, close the descriptor and retain the pathname for later reopen;
4. if non-seekable (`ESPIPE`), retain that exact descriptor;
5. clear `O_NONBLOCK` on retained streams before the read phase;
6. propagate all ordinary open errors before reading any stream.

### Execution phase

Carry a prepared-input abstraction through:

- normal external sort;
- merge mode;
- check mode.

A prepared input is either:

- a pathname that can be safely reopened; or
- an already-open non-seekable reader that must be consumed exactly once.

### Platform precedent

`sync` already uses nonblocking open followed by flag reset, giving an in-tree precedent for avoiding blocking during setup without leaving the descriptor nonblocking for the operation itself.

## Required tests

1. one-writer unterminated FIFO in normal mode;
2. the same in merge mode;
3. two independent FIFOs;
4. FIFO first plus missing ordinary file in normal and merge modes;
5. many regular inputs under low `RLIMIT_NOFILE` still succeed;
6. symlink resolving to FIFO consumes one retained descriptor;
7. path replacement after preparation does not redirect a retained stream;
8. complete sort integration module, rustfmt, and clippy.

## Stop signal

Do not promote a source patch until normal, merge, and check paths share the prepared-reader abstraction and both error-ordering and descriptor-budget controls pass.

## Authority

No canonical-upstream issue comment, pull request, review, email, patch submission, or other contact has been authorized or made.
