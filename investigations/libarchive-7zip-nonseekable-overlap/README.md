# libarchive 7-Zip non-seekable stream overlap review

## TL;DR

The original Linux Fieldwork selection treated libarchive issue 3068 as an unowned implementation target. A live source and discussion refresh found two upstream carriers:

- merged PR 3074 restored forward-only 7-Zip reading after a regression;
- open PR 3070 already proposes seekability-aware bidding, core descriptor seekability changes, and a pipe/raw fallback test.

Independent implementation stops. This record retains current-master behavior, the exact overlap correction, and the compatibility questions that the active patch still needs to answer.

## Explain like I'm five

A 7-Zip reader sometimes can walk forward through the archive without jumping backward. One upstream repair restored that walk. Another open patch says the reader should refuse every delivery method that cannot jump. Our job is to test where walking is enough and where jumping is truly required, not to build a competing patch.

## Why care

libarchive is a shared parser behind archive tools, package systems, backup software, and language runtimes. A bidder that claims an unreadable stream can fail late. A bidder that rejects every non-seekable stream can also discard valid forward-readable layouts or silently hand recognized bytes to the raw reader. Listing, extraction, archive layout, filters, callbacks, and diagnostic policy all matter.

## Source and authority

- Project: libarchive
- Controlled fork: `teamleaderleo/libarchive`
- Fork PR: `teamleaderleo/libarchive#1`
- Initial probe head: `ceb74e8db3aa90cd8ed7d269c911ed2d4f6d7762`
- Current probe head: `05b12705eac73fafb6ce3da68fd6d719edada05a`
- Linux Fieldwork issue: #230
- Public issue: https://github.com/libarchive/libarchive/issues/3068
- Active public PR: https://github.com/libarchive/libarchive/pull/3070
- Merged public PR: https://github.com/libarchive/libarchive/pull/3074
- External contact: unauthorized and not made

The controlled fork adds evidence scripts and workflow only. No libarchive product source is changed.

## Historical source transition

The issue discussion identifies PR 2985 as the regression point where SFX data-offset detection and central-directory slurping were merged. That path introduced an unconditional seek.

Merged PR 3074, merge commit `531d70f88cb0ba6a44f3f72995c42ac5188f58ca`, made one focused change:

```diff
-if (__archive_read_seek(a, data_offset, SEEK_SET) < 0)
+if (__archive_read_consume(a, data_offset) < 0)
```

That restores forward progress when the central-directory offset lies ahead of the current stream position. It does not create general backward seeking.

Current `seek_compat()` follows the same boundary:

- real seek when `a->filter->can_seek` is true;
- forward `SEEK_CUR` and forward `SEEK_SET` become byte consumption when compatibility mode is enabled;
- backward movement on a non-seekable stream fails.

The phrase “7-Zip requires seeking” is therefore too broad. Some layouts and operations are forward-readable; others require a backward move after end metadata is parsed.

## Active equivalent work

Open PR 3070, head `c79a8b8a221022ebc5b23accdb06bc14923c4082`, changes four files:

1. initial filter `can_seek` state derives from whether a client seeker exists;
2. `archive_read_open_fd()` installs `file_seek` only for regular files;
3. the 7-Zip bidder returns zero when `a->filter->can_seek == 0`;
4. a new pipe test expects 7-Zip to abstain and raw format to win.

The public PR remains open. Under Linux Fieldwork's promotion-expiry rule, this is active equivalent ownership. Any local product branch would be duplicate work.

## First controlled probe

Focused run: `30592942923`  
Job: `91038954194`  
Conclusion: success  
Artifact ID: `8780161783`  
Artifact ZIP SHA-256: `7663cb66d52486e9f66c9fb20047d0f21dcdc8b6cf8db85e622013a14e6c0b55`

A tiny ordinary 7-Zip archive containing `payload.txt` listed successfully through:

```text
regular file             status 0
direct 7-Zip stdin pipe status 0
gzip-wrapped file        status 0
gzip-wrapped stdin pipe  status 0
```

This confirms current master can recognize and list the small fixture without seekable input.

The first script also attempted `bsdtar --format raw` in list mode. `bsdtar` rejected that command because `--format` is not permitted with list mode. That row is a harness error, not a raw-fallback observation.

## Evidence hole and repair

Listing can consume forward to end metadata and print names without proving that entry payload can later be reached. A central directory at the end can require backward movement for extraction.

The repaired probe removes the invalid raw command and adds both list and `-xO` extraction cases for:

- seekable regular 7-Zip file;
- direct 7-Zip pipe;
- gzip-wrapped file;
- gzip-wrapped pipe;
- externally gzip-decoded 7-Zip pipe.

Current exact head: `05b12705eac73fafb6ce3da68fd6d719edada05a`  
Focused rerun: `30596397991`  
State at last checkpoint: queued

No extraction result is claimed until that run completes.

## Active-PR review questions

### Bid versus actual capability

A global `can_seek == 0` bidder rejection may discard an archive that needs only forward consumption. The active test uses a truncated signature and raw fallback, not a complete streamable 7-Zip archive. A complete forward-readable control should determine whether the bidder change removes useful behavior.

### Descriptor classification

PR 3070 installs the default file seeker only for regular files. Review character devices, block devices, sockets, FIFOs, memfd, procfs/sysfs files, and descriptors whose `lseek()` behavior does not match `S_ISREG`.

### Operation-specific behavior

Listing may succeed where extraction fails. The public contract may prefer:

- recognized format plus a late precise seek error;
- early recognized-but-unreadable error;
- raw fallback;
- spooling;
- operation/layout-specific streaming.

These choices are not equivalent.

### Archive matrix

A convincing regression should vary:

- central-directory placement;
- tiny versus look-ahead-exceeding payloads;
- one versus multiple folders/pack streams;
- encoded headers;
- SFX prefixes;
- direct and gzip-filtered input;
- memory and explicitly non-seekable callbacks;
- list, extract, skip, and partial-read operations.

## Negative ramifications

- Bidder abstention can weaken reliable format identity and route bytes through raw mode.
- Strong bidding can retain late seek failures.
- Spooling can consume unbounded disk, change latency, and add cleanup/failure policy.
- Core descriptor seekability changes affect every filter and format, not only 7-Zip.
- A test that uses only a signature-sized truncated buffer may prove bidding mechanics while missing complete-archive compatibility.

## Cleanup and evidence limits

The hosted probe builds in a disposable runner, creates temporary archives under a PID-specific directory, removes them through a trap, and uploads text results only. No external data or privileged state is involved.

The first result covers one small archive generated by 7-Zip on Ubuntu and current controlled-fork master. It does not establish larger archives, all 7-Zip layouts, callback APIs, or the active PR's final behavior.

## Current disposition

**HOLD AS OVERLAP REVIEW.** Finish the extraction matrix, retain any missing compatibility control, and stop independent product implementation while upstream PR 3070 remains the active equivalent carrier.