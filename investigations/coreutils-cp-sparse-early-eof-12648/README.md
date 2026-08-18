# uutils `cp --sparse=always`: early EOF after source truncation

## TL;DR

The Linux/Android sparse-copy loop captures the source's metadata size, pre-sizes the destination, and advances only by bytes returned from `read()`. If the source shrinks and `read()` returns zero before the captured size, the loop never advances and spins forever.

A correct repair must do two things: stop on EOF and shrink the destination from the stale metadata size to the number of bytes actually read. A controlled candidate extracts the loop into a testable helper and adds a deterministic early-EOF unit test.

## Explain like I'm five

The copier is told, “this file is 2 GB long,” so it makes a 2 GB destination. While it is copying, someone cuts the source shorter. The copier asks for more bytes and gets none, but it keeps asking forever because it still believes it must reach 2 GB.

The repair says: “No more bytes means the source ended. Resize the destination to how far we actually got, then stop.”

## Why care

The current behavior can pin a CPU indefinitely and leave a command that never completes. A naive break-only fix would stop the CPU spin but leave a destination with a stale trailing sparse region at the old size.

## Current state

- State: `EXECUTING`
- Canonical source head: `uutils/coreutils@a0cb02453f314bdd3addda6f321f7e03adceb56b`
- Controlled source branch: `teamleaderleo/coreutils:fieldwork/cp-sparse-early-eof-12648`
- Controlled staged head: `e33584c9ad932b6c602ddac3674ab0d2bf940e85`
- Controlled draft PR: `teamleaderleo/coreutils#4`
- First incomplete step: inspect the PR-visible `Fieldwork cp sparse early EOF` workflow
- Cleanup state: transformer and workflow remain until a green push-side promotion
- Next safe action: classify the first failing workflow step, or inspect the source-only promoted head if green
- External-contact state: no canonical-upstream contact authorized or made

## Intent and precedent

uutils aims to be a reliable drop-in replacement for current GNU coreutils, remain cross-platform, avoid unexpected failure, and require regression tests, rustfmt, and clippy-clean code.

The affected path is specifically the Linux/Android `--sparse=always` implementation. It pre-sizes the destination so zero blocks can remain holes, then writes only blocks containing non-zero bytes.

## Question

When a regular source reaches EOF before the metadata size captured at the beginning of a sparse copy, what destination size and termination behavior should uutils produce?

## Source

- Project: uutils/coreutils
- Issue: `#12648`
- Requested revision: canonical `main`
- Resolved commit: `a0cb02453f314bdd3addda6f321f7e03adceb56b`
- Controlled comparison base: `teamleaderleo/coreutils:base/canonical-main-20260804`
- Controlled candidate branch: `fieldwork/cp-sparse-early-eof-12648`
- Candidate source commit: pending promotion
- Imported source: none; exact Git identities are the source boundary

## Environment

- GNU oracle: GNU coreutils 9.7
- Probe host: Linux, x86_64
- Shell: bash
- Candidate execution: GitHub Actions Ubuntu 24.04
- Candidate platforms directly affected by source selection: Linux and Android

## Baseline behavior

Current code records `size`, calls `ftruncate(destination, size)`, and loops while `current_offset < size`. A zero-byte read produces an empty slice, writes nothing, and adds zero to `current_offset`, so the condition remains true forever.

## GNU behavior receipt

Five black-box runs used a 2 GiB source with 64 MiB of initial data, a background truncation to zero, and GNU `cp --reflink=never --sparse=always`.

Observed destination sizes were approximately 3–12 MiB depending on how far copying progressed before truncation. Every run exited successfully. The destination was neither left at the original 2 GiB size nor forced to the source's eventual zero size; it ended at the amount read before EOF.

Representative command:

```sh
truncate -s 2G src
dd if=/dev/urandom of=src bs=1M count=64 conv=notrunc status=none
(sleep 0.01; truncate -s 0 src) &
cp --reflink=never --sparse=always src dst
stat -c %s dst
```

## Candidate

Extract the sparse data loop into a private helper with:

- a generic `Read` source;
- a real destination `File` for positional writes and truncation;
- a `u64` size snapshot and current offset;
- the existing sparse zero-block behavior.

When `read()` returns zero before the snapshot:

1. truncate the destination to `current_offset`;
2. break the loop;
3. return success.

## Deterministic test

Use a short in-memory reader but pass a declared size 4096 bytes larger. Pre-size a real temporary destination to the declared size. After the helper returns, assert:

- destination length equals the actual input length;
- destination content equals the input;
- no stale trailing pre-sized region remains.

This directly tests the missing transition without a timed race.

## Results

The candidate is staged behind a fail-closed single-occurrence transformer. No product result is claimed until the hosted gate completes.

The controlled gate requires:

- transformation and rustfmt with a one-file fence;
- deterministic helper unit test;
- complete `test_cp` integration module;
- focused clippy;
- source-only promotion.

## Interpretation

Early EOF is not merely a loop termination event. Because sparse copying pre-commits a destination length, EOF also invalidates that pre-sized tail. The destination must be contracted to the copy's actual progress.

## Evidence boundary

The GNU probe is a race and therefore produced varying copied lengths, but the invariant was stable across runs: successful termination and destination length equal to progress before EOF. The deterministic candidate test exercises the internal transition rather than the OS scheduling race. Android runtime behavior is not independently executed at this checkpoint.

## Next step

Inspect the controlled workflow. If green, verify the promoted branch contains only `src/uu/cp/src/platform/linux.rs`, review the complete final diff, compare against current canonical main, and update this record with the final source blob and run receipt.

## Authority

No canonical-upstream issue comment, pull request, review, email, patch submission, or other contact has been authorized or made.