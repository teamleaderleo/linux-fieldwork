# OverlayFS nested hot-state mounts fall back to `xino=off`

## In simple words

`big-red` logged 38 warnings while Glaeda and Scrapbook experiments mounted
task-private OverlayFS views over resident build/cache trees:

```text
overlayfs: fs on '<sandbox path>' does not support file handles, falling back to xino=off.
```

The workloads completed, and this is not evidence of an ext4 or NVMe failure.
The open question is whether the nested overlay topology merely loses optional
persistent/uniform inode-number behavior, or whether it can invalidate a
Glaeda cache-identity, filesystem-observation, or performance claim.

Tracking: [Linux Fieldwork issue #688](https://github.com/teamleaderleo/linux-fieldwork/issues/688)

## Current state

- State: `SCOPING`
- Exact working head: `bde57e9e8a93a0ac582bb62b9de47eacbfe636e8`
- Latest authoritative artifact: 38 current-boot kernel messages between
  14:42:26 and 15:26:26 Asia/Shanghai on 2026-08-29
- First incomplete step: reduce one warning to a minimal nested-overlay mount
  topology and record both layers' mount options and file-handle capability
- Cleanup state: no OverlayFS mounts remained active at the observation point
- Next safe action: compare one direct ext4-backed overlay and one
  overlay-backed lower/upper candidate with `stat`, `readdir`, rename/copy-up,
  hard-link, inotify/fanotify where supported, teardown, and clean rerun
- External-contact state: internal owned-repository research only; no upstream
  issue, comment, or patch is authorized

## Intent and precedent

The Linux OverlayFS documentation says `xino` composes a filesystem ID with an
underlying inode number. With `xino=on` or `xino=auto`, persistent and uniform
inode behavior requires underlying filesystems that support file handles. With
`xino=off`, `st_ino`, `st_dev`, and `d_ino` can have weaker persistence and
uniformity properties. Many applications do not care, but Glaeda explicitly
models source/cache identity and cleanup, so the lost property needs a bounded
compatibility check rather than an assumption.

Primary reference:
<https://www.kernel.org/doc/html/latest/filesystems/overlayfs.html#inode-properties>

## Question

For Glaeda's ultra-trusted stable-path/task-private hot-state topology, what
exact layer lacks exportable file handles, and does the resulting `xino=off`
fallback change any inode identity, directory enumeration, hard-link,
copy-up/rename, watcher, cleanup, or measured-latency property that the current
contract relies on?

## Environment

- Distribution: Ubuntu 26.04.1 LTS
- Kernel/architecture: Linux `7.0.0-30-generic`, x86-64
- Root filesystem: ext4, `rw,relatime`
- Overlay module `xino_auto`: `Y`
- Privileges: observation was read-only; the original mounts were created by
  unprivileged trusted local experiment helpers
- Context: task-private sandbox views over resident Rust `target` and Next.js
  `.next` trees; paths are sanitized here because their exact usernames and
  temporary names add no technical evidence

## Baseline behavior

The current boot contained 38 matching kernel messages. They covered resident
Rust target trees, task-private OverlayFS upper trees, temporary resident
targets, and one Next.js `.next` tree. A representative line was:

```text
overlayfs: fs on '<resident target>' does not support file handles, falling back to xino=off.
```

At the later observation point, `findmnt -t overlay` showed no surviving
mounts. The root filesystem remained healthy, and NVMe SMART reported no media
or error-log entries.

## Competing explanations

1. Expected nested-overlay limitation: an OverlayFS layer used as a backing
   layer does not provide the file handles required by `xino=auto`; only inode
   presentation weakens, while Glaeda's content/path/generation contracts stay
   correct.
2. Topology mistake: a path intended to remain direct ext4-backed is actually
   overlay-backed inside the sandbox, needlessly losing `xino` properties and
   perhaps adding copy-up cost.
3. Contract defect: a current Glaeda check implicitly treats inode identity or
   a watcher observation as stable across a topology where the kernel does not
   promise it.
4. Kernel regression: the exact nested topology previously supplied usable
   file handles but does not on this kernel. No version comparison currently
   supports this explanation.

## Reproduction

The current observation is recoverable with bounded read-only commands:

```sh
journalctl -k -b --no-pager \
  | grep 'overlayfs: .*falling back to xino=off'
cat /sys/module/overlay/parameters/xino_auto
findmnt -t overlay -o TARGET,SOURCE,FSTYPE,OPTIONS
findmnt -no FSTYPE,OPTIONS /
```

Do not recreate the warning by mounting over another route's live build tree.
The next probe must use disposable directories, name every lower/upper/work
layer, and remove only mounts and paths it created.

## Evidence boundary

This record establishes repeated fallback messages on one Ubuntu/kernel/host
and identifies the kernel contract that weakens when `xino` is disabled. It
does not yet establish a correctness failure, performance regression, kernel
regression, or upstream defect. No inode comparison, minimal topology, older
kernel control, or Glaeda semantic test has run.

## Next step

Build the smallest disposable direct-ext4 versus nested-overlay comparison.
Record mountinfo, file-handle support, inode/device values before and after
copy-up/rename, hard-link behavior, watcher behavior where available, elapsed
setup/teardown, surviving mounts, and a clean rerun. Stop if the only difference
is the documented inode-presentation property and Glaeda consumes none of it;
otherwise move the exact losing contract into the owning Glaeda test or a
kernel-source investigation.

## Authority

Internal research in `teamleaderleo/linux-fieldwork` is authorized. No external
upstream interaction has occurred or is authorized.
