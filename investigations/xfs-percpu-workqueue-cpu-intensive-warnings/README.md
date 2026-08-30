# XFS per-CPU workqueue CPU-intensive warnings

## In simple words

A sustained, disposable XFS/reflink experiment made two XFS background jobs
use more than 10 milliseconds of CPU in one workqueue invocation. Linux
reported this as a CPU-intensive workqueue advisory for `xlog_ioend_work` and
`xfs_reclaim_worker`.

The filesystem still mounted and unmounted cleanly. There was no soft lockup,
hung task, filesystem shutdown, corruption report, or demonstrated user-visible
stall. Shorter XFS experiments on the same boot did not emit the advisory.

This is worth measuring because the long experiment exercised the same
sustained metadata and compiler-state churn that a future persistent Glaeda
project disk may see. It is not evidence that Glaeda damaged the filesystem,
and it is not a reason to change the live kernel, workqueue flags, or XFS mount
policy.

## Current state

- State: `SCOPING`
- Owning issue: [#696](https://github.com/teamleaderleo/linux-fieldwork/issues/696)
- Exact working source reference: Linux main
  `08dbfad3f5040f5bdb6c529da20d6d4e81fefd72`; the running Ubuntu source was not
  imported
- Latest authoritative artifact: current-boot kernel journal plus the frozen
  workload summary in the owned Glaeda repository
- First incomplete step: identify which callback, loop, or lock accounts for
  the measured `xlog_ioend_work` CPU time and independently characterize the
  reclaim worker
- Cleanup state: the observed loopback filesystem was cleanly unmounted and
  its route-owned experiment artifacts were removed; no tracing process,
  benchmark worker, loop device, or test mount remains from this investigation
- Next safe action: run a short-versus-sustained discriminator on a new
  disposable loopback filesystem during an authorized quiet window
- External-contact state: no upstream contact authorized or made

## Question

Under a bounded reflink/materialization workload, which exact XFS callback,
loop, or lock makes `xlog_ioend_work` and `xfs_reclaim_worker` exceed Linux's
10-millisecond per-CPU workqueue threshold, and does the event correlate with
workload duration, metadata fan-out, memory pressure, or storage latency?

The two functions are separate observations. A result for the log-completion
path must not be generalized to inode reclaim without independent evidence.

## Source and intent

The current Linux workqueue implementation automatically marks a bound work
item CPU-intensive after it exceeds the configured threshold. The diagnostic
uses exponential backoff and suggests considering `WQ_UNBOUND`; that suggestion
is a generic workqueue hint, not a subsystem-specific fix.

Primary sources at the inspected Linux head:

- [`kernel/workqueue.c`](https://github.com/torvalds/linux/blob/08dbfad3f5040f5bdb6c529da20d6d4e81fefd72/kernel/workqueue.c)
  contains the accounting, advisory, and automatic CPU-intensive classification.
- [Workqueue documentation](https://github.com/torvalds/linux/blob/08dbfad3f5040f5bdb6c529da20d6d4e81fefd72/Documentation/core-api/workqueue.rst)
  describes the locality and scheduler tradeoffs of `WQ_UNBOUND` and
  `WQ_CPU_INTENSIVE`.
- [`fs/xfs/xfs_log.c`](https://github.com/torvalds/linux/blob/08dbfad3f5040f5bdb6c529da20d6d4e81fefd72/fs/xfs/xfs_log.c)
  runs the journal completion callbacks in `xlog_ioend_work()` and then releases
  the iclog semaphore.
- [`fs/xfs/xfs_super.c`](https://github.com/torvalds/linux/blob/08dbfad3f5040f5bdb6c529da20d6d4e81fefd72/fs/xfs/xfs_super.c)
  runs the reclaim walk and requeues `xfs_reclaim_worker()`.

At that head, XFS deliberately creates both relevant queues as per-CPU queues.
The log queue additionally uses high priority. Current main therefore contains
no accepted switch to `WQ_UNBOUND` for either observation.

Commit `69635d7f4b344e6f5344bba3c3de92e4fb8b0d2a` added explicit `WQ_PERCPU` to
these queue definitions as part of the workqueue API migration. It preserved
the former absence of `WQ_UNBOUND`; it was not a behavioral queue-policy change.

## Environment

- Distribution: Ubuntu 26.04.1 LTS
- Running kernel: `7.0.0-30-generic`, Ubuntu package `7.0.0-30.30`, upstream
  version signature `7.0.12`
- Architecture and preemption: x86-64, `PREEMPT_DYNAMIC`
- Host context: physical workstation; the observed filesystem was a disposable
  32 GiB sparse loopback image, not the root filesystem or a user data volume
- XFS userspace: `xfsprogs 6.18`
- XFS format and mount: reflink enabled, 4 KiB blocks, `noatime`
- Workqueue threshold: `cpu_intensive_thresh_us=10000`
- Workqueue warning threshold: `cpu_intensive_warning_thresh=4`
- Default affinity scope: `cache`
- Power-efficient workqueues: enabled
- Privileges in this pass: journal, sysfs, source, and repository reads only;
  no tracing, mount, kernel, sysfs, or package change

## Natural observation

The loopback XFS filesystem mounted cleanly at 04:53:35 Asia/Shanghai. The
first advisory appeared after 5 minutes 15 seconds. The final advisory appeared
at 06:07:44, and the filesystem unmounted cleanly at 06:21:36.

The workqueue report's count is cumulative and printed with exponential
backoff, so the following values do not mean there were only ten long
invocations:

| Function | Report times | Cumulative counts shown |
| --- | --- | --- |
| `xlog_ioend_work` | 04:58:50 through 06:07:44 | 4, 5, 7, 11, 19, 35, 67 |
| `xfs_reclaim_worker` | 05:16:16 through 05:21:51 | 4, 5, 7 |

The frozen workload used 475 tracked regular files and about 9.29 MB of source
per task. It combined exact same-head source fan-out with private compiler-state
lineages. The primary bracket included fan-out widths one and four; one later
exploratory arm used width eight. Across the full run, 63 task worktrees were
created, validated, and removed. All 51 task validators in the composed bracket
passed 1,343 tests with one ignored and zero failures.

The largest measured single run grew the XFS filesystem by about 12.55 GB. The
full route lasted about 88 minutes and repeatedly created, compiled in, and
removed task trees. This is sustained metadata and data churn, not merely one
reflink fan-out call.

Negative controls on the same boot matter:

- earlier short XFS mounts lasting roughly four to six minutes emitted none of
  these workqueue advisories;
- a later 25-minute XFS loopback mount emitted none;
- the observed mount produced no soft-lockup, hung-task, XFS shutdown,
  corruption, or unclean-unmount message.

This makes sustained workload duration or volume a useful discriminator. It
does not yet distinguish callback-list size, lock contention, inode pressure,
CPU contention, or backing-file latency.

## Related 2026 patch series is not an exact match

XFS Patchwork series 1051055, version 1, proposed adding `cond_resched()` in
several XFS loops. Patch 14413226 is titled `xfs: take a breath in
xlog_ioend_work()`. As of this investigation it remains `new` with checks
`pending`; the Patchwork index contains no version 2.

That report is not an accepted fix and does not match this observation:

- its submitted stack showed a 22-second soft lockup in
  `xlog_cil_process_committed()` under concurrent stress-ng, LTP, and fio;
- the XFS maintainer stated that normal completion may process tens of
  thousands of items but should not take more than a few hundred milliseconds;
- the review characterized the 22-second behavior as catastrophic spin-lock
  contention rather than proof that the loop simply needed a yield;
- the companion xfsaild report was from Linux 6.6 on a 384-CPU machine with
  four allocation groups and a relatively small log. The maintainer identified
  a scalability series merged for 6.11 as the relevant fix direction;
- this host runs 7.0.12, recorded only the generic greater-than-10-ms
  workqueue advisory, and produced no stack or soft lockup;
- the proposed series does not address `xfs_reclaim_worker`.

Primary discussion:

- [Patchwork 14413226](https://patchwork.kernel.org/project/xfs/patch/20260205082621.2259895-2-alexjlzheng@tencent.com/)
- [Patchwork 14413227](https://patchwork.kernel.org/project/xfs/patch/20260205082621.2259895-3-alexjlzheng@tencent.com/)

Applying that patch, changing queue flags, or raising the warning threshold
would hide or alter the signal before the actual 10-ms path is known. None is
a justified host optimization.

## Hypotheses and discriminators

1. **Sustained callback volume:** long/high-fan-out arms should increase
   `xlog_ioend_work` events even when CPU and storage latency are stable.
2. **Log or AIL lock contention:** event duration should correlate with lock
   wait/spin evidence or concurrent transaction pressure rather than file count
   alone.
3. **Inode reclaim pressure:** `xfs_reclaim_worker` events should correlate
   with reclaimable inode counts or memory pressure and may occur independently
   of log-completion events.
4. **Backing-file latency:** events should track loopback writeback or host
   storage latency; a direct disposable block device or different backing
   treatment would distinguish this, but is not required for the first pass.
5. **Generic CPU contention:** equivalent filesystem work under a smaller,
   explicit CPU grant should change event duration without changing XFS object
   counts.

## Safe reproduction design

Do not reproduce on a user filesystem. During an authorized quiet window:

1. create a new, bounded sparse image in a route-owned temporary directory;
2. attach one explicitly recorded loop device, format it as XFS with reflink,
   and mount it below that same temporary root;
3. capture the starting journal cursor, workqueue threshold, kernel/package
   identity, XFS geometry, memory pressure, and block-device topology;
4. run synthetic-path arms that vary one dimension at a time: short versus
   sustained duration, then low versus high metadata fan-out;
5. retain exact operation counts and workload phase timestamps;
6. if the advisory recurs, use a bounded trace window only on the disposable
   arm to measure workqueue execution duration and selected XFS/lock events;
7. stop the workload, synchronize, unmount cleanly, detach the exact loop
   device, remove the route-owned temporary directory, and prove no worker,
   listener, mount, or loop attachment remains.

The first run should not change workqueue sysfs, kernel command-line options,
XFS queue flags, watchdog thresholds, or production mount policy. If tracing
cannot distinguish time inside the callback path from off-CPU delay, stop and
refine the trace plan rather than broadening capture on the live machine.

## Interpretation

The current evidence justifies a scoped performance/scheduler investigation.
It does not justify a Glaeda defect, an XFS correctness bug, or a kernel change.

The strongest present discriminator is duration/volume: the warnings appeared
only during the long composed workload, began several minutes after mount, and
continued at widening intervals as Linux's report count backed off. Mounting
XFS or using reflink once was insufficient in the observed negative controls.

Because `xlog_ioend_work` and `xfs_reclaim_worker` both remain on intentional
per-CPU queues in current upstream source, the generic `consider switching to
WQ_UNBOUND` text must not be treated as upstream's subsystem decision. Moving
work unbound may trade locality and priority behavior for scheduler freedom;
that trade needs function-specific measurements and upstream design context.

## Evidence boundary

Demonstrated:

- repeated greater-than-10-ms CPU-intensive classifications for the two named
  XFS work functions during one sustained disposable workload;
- clean mount, successful workload semantics, complete cleanup, and clean
  unmount;
- absence of the matching warnings in shorter same-boot XFS controls;
- absence of current upstream `WQ_UNBOUND` conversion for these queues;
- an unmerged soft-lockup patch series exists but has a materially different
  kernel, scale, duration, stack evidence, and failure severity.

Not demonstrated:

- exact invocation durations above 10 ms;
- where CPU time was spent within either function;
- a soft lockup, user-visible latency regression, data loss, corruption, or
  filesystem shutdown;
- deterministic reproduction;
- that reflink itself, rather than sustained compiler output, worktree cleanup,
  writeback, or inode reclaim, is causal;
- that the current upstream source is byte-identical to Ubuntu's 7.0.12 XFS
  module; Ubuntu source was not imported in this pass;
- that changing queue policy or adding `cond_resched()` would improve this
  workload without a correctness or performance cost.

## Next step

Retain this as `SCOPING` until a quiet window permits the isolated
short-versus-sustained discriminator. Promote it to `EXECUTING` only with an
exact temporary root, time bound, cleanup proof, journal cursor, and narrow
trace plan. If no advisory recurs under the bounded synthetic treatment, keep
the natural observation and wait for another route-owned high-volume XFS run
rather than increasing load on the workstation merely to force the warning.

## Authority and privacy

Owned Linux Fieldwork research and repository updates are authorized. No Linux,
XFS, Ubuntu, Patchwork, mailing-list, or third-party issue, comment, email,
patch, or other interaction was created. Private paths, raw task names, process
arguments, and unrelated journal content are not committed.
