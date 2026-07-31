# libarchive 7-Zip non-seekable stream overlap review

## TL;DR

Current libarchive master can list a small ordinary 7-Zip archive through every tested non-seekable transport, but extraction fails with `Seek error` through every tested non-seekable transport. The same archive extracts successfully from a regular seekable file.

Open upstream PR 3070 proposes making the 7-Zip bidder abstain whenever the input lacks seek capability and expects raw format to win. The executed matrix shows that rule is too broad as a general capability statement: it would discard currently working non-seekable listing together with failing extraction.

Independent product implementation remains stopped because PR 3070 already owns the proposed change. The useful contribution here is the operation-specific compatibility result and the resulting review questions.

## Explain like I'm five

The reader can walk forward through this package far enough to read the table of contents. To take a file out, it then needs to walk backward, which a pipe cannot do.

An open patch proposes refusing the package as soon as it arrives through any one-way delivery method. That avoids the later extraction failure, but it also throws away the table-of-contents operation that already works.

## Why care

libarchive is a shared parser behind archive tools, package systems, backups, and language runtimes. Format identity, listing, extraction, fallback, and diagnostics are separate compatibility surfaces. A single bidder rule can improve one while regressing another.

## Current state

- State: `COMPLETE OVERLAP REVIEW — PRODUCT IMPLEMENTATION RETIRED`
- Linux Fieldwork issue: #230
- Controlled fork PR: `teamleaderleo/libarchive` #1
- Exact probe head: `0ff0fe951b3bfe264875d0b4bf1e0dcc23088edd`
- Focused run: `30599140008`
- Focused job: `91057873783`
- Artifact: `nonseekable-7zip-probe-30599140008-1`
- Artifact ID: `8782133075`
- Artifact ZIP SHA-256: `6308f13935fc3ef8fee7ab0734faf8d2a43360b20f883249e1b766155456c29e`
- Cleanup state: disposable runner and PID-specific fixture directory removed by trap
- External-contact state: unauthorized and not made

## Source and overlap

- Public issue: https://github.com/libarchive/libarchive/issues/3068
- Active public PR: https://github.com/libarchive/libarchive/pull/3070
- Active PR head checked: `c79a8b8a221022ebc5b23accdb06bc14923c4082`
- Merged streamability repair: https://github.com/libarchive/libarchive/pull/3074
- Merged repair commit: `531d70f88cb0ba6a44f3f72995c42ac5188f58ca`

The controlled fork changes evidence workflow and probe scripts only. It does not modify libarchive product source.

## Historical source transition

Issue discussion identifies PR 2985 as the regression point where SFX data-offset detection and central-directory slurping were merged around an unconditional seek.

Merged PR 3074 changed:

```diff
-if (__archive_read_seek(a, data_offset, SEEK_SET) < 0)
+if (__archive_read_consume(a, data_offset) < 0)
```

Current `seek_compat()` follows the same boundary:

- use real seek when the filter supports it;
- convert forward `SEEK_CUR` and forward `SEEK_SET` into byte consumption when compatibility mode is enabled;
- reject backward movement on non-seekable input.

The phrase “7-Zip requires seeking” is therefore incomplete. Some layouts and operations are forward-readable; later payload access can still require a backward move.

## Executed matrix

The probe generated one small 7-Zip archive containing `payload.txt` with bytes `fieldwork payload`, plus a gzip-wrapped copy.

```text
case                                status  observed result
regular 7-Zip list                  0       payload.txt
direct 7-Zip stdin pipe list        0       payload.txt
gzip-wrapped file list              0       payload.txt
gzip-wrapped stdin pipe list        0       payload.txt
external gzip → 7-Zip pipe list      0       payload.txt

regular 7-Zip extract               0       fieldwork payload
direct 7-Zip stdin pipe extract     1       Seek error
gzip-wrapped file extract           1       Seek error
gzip-wrapped stdin pipe extract     1       Seek error
external gzip → 7-Zip pipe extract   1       Seek error
```

This is the distinguishing result:

```text
same archive + same parser + non-seekable transport
listing: succeeds
extraction: fails when backward access becomes necessary
```

## Proposal review

Open PR 3070 changes four related boundaries:

1. initial filter `can_seek` derives from whether a client seeker exists;
2. `archive_read_open_fd()` installs the default seeker only for regular files;
3. the 7-Zip bidder returns zero whenever `a->filter->can_seek == 0`;
4. a pipe test expects 7-Zip to abstain and raw format to win.

### Opinion

The proposal identifies a real late-failure problem, but the bidder condition is too coarse for the behavior now demonstrated.

A blanket `can_seek == 0` rejection would likely:

- prevent the successful non-seekable list cases above;
- erase recognized 7-Zip identity before the operation proves backward access is needed;
- route complete recognized archive bytes through raw format, which changes semantics rather than merely improving diagnostics;
- apply one format-level answer to an operation- and layout-dependent capability.

A stronger direction would preserve format identity and make the actual backward-seek requirement explicit. Viable designs include:

- retain the bid and return a precise recognized-but-non-seekable error at the first required backward move;
- expose or select a forward-only reader path for operations and layouts that need no backward move;
- spool only under an explicit bounded policy with owned cleanup and resource limits;
- add operation-specific evidence before changing the initial bidder.

The right upstream design remains their decision. This repository records why a one-line bidder guard has a real compatibility cost.

## Missing controls in the active proposal

A convincing upstream matrix should include:

- complete streamable 7-Zip input, not only a truncated signature buffer;
- list and extract as separate operations;
- central-directory placement that permits forward-only reading and placement that requires backward movement;
- tiny and look-ahead-exceeding payloads;
- one and multiple folders or pack streams;
- encoded headers and SFX prefixes;
- direct pipes, gzip filters, memory callbacks, and explicitly non-seekable callbacks;
- the observable format identity and diagnostic, not only status;
- raw fallback payload semantics.

## Generic CI caveat

The exact fork head passed:

- the focused list/extract workflow;
- the repository's standard CI workflow;
- Lint;
- CodeQL.

The generic CIFuzz workflow failed. Repeated job-log retrieval did not expose a usable diagnostic, so the cause remains unclassified. The evidence branch changes only workflow/probe files and the focused matrix is authoritative for the stated result, but the fork head is not described as fully green.

## Evidence boundary

The executed result covers one small 7-Zip archive generated on Ubuntu, one current controlled-fork master, `bsdtar` list and `-xO` extraction, direct/gzip-filtered transports, and one ordinary payload layout.

It does not establish every 7-Zip layout, large archives, callback APIs, partial reads, skip behavior, SFX, encoded headers, Windows pipes, or the final behavior of upstream PR 3070.

## Cleanup and rerun

The workflow built in a disposable runner, created all archives below a PID-specific directory, removed the directory through an EXIT trap, and retained text results only. No external data, persistent process, mount, package mutation, or privileged product operation survived.

## Disposition

**RETAIN AS OVERLAP REVIEW.** Close the controlled fork evidence carrier after posting its exact receipt. Do not create a competing product implementation while upstream PR 3070 remains active. Recheck public state before any future continuation.
