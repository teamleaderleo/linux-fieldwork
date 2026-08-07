# uutils `cp`: preserve opened identity across clone fallback

## TL;DR

The Linux clone path opens the source and destination, attempts `FICLONE`, then—if the ioctl fails—drops those descriptors and falls back by reopening the source and destination pathnames.

That creates a checked/opened-object versus fallback-object split. A concurrent rename or replacement can make the fallback copy from or into objects different from the descriptors used for the clone attempt.

A correct repair must make every fallback operate on the already-open source and destination handles, with explicit offset/truncation preparation for each copy strategy.

## Explain like I'm five

`cp` opens two files and tries the fast copying method. If that method says no, `cp` currently closes the files and asks the directory names for them again. Someone can swap what those names point to between the two attempts.

The repair should say: “The fast method failed, so use the slower method on the same two open files.”

## Why care

The current fallback can copy data from a replacement source or overwrite a replacement destination. This is most relevant in attacker-writable or concurrently modified directories and undermines the safe-open work already present in `uucore::safe_copy`.

## Current state

- State: `SCOPING`
- Canonical source reviewed: `uutils/coreutils@21d4e9635b07a04f262cd8a5386f2987bca6cfef`
- Issue: `#13185`
- Matching canonical PR found: none at the recorded search boundary
- Controlled source candidate: none
- Related active work:
  - controlled sparse early-EOF candidate `teamleaderleo/coreutils#4`;
  - canonical early-EOF PR `uutils/coreutils#12649`.
- External-contact state: no canonical-upstream contact authorized or made

## Baseline source path

`clone()` currently:

1. opens the source with `open_source()`;
2. creates/opens the destination with `create_dest_restrictive()`;
3. passes both `File` values by value to `ioctl_ficlone()`;
4. on ioctl failure, calls path-based `fs_copy()`, `sparse_copy()`, or `sparse_copy_without_hole()`.

The generic ioctl call only needs borrowed descriptors, but passing owned values causes them to be dropped before the fallback branch. The fallback helpers then repeat path resolution and opening.

## Required design

### Retain the handles

Pass borrowed descriptors to `ioctl_ficlone()` and retain mutable source/destination `File` values for fallback.

### Prepare each fallback explicitly

The fallback cannot simply call the current path helpers. It must define the starting state of the retained descriptors:

- source offset reset to zero when a prior operation may have moved it;
- destination offset reset to zero;
- destination truncation/pre-sizing appropriate to the selected strategy;
- sparse-copy size snapshot obtained from the opened source descriptor;
- FIFO/device/stream handling kept outside assumptions that require a regular seekable file.

### Preserve error context

Errors should retain the existing source/destination context and should not silently switch back to path-based helpers after a descriptor operation fails.

## Deterministic test direction

A useful helper-level test should avoid racing the scheduler:

1. create source A and destination A;
2. open both through the production safe-open path;
3. rename those pathnames away and install source B/destination B at the original names;
4. force the clone operation into a selected fallback;
5. assert that the fallback reads source A and writes destination A through the retained descriptors;
6. assert source B/destination B remain untouched.

The production ioctl failure can be represented by a helper that accepts the fallback decision after the descriptors are open, rather than syscall interposition.

## Interaction with sparse early EOF

The sparse-copy helper from issue #12648 is useful only if it accepts the retained source and destination descriptors. The two changes should be designed to compose, but should remain independently reviewable:

- early EOF owns destination-size correction;
- clone fallback owns descriptor identity.

## Stop signal

Do not write the source candidate until:

- all four fallback modes have explicit descriptor starting-state contracts;
- destination truncation semantics after a failed clone are black-box checked;
- the helper-level identity test is deterministic;
- interaction with streams and special files is mapped;
- the diff can avoid duplicating the sparse-copy loop.

## Interpretation

The operation owner is the opened file descriptor pair. A pathname is suitable for diagnostics, but once safe opening has succeeded it should not be used to choose a different object for the actual fallback copy.

## Authority

No canonical-upstream issue comment, pull request, review, email, patch submission, or other contact has been authorized or made.
