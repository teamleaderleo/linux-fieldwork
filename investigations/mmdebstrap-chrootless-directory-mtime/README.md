# mmdebstrap root/chrootless directory-mtime comparison

Tracking: #380

## In simple words

The real Debian sid package test built the same root filesystem in root and
chrootless modes. The file set and file bytes matched, but directory dates did
not. Because tar stores directory dates, the two archives were not byte-for-byte
identical.

This investigation separates four policies before changing product source:

1. keep the current clamp policy;
2. normalize every member timestamp;
3. normalize directory timestamps before the final tar operation;
4. ignore directory timestamps only while comparing test output.

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

It then runs GNU tar with the exact relevant mmdebstrap reproducibility options,
including sorted PAX output and removal of atime/ctime PAX fields.

Observed synthetic outcomes:

| Policy | Archives converge | Package file mtime preserved | Interpretation |
| --- | --- | --- | --- |
| `--mtime` plus `--clamp-mtime` | no | yes | reproduces directory-only divergence |
| full `--mtime`, no clamp | yes | no | too broad for a narrow repair |
| normalize directories, then clamp | yes | yes | promising mechanism class |
| normalize only comparison manifests | comparison only | yes | explains result but leaves product bytes different |

## Current interpretation

Directory-only normalization is the only tested policy that both converges the
archive bytes and preserves the deliberately old regular-file timestamp.

That does not yet make it a product patch. Before modifying mmdebstrap, the next
candidate must answer:

- whether touching every directory in the temporary root is safe for all output
  formats and permissions;
- whether normalization should occur only for archive output;
- whether symlinks, mount boundaries, xattrs, ACLs, hard links, and package
  maintainer-script expectations remain unchanged;
- whether a streaming header rewrite would repeat LF-14's sparse-member
  corruption class;
- whether root/chrootless byte identity is the intended public contract or only
  an internal test assumption.

## Stop rule

Retain this evidence-only matrix until one product candidate adds reversing
controls for ordinary files, links, xattrs, sparse members, directory output,
and a second clean run. Do not weaken the real test to ignore directory mtimes
without an explicit contract decision.

## Authority

Internal source copies, retained artifacts, and synthetic local/hosted controls
only. No upstream contact, publication, package change, deployment, or merge is
authorized by this investigation.
