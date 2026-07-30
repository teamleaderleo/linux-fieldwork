# LF-SCOUT-FS-01 — Archive extraction and metadata contracts

## In simple words

The first LF-14 corpus now covers nine ordinary archive features with generated,
auditable fixtures. GNU tar handled the reference archives as expected. The
mmdebstrap tar filter preserved containment behavior, hard links, numeric owner
headers, modes, timestamps, and an ordinary `user.*` xattr. Its rewrite of a
GNU PAX sparse member produced an archive that GNU tar could list only with an
error and could not extract. Python's tar reader also rejected the rewritten
member. The result is **promote** for a focused local investigation of sparse
member handling.

## Scout identity and home lane

- Scout-ID: `LF-SCOUT-FS-01`
- Home lane: `LF-14`
- Working branch: `scout/lf-scout-fs-01/lf-14-archive-metadata-contracts`
- Assignment issue: `#14`
- Reviewer: `LF-SCOUT-DEB-01`
- Cross-review duty: `LF-SCOUT-DEB-02` on `LF-12` after `READY FOR REVIEW`

## Exact source or package boundary

The tested repository source is:

- `upstream/mmdebstrap/tarfilter`
- repository base commit: `b8cb602d832f5eec6a5993a21bbb1d536a60098d`
- tarfilter blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`

The active path was forced by passing a non-matching path exclusion. That makes
the filter parse every input member and emit a new PAX archive, while retaining
all fixtures:

```sh
python3 upstream/mmdebstrap/tarfilter \
  --path-exclude=/__lf14_never_match__ < fixture.tar > filtered.tar
```

The reference extractor is GNU tar. The probe does not cover mmdebstrap's full
bootstrap flow, package download, or later image conversion stages.

## Environment and privileges

The retained first run used:

- Linux on an ext-family filesystem;
- Python `3.13.5`;
- GNU tar `1.35`;
- effective uid/gid `65534:65534` via `setpriv`;
- no root-only extraction operation;
- ordinary `user.lf14` extended attributes.

The repository CI test runs the same generator and probe against the checked-out
`upstream/mmdebstrap/tarfilter` on Ubuntu 24.04. Numeric ownership is compared in
archive headers; unprivileged extraction correctly creates files as the caller.

## Source and test map

| Area | Source or artifact | Purpose |
|---|---|---|
| Filter under test | `upstream/mmdebstrap/tarfilter` | Parse and rewrite every fixture as PAX |
| Fixture generator | `artifacts/generate-fixtures.py` | Create nine minimal archives repeatably |
| Probe runner | `artifacts/run-probes.py` | Rewrite, extract, compare, and retain logs |
| CI regression | `tests/test_lf14_archive_corpus.py` | Require the reference path to pass and isolate the sparse failure |
| First retained run | `artifacts/observed-python3.13-unprivileged/` | Matrix, metadata comparison, and diagnostics |

## Corpus design and expected behavior

Each feature has one minimal archive. The expected behavior was written into the
probe before extraction.

| Fixture | Minimal member design | Expected extraction behavior |
|---|---|---|
| traversal | regular file named `../lf14-traversal-escape` | reject; create nothing outside target |
| absolute | regular file named `/lf14-absolute-escape` | strip leading slash; create beneath target |
| symlink | `pivot -> ../lf14-symlink-outside`, then `pivot/payload` | preserve link entry; refuse to follow it outside target |
| hard link | `hard/base` plus `hard/peer` linked to it | extract both names with one inode relationship |
| sparse file | 8 MiB logical file with three short data extents | preserve bytes and sparse allocation |
| numeric ownership | uid `12345`, gid `23456` in header | preserve numeric header values; extraction follows caller privilege |
| mode bits | regular file mode `0751` | preserve mode `0751` |
| timestamps | mtime `946684800` | preserve `2000-01-01T00:00:00Z` |
| xattr | PAX `SCHILY.xattr.user.lf14=corpus` | restore `user.lf14=corpus` with GNU tar `--xattrs` |

The generator uses Python `tarfile` for crafted paths, links, owner fields,
modes, timestamps, and PAX xattr headers. GNU tar `--format=pax --sparse` creates
the sparse fixture so its GNU sparse map is genuine.

## Probe design and distinguishing outcomes

For every fixture the runner creates two extraction paths:

1. direct extraction of the generated archive with GNU tar;
2. rewrite through mmdebstrap `tarfilter`, followed by the same GNU tar command.

Containment checks inspect sibling paths after extraction. Link checks compare
inode numbers and link counts. Sparse checks compare logical size with allocated
512-byte blocks. Archive manifests compare names, types, sizes, uid/gid, modes,
mtimes, link targets, PAX headers, and Python's parsed sparse map. Filesystem
checks compare extracted ownership, modes, mtimes, inode relationships,
allocation, and `user.lf14`.

The useful distinguishing outcomes were:

- reference failure plus filtered failure: fixture or extractor contract issue;
- reference pass plus filtered pass: filter preserved the tested contract;
- reference pass plus filtered failure: filter rewrite changed or corrupted the
  contract;
- both extract but filtered allocation expands: sparse representation loss.

## Generator and commands

Generate and run the complete corpus from the repository root:

```sh
python3 programmes/filesystems-images/lanes/LF-14-archive-extraction-metadata-contracts/scouts/LF-SCOUT-FS-01/artifacts/run-probes.py \
  --repo-root "$PWD" \
  --output /tmp/lf14-run
