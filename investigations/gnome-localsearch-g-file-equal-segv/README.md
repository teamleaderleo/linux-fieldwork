# GNOME LocalSearch pending-directory lifetime crash

## In simple words

GNOME LocalSearch crashed five times while processing ordinary filesystem
events. The retained Ubuntu crash frame, matching debug symbols, exact packaged
source, and upstream history now identify the defect: LocalSearch 3.11.0 can
continue or free its active indexing root before walking that root's queued
directories. It then compares stale queue data in `g_file_equal()`.

GNOME had already fixed this exact crash after the 3.11.0 release. Upstream
commit `a53a3a7ffb4a9f2c6b4182c260c668ddc713f9ea` changes the handling order so
queued directories are removed before the operation that can continue or free
the indexing root. GNOME issue 442 contains the same function, source line, and
fanotify callback path as the retained Ubuntu crash.

Ubuntu 26.04 currently offers `localsearch 3.11.0-1ubuntu1.1`, which does not
contain that fix. The service has recovered automatically after every crash.
No live service, index, package, or setting was changed during this source
match.

## Current state

- State: `SOURCE-MATCHED`
- Owning issue: [#686](https://github.com/teamleaderleo/linux-fieldwork/issues/686)
- Exact working head: Linux Fieldwork base
  `85eebeb881d7e7c5ea9efac5b7438b0cf9126984`
- Latest authoritative artifact: retained Ubuntu Apport report resolved with
  the exact `localsearch-dbgsym 3.11.0-1ubuntu1.1` package
- First incomplete step: validate a future Ubuntu package containing upstream
  commit `a53a3a7ff` before treating the host exposure as fixed
- Cleanup state: all source/debug-package inspection used deleted temporary
  directories; the live service is active and healthy after automatic restart
- Next safe action: wait for or deliberately stage a matching fixed package in
  an isolated test environment; do not reproduce against the live user index
- External-contact state: no upstream or Ubuntu contact authorized or made

## Question and answer

**Question:** Can LocalSearch 3.11.0 reach invalid `GFile` state during a
filesystem lifecycle transition, and which transition owns that state?

**Answer:** Yes. A fanotify filesystem event reaches
`tracker_index_root_remove_directory()`. In 3.11.0, that function may call
`tracker_index_root_continue()` before iterating `root->pending_dirs`; upstream
identified that the earlier step can free the `TrackerIndexRoot`. The later
`g_file_equal()` therefore reads stale queue state. Upstream fixed the order in
`a53a3a7ff` and associated it with GNOME issue 442.

This is an exact source match, not merely a similarity in the top GLib frame:

- retained frame 0: `g_file_equal()`
- retained frame 1, PIE-relative `0x36907`:
  `tracker_index_root_remove_directory()` at the return from the
  `g_file_equal()` call for a pending directory
- retained later frames: `flush_event()` and `fanotify_events_cb()`
- GNOME issue 442: the same `g_file_equal()` call at
  `tracker-file-notifier.c:822`, reached from a monitor event and fanotify
- upstream fix: moves the pending-directory walk before the continuation path
  that can invalidate its owner and deletes the current queue link directly

## Source and package identity

- Project: GNOME LocalSearch and GLib/GIO
- Installed package: `localsearch 3.11.0-1ubuntu1.1`
- Installed GLib: `libglib2.0-0t64 2.88.0-1`
- Executable: `/usr/libexec/localsearch-3`
- Installed executable build ID:
  `fc49cb72b113f002a5c5df803a79f4db6b6932b0`
- Exact debug package SHA-256:
  `36f3334714c0d3dc54a533dd1c6dba4f2a1a9ce569db4717c63b72c1a28711f2`
- GNOME 3.11.0 tag commit:
  `bb5b477893df0a838e21f8ee32013200472d3404`
- GNOME 3.11 branch inspected at:
  `e2e3c36e0b19aed7552962ad4963a7b574feaab0`
- GNOME main inspected at:
  `6e00899e838d6ece976642ec9e05c3c5de51ffdc`
- Matching upstream fix:
  `a53a3a7ffb4a9f2c6b4182c260c668ddc713f9ea`
- Ubuntu source descriptor:
  `localsearch_3.11.0-1ubuntu1.1.dsc`
- Ubuntu original tar SHA-256:
  `c6774761a8b9f4a06f6812f1c8078bee2e937d65e376c3d2338b78993e5f4666`
- Ubuntu Debian tar SHA-256:
  `997dedd1695828ded5d308aacd32bfdf30c44b399ac2fcb2bd20b12e984b2c9b`

The Ubuntu delta has four patches: two test changes, one expected-failure
marker, and one extractor ZIP-library change. None touches
`tracker-file-notifier.c`, `tracker_index_root_remove_directory()`, or the
pending-directory queue. The installed package therefore retains the 3.11.0
ordering relevant to this crash.

## Environment

- Distribution: Ubuntu 26.04.1 LTS
- Kernel and architecture: Linux `7.0.0-30-generic`, x86-64
- Host context: physical GNOME workstation
- Privileges used: read-only user/system journal, retained user-owned Apport
  report, official source, and an extracted debug package

## Natural occurrences

The user service journal records five `SIGSEGV` exits:

1. 2026-08-29 14:14:46 Asia/Shanghai
2. 2026-08-29 20:18:15 Asia/Shanghai
3. 2026-08-30 01:53:49 Asia/Shanghai
4. 2026-08-30 02:03:43 Asia/Shanghai
5. 2026-08-30 08:11:05 Asia/Shanghai

An additional 2026-08-29 14:33:49 `SIGKILL` was externally initiated and is
not counted as a crash. This is why systemd's current `NRestarts=6` must not be
presented as six LocalSearch faults.

At the fifth crash, an extractor logged that its filesystem-miner endpoint had
closed immediately after the kernel fault. With the source match established,
that message is recovery fallout from the indexer disappearing, not evidence
that the endpoint closure triggered the fault.

The broad home-directory index had already been narrowed before the second
crash, so broad recursion is not required. A short interval between the third
and fourth crashes also shows that long uptime is not required. Concurrent
extractor work and host workloads remain environmental observations, not
causes.

## Evidence method

1. Counted only explicit `status=11/SEGV` exits in the service journal.
2. Unpacked the retained 20:18 Apport report into a temporary directory and
   inspected only stack, register, executable-map, and package identity data.
3. Computed the executable's PIE-relative retained frames:
   `0x36907`, `0x3054f`, `0x3099a`, and `0x15736`.
4. Downloaded and extracted the exact Ubuntu debug package without installing
   it. Its build ID matched the installed executable and resolved those frames
   to `tracker_index_root_remove_directory()`, `flush_event()`,
   `fanotify_events_cb()`, and `main()`.
5. Disassembled the installed `g_file_equal()` and LocalSearch call site. The
   kernel fault offset is the first-argument `GFile` type dereference, and the
   caller is the pending-directory comparison at 3.11.0 source line 822.
6. Verified the Ubuntu Debian tar checksum and inspected its complete patch
   series; no downstream patch changes this path.
7. Compared the exact 3.11.0 tag with the current 3.11 and main branches. The
   single relevant change is upstream `a53a3a7ff`, whose stated failure mode and
   code change match the retained stack.
8. Queried GNOME issue 442 read-only. Its full stack reaches the same source
   line through the same monitor/fanotify path.

## What is and is not demonstrated

Demonstrated:

- five natural recurrences on the installed package;
- exact function and call site for the retained crash;
- exact equivalence to a closed upstream issue and merged upstream fix;
- absence of a relevant Ubuntu downstream patch;
- automatic service recovery after every crash.

Not demonstrated:

- a deterministic synthetic reproduction on this host;
- whether every one of the five crashes used the identical deeper callback
  path, because only one full Apport stack is retained;
- that unrelated MIME warnings, indexed file contents, memory pressure, or
  host contention cause the fault;
- that the host is fixed while Ubuntu still ships the pre-fix package.

## Next step

Treat this investigation as source-matched and stop trying to provoke the live
service. Monitor Ubuntu for a package that contains `a53a3a7ff`; when one is
available, verify its source delta/build identity, install it during an
authorized low-impact window, and confirm that the service remains healthy
across ordinary filesystem activity. If a local backport is considered before
then, build and exercise it only in an isolated user/session first.

## Authority and privacy

Internal source research and owned Linux Fieldwork updates are authorized. No
upstream issue, merge request, comment, Ubuntu bug, crash upload, or patch was
created by this investigation. The original crash file, memory maps, private
paths, filenames, environment, and process arguments are not committed.
