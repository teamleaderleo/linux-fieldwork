# mmdebstrap root/chrootless directory-mtime comparison

Tracking: #380

## TL;DR

The real Debian sid package test built root and chrootless tarballs with the same
files and file bytes, but 123 directory timestamps differed. A focused GNU tar
matrix shows that full timestamp normalization is too broad, while real-directory
normalization before tar can converge archive bytes and preserve package file
mtimes.

Cross-context review found one evidence defect in the first matrix: `Path.is_dir()`
follows symlinks, so a symlink to a directory could have its own timestamp changed
while the helper still called the policy “directory-only.” The repaired matrix
uses `lstat` type identity and proves symlink, hard-link, regular-file, and outside
target metadata remain unchanged.

This is still an evidence-only comparison. No product policy is selected yet.

## Explain like I'm five

Two workers built the same box with the same files. One wrote today's date on
folders; the other kept older package folder dates. The boxes therefore differ
byte-for-byte even though the contents match.

The first proposed ruler also mistook a shortcut pointing to a folder for a real
folder. The repaired ruler checks what the object itself is before changing its
date.

## Why care

The existing `chrootless` test requires root and chrootless tarballs to be
byte-identical. Ignoring directory timestamps could weaken a real reproducibility
contract. Normalizing every timestamp would destroy legitimate package file
metadata. A so-called directory-only repair must also avoid changing symlink or
outside-target metadata.

## Real-system anchor

PR #361 exact head `c2b7c43a4b6ce883f6dcdbef8d489bcf48323266`
ran Linux Fieldwork CI `30640356619` / 999. The disposable Debian sid package
matrix completed 154 tests and stopped at `(242/284) chrootless`.

Artifact `8798679560`, digest
`sha256:50d8ab7a20cb241ff9821b35329508ecdb0c58cbd3dec348c18d68d1dfe7a244`,
contains the first failure.

Diffoscope reported the same 123 paths on both sides. Every path was a directory.
Names, types, modes, uid/gid, and sizes matched. Only directory mtimes differed.
Regular files and file contents did not appear in the delta.

The tested mmdebstrap source creates archives with:

```text
--mtime=@$SOURCE_DATE_EPOCH
--clamp-mtime
```

GNU tar therefore changes newer directory mtimes to the selected epoch while
retaining older package-owned mtimes.

## Focused policy matrix

`tests/test_mmdebstrap_chrootless_directory_mtime.py` creates two otherwise
identical trees:

- the root-mode analogue has directory mtimes newer than the epoch;
- the chrootless analogue has directory mtimes older than the epoch;
- one regular file has an intentionally older package mtime that must remain
  observable;
- file bytes, names, modes, and ownership headers are identical.

It then runs GNU tar with the relevant mmdebstrap reproducibility options,
including sorted PAX output and removal of atime/ctime PAX fields.

| Policy | Archives converge | Package file mtime preserved | Interpretation |
| --- | --- | --- | --- |
| `--mtime` plus `--clamp-mtime` | no | yes | reproduces directory-only divergence |
| full `--mtime`, no clamp | yes | no | too broad for a narrow repair |
| normalize real directories, then clamp | yes | yes | promising mechanism class |
| normalize only comparison manifests | comparison only | yes | explains result but leaves product bytes different |

## Review repair — object identity before timestamp mutation

The first helper collected paths with:

```python
path.is_dir()
```

That follows symlinks. A symlink to a directory could enter the normalization
set even though `os.utime(..., follow_symlinks=False)` then changes the symlink
object rather than the directory target.

The repaired helper classifies each candidate with `lstat` and selects only
`stat.S_ISDIR(...)` objects. Its reversing control adds:

- a symlink to an outside directory with its own old mtime;
- an outside directory and sentinel file whose mtimes must not change;
- a hard link to the package payload;
- the original regular file mtime and inode relationship.

After normalization:

- only real in-tree directory mtimes change;
- symlink mtime and link target remain unchanged;
- outside directory and sentinel mtimes remain unchanged;
- regular file and hard-link mtimes remain package-owned;
- the hard-link inode relationship remains intact;
- root/chrootless archive bytes converge;
- the tar archive retains the symlink and hard-link member types.

This closes the immediate symlink-identity hole in the evidence model. It does
not prove a safe product implementation across mount points or every metadata
class.

## Current interpretation

Real-directory-only normalization is the only tested policy that converges the
archive bytes while preserving the deliberately old regular-file, symlink, and
hard-link controls.

That does not yet make it a product patch. Before modifying mmdebstrap, the next
candidate must answer:

- whether mutating temporary-tree directory mtimes is safe for all output formats
  and permissions;
- whether normalization should occur only for archive output;
- how mount boundaries are detected rather than traversed;
- whether xattrs, ACLs, capabilities, sparse files, and package script
  expectations remain unchanged;
- whether a streaming header rewrite would repeat LF-14's sparse-member
  corruption class;
- whether root/chrootless byte identity is the intended public contract or only
  an internal test assumption.

## Stop rule

Retain this evidence-only matrix until one product candidate adds reversing
controls for mount boundaries, xattrs/ACLs/capabilities, sparse members,
directory-format output, failure cleanup, and a second clean run. Do not weaken
the real test to ignore directory mtimes without an explicit contract decision.

## Authority

Internal source copies, retained artifacts, and synthetic local/hosted controls
only. No upstream contact, publication, package change, deployment, or merge is
authorized by this investigation.
