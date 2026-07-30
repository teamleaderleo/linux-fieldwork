# tarfilter path exclusions and hard-link target ownership

## TL;DR

`mmdebstrap`'s `tarfilter` decides whether to keep each archive member by its own path. A hard-link entry contains no file bytes; it points at another archive member through `linkname`. Excluding the data-bearing target while retaining the link member can therefore produce a dangling archive entry that GNU tar rejects during the next pipeline stage.

Dpkg documents path filters as current-object-only decisions and warns that selected exclusions can cause later unpack failures. A direct disposable dpkg 1.22.22 control now reproduces the same target-excluded / hard-link-retained failure. This investigation is therefore a compatibility and diagnosability record unless a stronger mmdebstrap contract appears.

## Explain like I'm five

An archive has two labels for one box. One label owns the box. The other label says, “use the first label's box.” The filter throws away the first label and keeps the second, leaving an instruction that points nowhere. The later unpack step finds the broken instruction and stops.

## Why care

Mmdebstrap places this filter between `dpkg-deb` and GNU tar while building a root filesystem. The filter can exit 0 before GNU tar reports the dangling hard link. Direct dpkg fails on the same filter choice, so the core result follows dpkg compatibility. A precise record still helps users connect the later extraction error to the selected path rule and separates expected hazardous configuration from a tarfilter implementation failure.

## Canonical records

- Investigation issue: #240
- Investigation PR: #241
- Home lane: LF-14, archive extraction and metadata contracts
- Broad scout: `LF-SCOUT-FS-01`
- Working branch: `investigate/tarfilter-excluded-hardlink-target`
- Imported source: `upstream/mmdebstrap/tarfilter`
- Imported tarfilter blob at branch creation: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Imported mmdebstrap blob at branch creation: `41aa46f989a2660cebdb0138e0847cde25b269a3`
- Regression: `tests/test_tarfilter_excluded_hardlink_target.py`
- Direct dpkg control: `artifacts/dpkg-path-exclude-control.txt`

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

## Dpkg intent and parity

Dpkg's `--path-exclude` documentation states that filters know only the object currently being filtered and have no visibility into later archive objects. It warns that exclusions can break the installed system and gives a directory example where later children fail to unpack.

A direct local control used Debian dpkg 1.22.22, a disposable package, an isolated root, and an empty temporary dpkg database. The package contained:

```text
/usr/share/hardlink-filter-probe/base
/usr/share/hardlink-filter-probe/peer  -> same inode as base
```

The negative control `dpkg-deb -x` returned 0 and preserved the shared inode. Unpacking with:

```text
dpkg --path-exclude=/usr/share/hardlink-filter-probe/base --unpack probe.deb
```

returned 1 with:

```text
error creating hard link './usr/share/hardlink-filter-probe/peer': No such file or directory
```

The full command boundary and cleanup receipt are retained in `artifacts/dpkg-path-exclude-control.txt`.

This parity result establishes independent per-member filtering as the governing compatibility baseline for issue #240. It leaves a narrower enhancement question: whether tarfilter or mmdebstrap can report the selected rule and missing dependency earlier without changing dpkg semantics.

## Bounded question

When a path rule removes the data-bearing member of a hard-link pair while retaining the link member:

1. what exact archive does tarfilter emit;
2. where does the mmdebstrap-style pipeline fail;
3. does the result match direct dpkg behavior;
4. can the pipeline provide a more precise diagnostic while preserving compatibility?

## Fixture and negative control

The retained test creates a PAX archive with:

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

- target and dependent hard link both absent: dependency-aware filtering beyond direct dpkg;
- peer retained and extractable with bytes: materialized or retargeted result;
- peer retained, target absent, extraction failure: dpkg-compatible hazardous filter result;
- filter rejects the dependency before output: explicit stronger failure boundary.

The test encodes the source-visible third outcome as the current characterization. Exact CI decides whether GNU tar and the checked-out source exhibit it together.

## Candidate design space

The compatibility result narrows useful follow-up options:

1. retain current per-member semantics and preserve this investigation as a reusable warning;
2. enrich mmdebstrap's final extraction diagnostic with active path-filter context;
3. add an optional stricter tarfilter mode that rejects known dangling hard links;
4. document hard-link dependency risk beside path-filter configuration examples.

Automatic skipping, materialization, or buffering would diverge from direct dpkg behavior and needs an explicit product decision plus a larger ordering matrix.

## Reference ordering matrix

A local GNU tar control established:

- target before hard link: extraction succeeds and shares one inode;
- hard link before target: extraction fails even when the target appears later;
- target, peer, then chain: extraction succeeds with one inode;
- peer or chain before its target: extraction fails.

The retained tarfilter fixture deliberately uses target-before-link ordering so the unfiltered archive is a valid negative control. This matrix characterizes GNU tar only; it does not substitute for exact tarfilter execution.

## Next matrix

After the first exact tarfilter execution, useful compatibility branches are:

- exclude followed by re-include;
- several target-before-link peers;
- a target-before-peer-before-chain group;
- path transforms combined with exclusions;
- final diagnostic content in the complete mmdebstrap pipeline;
- package rules from real-world configurations that select this failure accidentally.

Target removal through `--type-exclude` moved to the separate tarfilter-specific issue #243 / PR #244.

## Cleanup and rerun

The retained Python probe creates one temporary archive and two extraction directories below `TemporaryDirectory`. It invokes only the checked-out Python source and GNU tar, creates no device nodes or privileged metadata, and leaves no persistent output.

The direct dpkg control used one temporary package tree, `.deb`, extraction root, installation root, and dpkg database. All were removed with the enclosing temporary directory.

Any diagnostic candidate must rerun the same logical output path immediately after the failing case and prove that retained temporary state does not alter a successful extraction.

## Evidence boundary

Established:

- tarfilter source ownership and mmdebstrap pipeline placement: source-read;
- dpkg current-object filter intent: documentation-read;
- direct dpkg hard-link failure under path exclusion: locally executed with dpkg 1.22.22;
- GNU tar ordering behavior: locally executed reference matrix.

Execution-pending:

- exact checked-out tarfilter member table and status through repository CI;
- complete mmdebstrap diagnostic under the same package fixture.

Still outside the boundary:

- include rules that restore a target;
- several peers and chains through tarfilter;
- transforms combined with exclusions;
- cross-extractor behavior;
- privileged ownership, xattrs, ACLs, capabilities, or device nodes.

## Authority

Internal Linux Fieldwork investigation only. No Debian or external upstream contact is authorized or included.

## Disposition

**EXECUTE AND RETAIN AS COMPATIBILITY EVIDENCE.** A passing tarfilter characterization will complete the dpkg-parity record. Promote only a bounded diagnostic improvement or a separately authorized strict mode; the ordinary path-filter behavior matches direct dpkg.