```

The runner records:

- `environment.json`;
- generated `fixtures/` and rewritten `filtered/` archives;
- `archive-manifests.json`;
- `extraction-results.json`;
- `extraction-matrix.md`;
- `metadata-comparison.md`;
- per-case stdout and stderr under `logs/`;
- exact commands in `commands.txt`.

The generated binary archives stay out of git. They are deterministic enough to
rebuild from the small generator, while the retained text captures the observed
comparison.

## Extraction matrix

The retained ordinary-user run produced 18 path/fixture combinations:

- GNU tar direct: 9 of 9 contracts passed;
- mmdebstrap tarfilter then GNU tar: 8 of 9 contracts passed;
- sole failure: `mmdebstrap-tarfilter / sparse`.

Key observations:

| Path | Fixture | Result | Observation |
|---|---|---|---|
| direct | traversal | pass | GNU tar rejected `..`; no sibling file appeared |
| filtered | traversal | pass | same rejection and containment |
| direct | absolute | pass | leading slash removed; file stayed under target |
| filtered | absolute | pass | same containment |
| direct | symlink | pass | payload extraction failed with `Not a directory`; outside target stayed empty |
| filtered | symlink | pass | same containment |
| direct | hard link | pass | both names shared one inode |
| filtered | hard link | pass | relationship preserved |
| direct | sparse | pass | logical `8,388,611` bytes; allocated `12,288` bytes |
| filtered | sparse | **fail** | extraction exited 2 and produced no file |
| direct/filtered | owner, mode, time, xattr | pass | header and supported filesystem metadata survived |

The full table is retained at
`artifacts/observed-python3.13-unprivileged/extraction-matrix.md`.

## Metadata comparison method

The archive-side manifest uses Python `tarfile` and records each member's core
fields, PAX headers, and parsed sparse map. If Python cannot parse an archive,
the runner also asks GNU tar to list it and retains both diagnostics.

The extracted-tree comparison uses `lstat`, inode and link counts, uid/gid,
permission bits, integer mtime, logical size, `st_blocks * 512`, symlink target,
and `os.getxattr` for `user.lf14`.

This combination catches byte-visible metadata changes and filesystem effects.
It also separates numeric owner preservation in the archive from ownership that
an ordinary extractor is authorized to apply.

## Observed results and discrepancies

Eight filtered fixtures preserved their tested contract. Core archive fields
matched before and after filtering for traversal, absolute path, symlink, hard
link, numeric ownership, mode bits, and timestamps. The xattr PAX header stayed
`SCHILY.xattr.user.lf14=corpus`, and GNU tar restored it.

The sparse fixture changed decisively:

- original parsed sparse map:
  `[(0, 4096), (1048576, 4096), (8388608, 3), (8388611, 0)]`;
- filtered parsed sparse map: absent;
- Python reader error:
  `ValueError: not enough values to unpack (expected 2, got 1)`;
- GNU tar listing/extraction error:
  `numeric overflow in sparse archive member`;
- filtered extraction result: exit 2, no output file.

The source loop copies `member.pax_headers` and passes the extracted logical file
stream to `addfile`. GNU sparse 1.0 stores its sparse map in data preceding the
file extents. Re-emitting the member while retaining GNU sparse PAX keys can
therefore pair stale sparse metadata with a newly written data stream. The
observed malformed output follows that mechanism. This is an interpretation
from the source and the two independent reader failures.

## Unsupported and privilege-dependent extension

The first corpus intentionally leaves these for a later privileged extension:

- ACLs and default ACLs;
- `security.capability` and other `security.*` xattrs;
- `trusted.*` xattrs;
- device nodes and FIFOs requiring special handling;
- ownership application as root across multiple uid/gid mappings;
- immutable or append-only flags;
- restricted target filesystems without xattr or sparse support;
- libarchive, `dpkg-deb`, container unpackers, and image conversion tools.

The ordinary xattr case covers only `user.*`. Tar archives preserve mtime; this
probe makes no claim about ctime or birth time.

## Interpretation

Containment behavior remained with GNU tar in both paths for traversal,
absolute names, and the archive-created symlink. The filter preserved the
ordinary metadata contracts represented here except GNU PAX sparse members.

The sparse result crosses the lane's promotion threshold: a reference archive
extracts correctly, while a pass through the repository's tar filter yields an
unextractable member without the filter command itself reporting failure. A
focused investigation should reduce the sparse formats involved, confirm the
Python versions affected, and decide whether to reject sparse input precisely,
strip/rebuild GNU sparse headers, or preserve sparse encoding correctly.

## Evidence limits

- The retained first run used Python 3.13.5 and GNU tar 1.35 on one Linux
  filesystem.
- The direct and filtered extraction endpoint was GNU tar.
- The local retained run exercised the same parse/addfile rewrite path; the CI
  regression executes the checked-out repository file directly.
- No concurrent symlink race was attempted; the fixture covers deterministic
  archive ordering.
- Sparse allocation thresholds allow filesystem block-size variation.
- No claim extends to privileged metadata or other unpackers.
- No upstream version comparison or contact was performed.

## Promotion or stop decision

**Decision: `promote`.**

Promote a narrow follow-up around `upstream/mmdebstrap/tarfilter` and GNU PAX
sparse 1.0 members. Retain the full corpus because the eight passing cases form
a reusable compatibility baseline and the sparse case is a stable regression
probe.

## Upstream authority state

No upstream contact is authorized. No external issue, email, merge request,
patch submission, or tracker comment was made. All findings remain inside
`teamleaderleo/linux-fieldwork`.
