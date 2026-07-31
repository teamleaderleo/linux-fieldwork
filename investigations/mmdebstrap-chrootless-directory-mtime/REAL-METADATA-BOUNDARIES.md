# Real mount, ACL, and file-capability boundary probe

Tracking: issue #380, PR #383, symlink repair PR #386, device repair PR
#388, metadata repair PR #390.

## TL;DR

The synthetic matrix now has an exact hosted integration gate for three material
premises that ordinary unprivileged tests cannot fully establish:

- a real foreign-device tmpfs mount is pruned without timestamp mutation;
- POSIX ACLs on a directory and regular file survive normalization;
- a real `security.capability` file attribute survives normalization.

The probe runs twice from clean disposable state, unmounts before recursive
cleanup, refuses `rm -rf` if the mount remains active, and retains one receipt per
run.

This is still an evidence gate. It does not patch mmdebstrap product source or
select the final insertion point.

## Explain like I'm five

The earlier test used a pretend label saying “this folder is on another disk.”
This hosted test creates a real tiny temporary disk, puts a sentinel inside it,
and proves the folder-date helper leaves it alone.

It also checks a directory access list and an executable file capability before
and after the operation.

## Why care

A source tree can contain mounted descendants and metadata that simple file
content comparisons do not show. A repair that makes archives reproducible while
crossing mounts, removing ACLs, or clearing capabilities would be worse than the
original timestamp difference.

Cleanup is part of the safety claim. Recursive deletion must never run against a
still-mounted path.

## Exact branch boundary

Construction branch:

`repair/chrootless-dir-mtime-real-boundaries`

Base:

PR #390 exact head `efb8ac9ce36b866fc7a5821cf8c5596de7501ba2`.

Changed surfaces:

- `.github/workflows/mmdebstrap-chrootless-directory-mtime.yml`;
- `investigations/mmdebstrap-chrootless-directory-mtime/real_metadata_probe.sh`;
- `tests/test_mmdebstrap_chrootless_directory_mtime_real_probe.py`;
- this record.

The focused normalization helper remains the same symlink-safe, same-device
helper from the lower evidence stack.

## Runtime authority

The probe accepts only the existing disposable parent families:

- `/tmp`;
- `/var/tmp`;
- `/home/runner/work/_temp`.

It canonicalizes the parent and fixed runtime, requires a strict child, rejects
filesystem root, rejects repository overlap in both directions, and rejects
unsafe HOME relationships. The ordinary hosted placement below
`/home/runner/work/_temp` is allowed without permitting the runtime to equal or
contain HOME.

Path validation completes before the first recursive deletion.

## Real mount control

The probe creates:

```text
$runtime/tree/
├── ordinary/
└── foreign-device/     # real tmpfs mount
    └── nested/
        └── sentinel
```

It requires:

- root and tmpfs `st_dev` values differ;
- ordinary directory starts with the old timestamp;
- tmpfs mount, nested directory, and sentinel start with the old timestamp;
- normalization changes the ordinary directory to the selected epoch;
- tmpfs mount, nested directory, sentinel mtime, and sentinel bytes remain
  unchanged;
- the tmpfs remains mounted during the assertions.

The probe imports the exact focused helper from the repository test module, so
the hosted result executes the same traversal policy reviewed by the synthetic
matrix.

## ACL control

The probe creates a real directory and regular file, adds explicit `nobody` ACL
entries through `setfacl`, and retains canonical `getfacl -cp` output before and
after normalization.

The exact ACL text must be identical.

## File-capability control

The probe creates an executable regular file and applies:

```text
cap_net_bind_service=ep
```

with `setcap`. File timestamps are configured before the capability is applied,
so setup does not accidentally clear the attribute before the observation.

The exact `getcap -n` output must be nonempty and identical before and after
directory normalization.

## Cleanup contract

The cleanup path:

1. attempts `sudo umount` when the tmpfs is active;
2. rechecks the exact mountpoint;
3. assigns a nonzero cleanup result if the mount still exists even when `umount`
   returned zero;
4. returns before recursive deletion when the mount remains;
5. removes the runtime only after the mount is gone.

Ordinary EXIT, INT 130, and TERM 143 have explicit handlers. The workflow also
checks that the runtime and exact mountpoint do not survive each run.

## Rerun and receipts

The dedicated workflow:

- installs `acl` and `libcap2-bin`;
- checks Bash/Python syntax;
- executes the complete synthetic matrix;
- executes the static probe-contract regression;
- runs the real probe as `first` and `rerun`;
- requires zero runtime and mount residue after each;
- retains `first.txt` and `rerun.txt` through an Actions artifact.

Each receipt includes schema version, device identities, before/after mtimes,
ACL/capability preservation, active-mount observation, and sentinel
preservation.

## Review repairs before execution

Self-review repaired three harness defects before the first hosted run:

1. generic HOME overlap logic rejected the normal hosted `RUNNER_TEMP` placement;
2. applying a file capability before a later `touch` made setup itself capable of
   clearing the attribute;
3. an unmount failure could fall through into recursive cleanup of a still-mounted
   path.

A fourth repair makes the active-mount refusal explicitly nonzero even if the
`umount` command returned success while the recheck still sees the mount.

These are harness findings, not product results.

## Evidence boundary

Established if the exact workflow passes:

- real tmpfs device pruning;
- real ACL preservation;
- real file-capability preservation;
- safe unmount-before-delete cleanup;
- immediate second clean run.

Not established:

- bind mounts with the same device number;
- overlay, FUSE, autofs, or mount replacement races;
- SELinux/AppArmor labels;
- permission-denied result precedence in product code;
- sparse archive layout;
- directory-format output;
- product source insertion;
- real Debian package-matrix recovery after case 242.

## Next decision

A green exact head clears the major real-metadata premises for a bounded product
candidate. The next product unit should:

1. normalize only archive/image temporary trees;
2. run immediately after `setup()` and before tar;
3. preserve same-device and symlink rules;
4. define timestamp-change failure precedence;
5. apply to both root and chrootless modes;
6. retain the current directory-output contract unchanged;
7. run the focused real sid `chrootless` case before the remaining package
   matrix.

## Authority

Internal disposable hosted filesystem evidence only. No Debian/mmdebstrap
upstream contact, package publication, release, deployment, or merge to `main`
is included or authorized.
