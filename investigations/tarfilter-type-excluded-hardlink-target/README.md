# tarfilter type exclusion and hard-link dependencies

## TL;DR

`tarfilter --type-exclude=REGTYPE` filters regular archive members by their type. A hard-link member uses `LNKTYPE`, carries no payload, and names a data-bearing member through `linkname`. The current source can therefore remove the regular target, retain the hard link, exit 0, and emit an archive GNU tar cannot extract.

This is a stronger candidate than the related path-exclusion case because `--type-exclude` is tarfilter-specific and its help text does not inherit dpkg's documented current-object path-filter warning. Exact repository execution is pending.

## Explain like I'm five

The filter removes every box marked “regular file.” It keeps a label marked “hard link,” even though that label only says “use the removed box.” The resulting archive has a label with nothing behind it.

## Why care

Type filtering should produce a usable filtered archive or a clear error when the requested type removal breaks another retained member. A zero-status filter followed by a later GNU tar failure hides the dependency problem behind the extraction stage and makes the option harder to use safely.

## Canonical records

- Investigation issue: #243
- Home lane: LF-14, archive extraction and metadata contracts
- Related path-filter compatibility map: #240 / PR #241
- Working branch: `investigate/tarfilter-type-excluded-hardlink-target`
- Imported source: `upstream/mmdebstrap/tarfilter`
- Imported blob at branch creation: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Regression: `tests/test_tarfilter_type_excluded_hardlink_target.py`

## Exact source observation

Type filtering is member-local:

```python
def type_filter_should_skip(member):
    if not hasattr(args, "typefilter"):
        return False
    for t in args.typefilter:
        if member.type == t:
            return True
    return False
```

The main loop discards a matching member before writing any output:

```python
if type_filter_should_skip(member):
    continue
```

A retained hard-link member follows the non-file branch and is written without payload bytes:

```python
if member.isfile():
    ...
else:
    out_tar.addfile(member)
```

Thus `--type-exclude=REGTYPE` can remove the only member carrying bytes while leaving a `LNKTYPE` member that refers to it.

## Bounded question

For one target-before-link PAX archive, what happens when the target's member type is excluded while the dependent hard-link type remains allowed?

## Fixture and controls

The test creates:

- regular `root/base` with `hard-link-payload\n`;
- hard link `root/peer -> root/base`.

### Negative control

Direct GNU tar extraction must:

- return 0;
- create both paths with identical bytes;
- preserve one inode relationship.

### Candidate characterization

Run:

```text
python3 upstream/mmdebstrap/tarfilter --type-exclude=REGTYPE
```

Record filter status, output member table, and GNU tar extraction.

### Neighboring control

Run:

```text
python3 upstream/mmdebstrap/tarfilter --type-exclude=LNKTYPE
```

This should retain the regular target, remove the hard-link peer, and produce an extractable archive. The control distinguishes the dependency hole from a general type-filter failure.

## Distinguishing outcomes

For `REGTYPE` exclusion:

- both target and dependent hard link absent: dependency-aware filtering;
- hard link converted to a payload member: materialized dependency;
- focused nonzero error: explicit unsupported-dependency contract;
- target absent, hard link retained, filter status 0, GNU tar failure: dangling output.

For `LNKTYPE` exclusion, the regular target should remain valid and extractable.

The retained test encodes the source-visible dangling-output result plus the neighboring valid control. Exact CI decides whether the checked-out source and GNU tar exhibit both.

## Promotion and repair design

A passing characterization promotes this into a focused defect investigation. Candidate policies include:

1. skip hard links whose known target was excluded;
2. reject the filter operation with a precise dependency diagnostic;
3. materialize an already-seen target's bytes into the retained link member;
4. buffer hard-link dependency groups until the stream establishes their fate.

Streaming constraints and member order decide feasibility. A repair must preserve:

- ordinary type filtering for independent members;
- `LNKTYPE` exclusion behavior;
- path transformation repairs already retained elsewhere;
- low-memory streaming where possible;
- clear failure status when coherence cannot be preserved.

## Next matrix

Before selecting a repair, add:

- link before target;
- multiple peers to one target;
- hard-link chains;
- target excluded by several type rules;
- simultaneous `REGTYPE` and `LNKTYPE` exclusion;
- long PAX `linkpath` names;
- a filter rerun after failure;
- Python tarfile and libarchive extraction comparison where available.

## Cleanup and rerun

The probe creates small archives and extraction directories below `TemporaryDirectory`. It invokes only the checked-out Python source and GNU tar. No privileged operations, package mutation, device nodes, network, or persistent output are used.

A candidate rerun must reuse the same logical output path after the failing control and prove that no temporary archive or extraction state affects the successful case.

## Evidence boundary

The first probe covers one target-before-link PAX archive and two type filters under an ordinary user. It skips reverse ordering, dependency chains, path rules, transforms, other extractors, package-level pipelines, and privileged metadata.

Source inspection supports the dependency hypothesis. Behavior remains `execution-pending` until Linux Fieldwork CI runs the exact test.

## Authority

Internal Linux Fieldwork investigation only. No Debian or external upstream contact is authorized or included.

## Disposition

**EXECUTE.** Run the exact branch through Linux Fieldwork CI. If the dangling-output characterization and neighboring valid control both pass, promote to a focused defect candidate and execute the ordering/dependency matrix before implementing a repair.
