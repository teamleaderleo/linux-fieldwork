# uutils `sort`: a FIFO must not be opened by a disposable preflight pass

## TL;DR

The named-FIFO hang is not an unterminated-line parsing defect. `sort` first opens every named input to validate it, drops those handles, and later reopens the inputs for real sorting. For a FIFO, that first open is the reader session the writer connects to. Its unread bytes are discarded when the temporary handle closes, and the real pass blocks waiting for another writer.

The controlled candidate retains preflight for ordinary inputs so missing-file errors still appear before any stream wait, but skips FIFO preflight on Unix and opens each FIFO only for actual consumption.

## Explain like I'm five

A writer brings one envelope to a pipe. `sort` sends a fake reader to the pipe first, accepts the envelope, throws it away unopened, and leaves. Then the real reader arrives and waits forever for a second envelope.

The repair removes only the fake FIFO reader. Ordinary files still get checked in advance.

## Why care

A normal one-writer FIFO session can hang indefinitely and lose the data already delivered. This affects named-pipe workflows even though the same unterminated input works correctly over stdin.

## Current state

- State: `EXECUTING`
- Canonical source base: `uutils/coreutils@89bdbb86627670afb6794f762bed5bd94372f331`
- Controlled source branch: `teamleaderleo/coreutils:fieldwork/sort-fifo-single-open-13172`
- Controlled staged head: `2f3d1d56a0f5a242bad0bc32fadc905617f1e592`
- Controlled draft PR: `teamleaderleo/coreutils#6`
- First incomplete step: inspect the focused hosted workflow
- Cleanup state: transformer and workflow remain until green promotion
- Next safe action: classify the first failed step or review the source-only promoted head
- External-contact state: no canonical-upstream contact authorized or made

## Intent and history

Current source deliberately validates every input, closes it, and reopens later, with a comment that this prevents exhausting file descriptors. That policy is reasonable for ordinary files but assumes opening is observational and repeatable.

FIFO opening is neither. A blocking read-only open synchronizes with a writer, and the resulting handle owns that writer session. Dropping it without reading is observable data loss.

## Question

Can `sort` preserve early diagnostics for ordinary inputs while ensuring each named FIFO is opened only by the pass that will consume it?

## Source

- Project: uutils/coreutils
- Issue: `#13172`
- Resolved canonical commit: `89bdbb86627670afb6794f762bed5bd94372f331`
- Controlled comparison base: `teamleaderleo/coreutils:base/canonical-main-20260804c`
- Controlled candidate: `fieldwork/sort-fifo-single-open-13172`
- Candidate source commit: pending promotion
- Imported source: none; exact Git identities are the source boundary

## Baseline path

In `uumain()`:

```text
for each named input:
    open(input)
    drop handle

exec():
    map open(input) again
    read and sort
```

For a FIFO:

```text
preflight open blocks until writer
writer writes and closes
preflight handle drops unread bytes
real open blocks waiting for another writer
```

## GNU 9.7 behavior receipt

Black-box probes establish:

- one FIFO writer sending `hello` without a newline produces `hello\n` and exits successfully;
- regular file plus FIFO is sorted together;
- two FIFO operands are consumed with one writer session each;
- a missing ordinary operand is reported before waiting on a FIFO, even when the FIFO is listed first.

The last result means deleting all preflight opens would be an incomplete compatibility repair.

## Candidate

Add `should_preflight_input(path)`:

- stdin remains preflightable;
- on non-Unix, behavior is unchanged;
- on Unix, `metadata()` identifies a FIFO, including a symlink resolving to a FIFO;
- only FIFOs skip the availability-open loop;
- missing paths still enter the existing open path and preserve the missing-file diagnostic;
- the actual sorting, merge, and check readers remain unchanged.

## Tests

### FIFO session test

1. Create a FIFO.
2. Spawn one writer thread.
3. Write `hello` without a newline and close.
4. Run `sort` with a five-second harness timeout.
5. Require successful `hello\n` output.

### Preflight-order test

1. Create a FIFO but no writer.
2. Invoke `sort FIFO missing` with a two-second harness timeout.
3. Require the missing-file diagnostic and exit code 2.

This test proves ordinary preflight remains ahead of FIFO consumption regardless of argument order.

## Results

The candidate is staged behind a fail-closed exact transformer and a two-file fence. No product result is claimed until the hosted gate completes.

## Interpretation

The operation owner is the FIFO reader session, not merely the pathname. Availability checking is safe only when opening and dropping a handle has no externally visible consumption or synchronization effect.

The minimal fix does not redesign the input iterator. It exempts the one file type for which the existing validation strategy destroys the real read session.

## Evidence boundary

The candidate currently targets Unix FIFO semantics. Windows named pipes are outside this change. Devices and sockets retain existing preflight behavior. The integration test uses real FIFO synchronization and a bounded timeout; it does not rely on a sleep to make the writer race the reader.

## Next step

Inspect the focused gate. If green, verify promotion leaves only `src/uu/sort/src/sort.rs` and `tests/by-util/test_sort.rs`, review every changed line, compare against current canonical main, and update this record with exact blobs and receipts.

## Authority

No canonical-upstream issue comment, pull request, review, email, patch submission, or other contact has been authorized or made.