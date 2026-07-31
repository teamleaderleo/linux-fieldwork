# Directory mtime normalization metadata boundary

Tracking: issue #380, PR #383, symlink repair PR #386, device repair PR #388.

## TL;DR

A real-directory-only timestamp policy should not rewrite regular-file metadata or
payload layout. This stacked evidence repair adds two reversing controls:

- user extended attributes on one real directory and one package file;
- a sparse regular file with fixed logical bytes, size, allocation, mode-time
  boundary, and archive content.

The controls show that the focused directory walk changes directory mtimes only:
source xattrs remain present, package file mtime remains package-owned, and each
sparse file keeps its own logical bytes, size, block allocation, and mtime.

The tar fixture now includes `--xattrs`, matching current mmdebstrap archive
creation, and proves the user xattrs survive into PAX headers.

This remains evidence-only. ACLs, capabilities, real mount behavior, sparse
archive layout, product insertion, failure cleanup, and directory-format output
remain open.

## Explain like I'm five

Changing folder dates should not erase labels attached to folders or files, and
it should not fill in the empty middle of a sparse file.

The test checks the labels and the file's empty-space layout before and after the
folder-date operation.

## Why care

A metadata repair can create a reproducible tarball while silently damaging
properties that another consumer relies on. Simple byte and pathname equality
would miss:

- extended attributes;
- sparse allocation;
- package-owned file timestamps;
- directory-versus-file mutation scope.

This is the same compatibility lesson seen in prior archive investigations:
correct logical bytes do not imply correct metadata or allocation behavior.

## Exact source context

Current mmdebstrap tar creation uses:

```text
--sort=name
--mtime=@$SOURCE_DATE_EPOCH
--clamp-mtime
--numeric-owner
--one-file-system
--format=pax
--xattrs
```

The focused test mirrors those relevant options.

## User xattr control

When supported by the fixture filesystem, both root-mode and chrootless
analogues receive:

```text
user.linux-fieldwork=directory-mtime-control
```

on:

- `usr/share/demo`;
- `usr/share/demo/payload`.

After real-directory normalization, the test requires:

- both source xattrs still equal the original bytes;
- the regular payload mtime remains package-owned;
- root/chrootless tarballs converge;
- both archive members contain the PAX key
  `SCHILY.xattr.user.linux-fieldwork` with the original value.

If the local filesystem or account does not support user xattrs, only this
focused control is skipped and the limitation remains visible.

## Sparse source control

Each tree receives a 4 MiB regular file with data only at the beginning and end.
The fixture requires that the filesystem actually reports sparse allocation;
otherwise the focused control skips rather than making a false sparse claim.

Before normalization, the test records per tree:

- logical size;
- allocated block count;
- mtime;
- SHA-256 of logical bytes.

After normalization, each file must match its own recorded tuple exactly.
Logical hashes must also agree across root and chrootless trees.

The archive comparison then requires:

- byte-identical root/chrootless tarballs;
- sparse member logical size 4 MiB;
- package-owned member mtime;
- logical payload hash unchanged.

The test deliberately does **not** claim the tar archive preserves sparse
allocation or GNU sparse PAX metadata because current mmdebstrap tar invocation
does not pass `--sparse` in this path. Sparse archive-layout preservation remains
a separate product compatibility question.

## Why allocation is compared per file

Two independently created sparse files may consume different block counts even
when their logical bytes are identical. Cross-file allocation equality is not a
stable product contract.

The relevant invariant is:

```text
root sparse allocation before == root sparse allocation after
chrootless sparse allocation before == chrootless sparse allocation after
```

while the logical bytes agree across both trees.

## Evidence boundary

Established for the synthetic same-device fixture:

- directory normalization preserves selected user xattrs;
- selected xattrs survive product-like PAX archive creation;
- regular file mtime remains unchanged;
- sparse source logical size, allocation, mtime, and bytes remain unchanged;
- archive logical bytes and metadata converge across root/chrootless analogues.

Not established:

- POSIX ACLs;
- `security.capability` or other privileged xattrs;
- SELinux/AppArmor labels;
- ownership and permission failures during timestamp changes;
- sparse archive allocation or GNU sparse headers;
- real mount boundaries;
- concurrent replacement races;
- directory-format output;
- failure cleanup and immediate product rerun;
- product source insertion.

## Next discriminator

Before a product patch is selected:

1. compose symlink, same-device, xattr, and sparse-source controls;
2. run one disposable privileged real-mount control;
3. add ACL and file-capability controls where runner support is explicit;
4. select an archive-only insertion point immediately before tar;
5. define error precedence if any directory timestamp change fails;
6. prove cleanup and a second clean archive run;
7. rerun the real sid `chrootless` case before the remaining package matrix.

## Authority

Internal synthetic filesystem/archive evidence only. No Debian/mmdebstrap
upstream contact, package publication, release, deployment, or merge to `main`
is included or authorized.
