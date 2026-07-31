# tarfilter type exclusion and hard-link dependencies

## TL;DR

`tarfilter --type-exclude=REGTYPE` removes the regular member `root/base`, retains the payload-free hard-link member `root/peer -> root/base`, exits 0, and emits an archive GNU tar cannot extract. Exact-head Linux Fieldwork CI reproduced that behavior and also proved that excluding `LNKTYPE` alone leaves a valid regular-file archive.

This is distinct from dpkg-compatible path exclusion. `--type-exclude` is a tarfilter-specific option without dpkg's documented current-object warning. Issue #243 now owns the defect; PR #244 is the executed baseline carrier, and stacked PR #248 carries a bounded rejection candidate.

## Explain like I'm five

Input: one archive box named `root/base`, plus a second label `root/peer` that says “use the first box.” Action: `--type-exclude=REGTYPE` throws away the box but keeps the label. Result: tarfilter reports success, then GNU tar cannot create either file because the label points at a missing box.

## Why care

The emitted bytes are not a usable filtered archive. A caller sees tarfilter status 0 and only learns about the broken dependency in a later extraction process. The later error names the missing target, while it does not identify the type-filter decision that removed it.

## Intent and precedent

The imported help text presents `--type-exclude` as a tarfilter feature that removes selected archive-member types. The source applies that decision independently to each member. It contains no documented dependency policy for hard links.

The neighboring path-filter investigation #240 / PR #241 is governed by dpkg compatibility: dpkg documents current-object-only path filtering and reproduces the same hazardous path-exclusion result. That precedent does not govern this tarfilter-specific type option. The design choice retained for the candidate is therefore an early focused error for a dependency already known to be removed by type, rather than silently producing a dangling member.

## Canonical records

- Investigation issue: #243
- Characterization PR: #244
- Executed characterization head: `c853da482a04a5ad49b53478b49e540fd4208b27`
- Linux Fieldwork CI: run `30590931312`, passed
- Candidate PR: #248
- Home lane: LF-14, archive extraction and metadata contracts
- Related path-filter compatibility map: #240 / PR #241
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

The main loop discards a matching member immediately:

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

The source therefore has no point where the retained link is checked against an earlier target removed by type.

## Bounded question

For one valid target-before-link PAX archive, what does tarfilter emit when the target's member type is excluded while the dependent hard-link type remains allowed?

## Fixture and controls

The test creates:

- regular `root/base` containing `hard-link-payload\n`;
- hard link `root/peer -> root/base`.

### Direct archive control

GNU tar extraction returns 0, creates both names with identical bytes, and preserves one inode relationship.

### `REGTYPE` characterization

Command:

```text
python3 upstream/mmdebstrap/tarfilter --type-exclude=REGTYPE
```

Observed:

- tarfilter status 0;
- output table contains only `root/peer -> root/base` as `LNKTYPE`;
- GNU tar extraction returns nonzero;
- neither `root/base` nor `root/peer` exists afterward.

### Neighboring `LNKTYPE` control

Command:

```text
python3 upstream/mmdebstrap/tarfilter --type-exclude=LNKTYPE
```

Observed:

- tarfilter status 0;
- output table contains only regular `root/base`;
- GNU tar extraction returns 0;
- `root/base` contains the original payload and `root/peer` is absent.

The neighboring control distinguishes a hard-link dependency hole from a general failure of type filtering.

## Execution

Linux Fieldwork CI run `30590931312` passed at exact head `c853da482a04a5ad49b53478b49e540fd4208b27`.

Evidence by claim:

- independent member filtering and payload-free hard-link output: `source-read`;
- direct archive, `REGTYPE`, and `LNKTYPE` outcomes: `target-executed` through the checked-out tarfilter and GNU tar;
- complete Linux Fieldwork repository compatibility at that head: `full-gate`, limited to the repository's declared Linux Fieldwork CI paths;
- package pipelines, other extractors, other platforms, and privileged metadata: unexecuted.

## Repair design

The observed behavior promotes the question from characterization to a focused defect. Possible policies were:

1. skip hard links whose known target was excluded;
2. reject the operation with a precise dependency diagnostic;
3. materialize an already-seen target's bytes into the retained link member;
4. buffer hard-link dependency groups until the stream establishes their fate.

Stacked PR #248 selects option 2 for target-before-link order. It uses bounded streaming state, preserves ordinary independent type filtering, and leaves dpkg-compatible path exclusions unchanged. Its implementation and execution remain a separate review surface.

## Remaining matrix

The characterization establishes one valid target-before-link pair. Further candidate work should continue to distinguish:

- normalized target spellings and non-equivalent spellings;
- multiple peers to one target;
- hard-link chains;
- simultaneous `REGTYPE` and `LNKTYPE` exclusion;
- immediate rerun after a focused failure;
- long PAX `linkpath` values;
- Python tarfile and libarchive extraction where available;
- complete mmdebstrap package-pipeline diagnostics.

Link-before-target ordering remains a reference boundary: GNU tar already rejects that ordering without filtering, so it cannot serve as the valid baseline for this bounded repair.

## Cleanup and rerun

The characterization creates small archives and extraction directories below `TemporaryDirectory`. It invokes only the checked-out Python source and GNU tar. It uses no network, package mutation, device nodes, privileged metadata, or persistent output.

## Evidence boundary

Demonstrated behavior is limited to one target-before-link PAX pair, two type selections, the checked-out imported tarfilter, and GNU tar on the CI environment. The result establishes a dangling-output mechanism and a neighboring valid control. It does not establish frequency, package-level impact, behavior in other extractors, cross-platform compatibility, or the correctness of any candidate repair.

## Authority

Internal Linux Fieldwork investigation only. No Debian or external upstream contact is authorized or included.

## Disposition

**ACCEPT CHARACTERIZATION.** PR #244 is suitable to merge as executed evidence. Review and execute PR #248 separately as the candidate repair; do not infer candidate acceptance from this baseline result.
