# Unprivileged bubblewrap OverlayFS falls back to `xino=off`

## In simple words

The repeated `xino=off` messages on `big-red` are explained behavior, not
evidence of broken ext4, NVMe, nested mounts, or a Linux regression.

Glaeda asks unprivileged bubblewrap to create a short-lived OverlayFS view. The
kernel only enables OverlayFS's persistent inode-number composition when the
mounting task can decode underlying file handles. Its
`ovl_can_decode_fh()` helper deliberately returns false unless the task has
`CAP_DAC_READ_SEARCH` in the initial user namespace. An unprivileged bubblewrap
mount does not have that authority, so `xino=auto` becomes `xino=off` and emits
one warning. The mount still works and is torn down correctly.

Tracking: [Linux Fieldwork issue #688](https://github.com/teamleaderleo/linux-fieldwork/issues/688)

## Disposition

- State: `NEGATIVE_RESULT_EXPLAINED`
- Host: Ubuntu 26.04.1, Linux `7.0.0-30-generic`, x86-64
- Glaeda head exercised: `c81ac80` (`main`, private-copy merge state)
- Exact Glaeda control: `HotRunTests.test_task_sees_stable_path_and_target_writes_stay_private`
- Current-boot count after bounded probes: 75 messages
- Cleanup: the test and both reduced probes exited; no OverlayFS mount remained;
  `/tmp/glaeda-xino-probe.M0ZNfn` was removed after restoring owner traversal
  permission on bubblewrap's empty work subdirectories
- External contact: none; no kernel or bubblewrap issue, comment, or patch is
  authorized or warranted by this evidence

## Why the first hypothesis lost

The first record suspected a nested-overlay backing layer because kernel paths
appeared below `/oldroot`. That prefix is bubblewrap's temporary name for the
host tree while it constructs the new mount namespace; it does not prove that
the lower filesystem is itself OverlayFS.

Two controls distinguish the mechanism:

1. Glaeda's own disposable `/tmp` fixture added exactly one warning: 72 -> 73.
2. A reduced bubblewrap overlay with a plain ext4-backed lower directory added
   exactly one warning: 73 -> 74. Repeating it with bubblewrap's
   `--cap-add CAP_DAC_READ_SEARCH` still added one: 74 -> 75. The latter flag
   cannot grant the initial-user-namespace capability required by the kernel
   check to an unprivileged caller.

The direct ext4 control rules out “only a nested OverlayFS lower triggers the
fallback.” It also makes a direct-versus-nested mount matrix unnecessary for
the question this investigation originally asked.

## Source mechanism

Current Linux source implements the decision in
[`ovl_can_decode_fh()`](https://github.com/torvalds/linux/blob/master/fs/overlayfs/util.c):
it returns zero when `capable(CAP_DAC_READ_SEARCH)` is false or when the
filesystem cannot decode handles. `capable()` is the initial-user-namespace
capability check. OverlayFS mount setup then turns `xino=auto` into `xino=off`
and emits the observed message when an upper layer exists and that helper
returns zero.

The [kernel OverlayFS documentation](https://docs.kernel.org/filesystems/overlayfs.html#inode-properties)
describes the consequence: without `xino`, `st_ino`, `st_dev`, and directory
entry inode values have weaker uniformity and persistence properties. This is
not data loss and does not mean the underlying filesystem cannot encode a file
handle for ordinary callers.

On this host, a read-only `name_to_handle_at()` probe succeeded for both the
ext4 Glaeda `target` directory and `/tmp`. That is consistent rather than
contradictory: the syscall's encoding ability is weaker than OverlayFS's need
to decode handles under its capability policy.

Bubblewrap 0.11.1 exposes `--overlay-src`, `--overlay`, `--tmp-overlay`, and
`--ro-overlay`, but no option for choosing `xino=off` explicitly. Its generated
unprivileged mount uses `userxattr`, and the kernel's global `xino_auto` module
parameter on this host is `Y`.

## Reproduction

The product-level control is disposable and uses Glaeda's existing test:

```sh
before=$(journalctl -k -b --no-pager | grep -c 'xino=off')
/usr/bin/python3 scripts/test-hot-run.py \
  HotRunTests.test_task_sees_stable_path_and_target_writes_stay_private
after=$(journalctl -k -b --no-pager | grep -c 'xino=off')
printf '%s -> %s\n' "$before" "$after"
findmnt -t overlay -o TARGET,SOURCE,FSTYPE,OPTIONS
```

Observed: the test passed, the count advanced `72 -> 73`, and no OverlayFS
mount survived.

The reduced control used a `mktemp -d` root with empty lower, upper, work, and
destination directories, then invoked:

```sh
bwrap --die-with-parent --dev-bind / / \
  --overlay-src "$probe/lower" \
  --overlay "$probe/upper" "$probe/work" "$probe/dest" \
  /usr/bin/true
```

The same command was repeated with `--cap-add CAP_DAC_READ_SEARCH`. Each run
added one warning. Both mounted successfully and exited; cleanup removed only
the named disposable root.

## Contract impact for Glaeda

The exercised Glaeda path does not use overlay inode numbers as durable cache,
lease, ownership, source, or cleanup identity. Its hot-state authority remains
bound to explicit resident/task paths, runtime identity, private state roots,
locks, content/toolchain contracts, and exact process completion. The focused
test proved task-private writes, stable visible paths, measurement output, and
teardown while the fallback occurred.

Accordingly, this investigation establishes no Glaeda correctness failure. The
remaining concern is operational noise and the documented weaker inode view if
a future cache indexer or watcher begins treating inode numbers as persistent
across mounts.

## Next decision

Do not change the host-wide `xino_auto` module parameter and do not grant
additional capabilities to suppress a harmless warning. Those would broaden
machine behavior or authority for no demonstrated benefit.

If Glaeda keeps OverlayFS mode as an option, a bounded successor may:

- add an explicit contract test that no durable Glaeda identity is derived
  from `st_ino`/`st_dev` across an overlay lifecycle;
- measure whether `xino=off` changes any relevant hot-run latency on the actual
  workload (the present work did not benchmark it); or
- investigate an owned bubblewrap enhancement that can request `xino=off`
  explicitly, solely to avoid predictable kernel-log noise.

Reopen the kernel-defect question only if a privileged control with the
required initial-namespace capability still produces the same fallback on a
filesystem whose export operations can decode handles, or if a documented
Glaeda invariant actually fails.

## Evidence boundary

This is one host, one kernel build, bubblewrap 0.11.1, one passing Glaeda
contract test, and two reduced unprivileged mounts. It explains the observed
warning and rules out the original nested-only hypothesis. It does not compare
performance, older kernels, privileged mounts, watcher behavior, NFS export,
or every OverlayFS operation. No upstream defect is claimed.
