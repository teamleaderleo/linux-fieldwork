# LF-14 archive corpus artifacts

`generate-fixtures.py` creates one minimal archive for traversal, absolute paths,
symlink escape, hard links, sparse files, numeric ownership, modes, timestamps,
and an ordinary `user.*` xattr. Generated archives stay out of git because the
generator is deterministic and easier to audit than binary fixtures.

`run-probes.py` regenerates the corpus, rewrites every archive through
`upstream/mmdebstrap/tarfilter` with a deliberately non-matching path filter,
extracts both original and rewritten archives with GNU tar, and emits JSON plus
Markdown comparisons.

Run from the repository root:

```sh
python3 programmes/filesystems-images/lanes/LF-14-archive-extraction-metadata-contracts/scouts/LF-SCOUT-FS-01/artifacts/run-probes.py \
  --repo-root "$PWD" \
  --output /tmp/lf14-run
```

The runner exits 1 when any extraction contract fails. The retained
`observed-python3.13-unprivileged/` directory records the first ordinary-user
run. It used uid/gid 65534, GNU tar 1.35, and Python 3.13.5.
