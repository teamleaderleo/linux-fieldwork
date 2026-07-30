# tarfilter path exclusions and hard-link target ownership

## TL;DR

`mmdebstrap`'s `tarfilter` decides whether to keep each archive member by its own path. A hard-link entry contains no file bytes; it points at another archive member through `linkname`. Excluding the data-bearing target while retaining the link member can therefore produce a dangling archive entry that GNU tar rejects during the next pipeline stage.

Dpkg documents path filters as current-object-only decisions and warns that selected exclusions can cause later unpack failures. This investigation therefore begins as a compatibility and diagnosability map. Promotion to a tarfilter defect requires evidence that mmdebstrap promises a stronger successful-output contract for this case.

## Explain like I'm five

An archive has two labels for one box. One label owns the box. The other label says, “use the first label's box.” The filter throws away the first label and keeps the second, leaving an instruction that points nowhere. The later unpack step finds the broken instruction and stops.

## Why care

Mmdebstrap places this filter between `dpkg-deb` and GNU tar while building a root filesystem. The filter can exit 0 before GNU tar reports the dangling hard link. That result may follow the documented dpkg filter model, yet it still shifts the useful diagnostic into a later process. A precise compatibility record helps distinguish expected hazardous configuration from a filter implementation failure.

## Canonical records

- Investigation issue: #240
- Home lane: LF-14, archive extraction and metadata contracts
- Broad scout: `LF-SCOUT-FS-01`
- Working branch: `investigate/tarfilter-excluded-hardlink-target`
- Imported source: `upstream/mmdebstrap/tarfilter`
- Imported tarfilter blob at branch creation: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Imported mmdebstrap blob at branch creation: `41aa46f989a2660cebdb0138e0847cde25b269a3`
- Regression: `tests/test_tarfilter_excluded_hardlink_target.py`

## Exact source observation

The source evaluates `path_filter_should_skip(member)` from `member.name`. A skipped member is discarded immediately:

```python
for member in in_tar:
    if path_filter_should_skip(member):
        continue
```

Ordinary path exclusion has no dependency check for `member.linkname`.

A retained hard-link member is written without a payload:

```python
if member.isfile():
    ...
else:
    out_tar.addfile(member)
```

For a hard link, `member.isfile()` is false. The output relies on the named target member remaining in the archive.

## Exact mmdebstrap pipeline

When `/etc/dpkg/dpkg.cfg.d/99mmdebstrap` contains path rules, the imported main program converts them into tarfilter arguments and inserts the filter into the essential-package extraction pipeline:

```text
dpkg-deb --fsys-tarfile PACKAGE
  | tarfilter --path-exclude=... --path-include=...
  | tar -C ROOT --keep-directory-symlink --extract --file -
```

The parent waits for all three processes. A zero tarfilter status followed by a nonzero GNU tar status becomes `tar --extract failed`. This preserves overall failure while assigning the final diagnostic to the extraction stage.

## Dpkg intent boundary

Dpkg's `--path-exclude` documentation states that filters know only the object currently being filtered and have no visibility into later archive objects. It warns that exclusions can break the installed system and gives a directory example where later children fail to unpack.

That documented model supports independent per-member filtering as an intentional compatibility baseline. It does not answer every hard-link question: a target may appear earlier, a link may appear first, and dependency-aware filtering could still be a deliberate mmdebstrap enhancement. The first reproduction therefore establishes behavior and diagnostic ownership, not an automatic bug verdict.

## Bounded question

When a path rule removes the data-bearing member of a hard-link pair while retaining the link member:

1. what exact archive does tarfilter emit;
2. where does the mmdebstrap-style pipeline fail;
3. does this match dpkg's documented current-object filter model;
4. is a more precise tarfilter diagnostic or dependency policy justified?

## Fixture and negative control

The test creates a PAX archive with:

- regular member `root/base`, containing `hard-link-payload\n`;
- hard-link member `root/peer`, with `linkname=root/base`.

Direct GNU tar extraction must:

- return 0;
- produce both paths with identical bytes;
- preserve one inode relationship.

The filtered path runs:

```text
python3 upstream/mmdebstrap/tarfilter --path-exclude=/root/base
```

The probe records the filtered member table and asks GNU tar to extract it.

## Distinguishing outcomes

- target and dependent hard link both absent: dependency-aware filtering;
- peer retained and extractable with bytes: materialized or retargeted result;
- peer retained, target absent, extraction failure: documented hazardous filter result or missing dependency handling;
- filter rejects the dependency before output: explicit failure boundary.

The test encodes the source-visible third outcome as the current characterization. Exact CI decides whether GNU tar and the checked-out source exhibit it together.

## Candidate design space

A stronger policy would require an explicit hard-link dependency contract. Plausible directions are:

1. retain current per-member semantics and improve the investigation/docs only;
2. detect a retained hard link whose already-seen target was excluded and fail with a focused diagnostic;
3. skip a retained hard-link member when its target is known to be excluded;
4. materialize the hard-link as a regular file when the target appeared earlier and its bytes remain available;
5. buffer dependency state and resolve hard-link groups after reading more of the stream.

Options 2–5 extend or alter dpkg-compatible path-filter semantics and streaming behavior. Selection requires a broader ordering matrix and source-intent review.

## Next matrix

After the first exact execution, test:

- target before link;
- link before target;
- several hard-link peers;
- hard-link chains;
- exclude followed by re-include;
- target removal by `--type-exclude`;
- path transforms combined with exclusions;
- a minimal dpkg unpack control in an isolated root.

A strong defect candidate needs a scenario accepted by documented configuration practice or a mismatch between tarfilter and dpkg behavior. A result confined to explicitly hazardous path selection belongs as a retained compatibility note or improved diagnostic proposal.

## Cleanup and rerun

The probe creates one temporary archive and two extraction directories below `TemporaryDirectory`. It invokes only the checked-out Python source and GNU tar, creates no device nodes or privileged metadata, and leaves no persistent output.

A later candidate must rerun the same pathname immediately after the failing case and prove clean extraction without retained temporary state.

## Evidence boundary

The first probe covers one target-before-link PAX archive under an ordinary user. It does not yet establish:

- direct dpkg unpack behavior for the same member order;
- reverse member ordering;
- hard-link chains or several peers;
- path includes that restore the target;
- transforms or type filters combined with exclusions;
- cross-extractor behavior;
- privileged ownership, xattrs, ACLs, capabilities, or device nodes.

Source inspection demonstrates the ownership mechanism and pipeline placement. Exact behavior remains `execution-pending` until repository CI runs the retained test. Dpkg documentation establishes the intended current-object visibility boundary; it does not settle whether mmdebstrap should add an earlier diagnostic.

## Authority

Internal Linux Fieldwork investigation only. No Debian or external upstream contact is authorized or included.

## Disposition

**EXECUTE AND CLASSIFY.** Run the exact branch through Linux Fieldwork CI. A passing characterization establishes a reproducible dpkg-compatible hazard. Promote only after the broader matrix or source intent supports a stronger invariant; otherwise retain the result as a compatibility and diagnostic record.
