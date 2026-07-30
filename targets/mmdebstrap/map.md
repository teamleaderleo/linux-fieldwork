# mmdebstrap Target Map

## In simple words

`mmdebstrap` creates Debian root filesystems through several privilege and isolation modes. Linux Fieldwork carries an exact imported source tree and retained investigations, making it the first active formal target.

## Source identity

- Canonical repository: `https://salsa.debian.org/debian/mmdebstrap.git`
- Imported revision: `debian/1.5.7-3`
- Resolved commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Local source: [`../../upstream/mmdebstrap/`](../../upstream/mmdebstrap/)
- Import metadata: [`../../upstream/mmdebstrap/.linux-fieldwork-source.json`](../../upstream/mmdebstrap/.linux-fieldwork-source.json)

## Why it recurs

The project crosses Debian package installation, privilege modes, user namespaces, tar and directory output, temporary storage, hooks, subprocess control, architecture support, mounts, and cleanup.

## Relevant programmes

- [`Rootless execution, namespaces, and mounts`](../../programmes/rootless-execution/STATUS.md)
- [`Filesystems, archives, and disk images`](../../programmes/filesystems-images/STATUS.md)
- [`Services, processes, and resources`](../../programmes/services-resources/STATUS.md)

## Mapped lanes

- [LF-02 — chrootless `DPKG_ROOT` containment](../../programmes/rootless-execution/lanes/LF-02-chrootless-dpkg-root-containment/brief.md)
- [LF-14 — archive extraction and metadata contracts](../../programmes/filesystems-images/lanes/LF-14-archive-extraction-metadata-contracts/brief.md)
- [LF-23 — cancellation, subprocess, and file-descriptor cleanup](../../programmes/services-resources/lanes/LF-23-cancellation-subprocess-fd-cleanup/brief.md)

## Existing investigations

- [`mmdebstrap` explicit `TMPDIR` handling](../../investigations/mmdebstrap-unwritable-tmpdir/README.md)
- [Debian autopkgtest `#1141078` transition triage](../../investigations/mmdebstrap-autopkgtest-1141078-transition-triage/README.md) — recovered `dev-ptmx`/`bsdutils` test-fixture owner, coordination issue #53

## Source and test surfaces

Begin with the main `mmdebstrap` executable, mode selection, temporary-directory creation, hook execution, tar filtering, child-process orchestration, cleanup paths, and the upstream test registry. Preserve exact imported revisions for every claim.

## Policy boundary

The local imported tree is a research and candidate-patch workspace. No Debian issue, email, merge request, patch submission, comment, or review is authorized by this map.
