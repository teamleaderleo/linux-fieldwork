# tarfilter path exclusions and hard-link target ownership

## TL;DR

`mmdebstrap`'s `tarfilter` decides whether to keep each archive member by its own path. A hard-link entry contains no file bytes; it points at another archive member through `linkname`. The current source can therefore exclude the data-bearing target, retain the hard-link entry, exit 0, and emit an archive whose only remaining file points at a missing member.

The retained probe compares a valid two-name hard-link archive with the result of `--path-exclude=/root/base`. Exact repository execution is pending on the investigation branch.

## Explain like I'm five

An archive has two labels for one box. One label owns the box. The other label says, “use the first label's box.” The filter throws away the first label and keeps the second, leaving an instruction that points nowhere.

## Why care

Path exclusions are used while constructing root filesystem archives. A successful filter command followed by an extraction failure moves the error into a later bootstrap or image stage. That makes cancellation, cleanup, and diagnosis harder, and the produced archive no longer satisfies the ordinary expectation that successful filtering yields an extractable stream.

## Canonical records

- Investigation issue: #240
- Home lane: LF-14, archive extraction and metadata contracts
- Broad scout: `LF-SCOUT-FS-01`
- Working branch: `investigate/tarfilter-excluded-hardlink-target`
- Imported source: `upstream/mmdebstrap/tarfilter`
- Imported blob at branch creation: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Regression: `tests/test_tarfilter_excluded_hardlink_target.py`

## Exact source observation

The source evaluates `path_filter_should_skip(member)` from `member.name`. A skipped member is discarded immediately:

```python
for member in in_tar:
    if path_filter_should_skip(member):
        continue
```

Later path rewriting changes member names and hard-link targets in repaired transform paths, while ordinary path exclusion has no dependency check for `member.linkname`.

A retained hard-link member is written without a payload:

```python
if member.isfile():
    ...
else:
    out_tar.addfile(member)
```

For a hard link, `member.isfile()` is false. The output therefore relies on the named target member remaining in the archive.

## Bounded question

When a path rule removes the data-bearing member of a hard-link pair while retaining the link member, does the filtered archive stay internally coherent and extractable?

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

The probe then records the filtered member table and asks GNU tar to extract it.

## Distinguishing outcomes

- target and dependent hard link both absent: dependency-aware filtering;
- peer retained and extractable with bytes: materialized or retargeted result;
- peer retained, target absent, extraction failure: dangling hard-link output;
- filter rejects the unsupported dependency: explicit failure boundary.

The test currently encodes the source-visible third outcome as the expected characterization. Exact CI decides whether GNU tar and the checked-out source exhibit it together.

## Candidate design space

A repair needs an explicit hard-link dependency policy. Plausible directions are:

1. skip a retained hard-link member when its target is excluded;
2. materialize the hard-link as a regular file when the target appeared earlier and its bytes remain available;
3. buffer dependency state and resolve hard-link groups after reading more of the stream;
4. reject a retained hard link whose target is filtered out.

Each direction changes path-filter semantics. The next step after reproduction is to compare dpkg's path-exclude behavior and test target-before-link, link-before-target, chains, multiple peers, and include-after-exclude rules before selecting a candidate.

## Cleanup and rerun

The probe creates one temporary archive and two extraction directories below `TemporaryDirectory`. It invokes only the checked-out Python source and GNU tar, creates no device nodes or privileged metadata, and leaves no persistent output.

A later candidate must rerun the same pathname immediately after the failing case and prove clean extraction without retained temporary state.

## Evidence boundary

The first probe covers one target-before-link PAX archive under an ordinary user. It does not yet establish:

- dpkg package-unpack parity;
- reverse member ordering;
- hard-link chains or several peers;
- path includes that restore the target later;
- transforms combined with exclusions;
- cross-extractor behavior;
- privileged ownership, xattrs, ACLs, capabilities, or device nodes.

Source inspection supports the ownership hypothesis. Exact behavior remains `execution-pending` until repository CI runs the retained test.

## Authority

Internal Linux Fieldwork investigation only. No Debian or external upstream contact is authorized or included.

## Disposition

**EXECUTE.** Run the exact branch through Linux Fieldwork CI, classify the observed member table and GNU tar result, then compare dpkg semantics before choosing a repair.