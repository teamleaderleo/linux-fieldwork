# Tests and evidence

## Executed source

| Item | Exact identity |
| --- | --- |
| user fork | `teamleaderleo/mmdebstrap` `master` at `574048f2a720057b75e56622003932f344dc700a` |
| base `tarfilter` | Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| prerequisite patch | blob `38510533dc015182f3e87e9d2f3777eea5b8c93b` |
| prerequisite result | blob `adb330efcc941bf5e646f195c245a3184e42f8e2` |
| regenerated regex patch | blob `7e7d37a77b0215af033b0c97770c83cce130911a` |
| candidate result | blob `ca8e656c036172230c796a8a12cb17f262108c39` |
| Python | `3.13.5` |
| reference | GNU tar `1.35`, `LC_ALL=C` |

## Historical carrier application result

After applying the clean unit-15 prerequisite, GNU patch 2.8 processed the historical core regex patch as follows:

```text
hunk 1: succeeded with offset +25
hunk 2: succeeded with offset +19
hunk 3: failed
```

This is a packaging/context failure. Offsets were rejected as release evidence. The regex layer was regenerated from prerequisite blob `adb330ef...` to candidate blob `ca8e656c...`.

## Regenerated series application

Dry run and real application both reported:

```text
Hunk #1 succeeded at 145.
Hunk #2 succeeded at 395.
Hunk #3 succeeded at 425.
```

Both patches used:

```sh
patch --fuzz=0 -p1
```

No hunk used fuzz or an offset. The reapplied bytes matched candidate Git blob `ca8e656c036172230c796a8a12cb17f262108c39`. Python compilation passed.

## Complete direct matrix

Command represented by the packet wrapper:

```sh
sh upstream-packets/units/01-tarfilter-regex-dialects/scripts/materialize_and_run.sh
```

Result:

| Group | Cases | Result |
| --- | ---: | --- |
| baseline and prerequisite negative controls | 3 observations | passed |
| candidate/GNU successful transforms | 41 | passed |
| numeric occurrence with member/hard-link/symlink scopes | 2 | passed |
| candidate/GNU shared rejection | 11 | passed |
| explicit candidate-reject/GNU-accept POSIX boundary | 3 | passed |

The 41 successful comparisons cover basic/extended operator reversal, groups, backreferences, contextual anchors, branch-leading basic `*`, literal `\0`, repeated quantifiers, intervals, unmatched extended closing parentheses, and all three PR #220 accepted-neighbor controls.

The 11 shared rejections cover four Python-only `(?...)` forms, six malformed active intervals across both dialect spellings, and consecutive basic intervals.

Full output: [`artifacts/FULL_MATRIX.txt`](artifacts/FULL_MATRIX.txt)  
Receipt SHA-256: `573cf47dcb947f62910fd3cdd77fe8103a0499b99b2d5d63dc0f081fb60ea8c0`

## Immediate rerun

A representative gate was run twice from a freshly reapplied candidate. Each run covered:

- eight successful dialect/edge cases;
- one numeric occurrence plus link-scope case;
- two shared-invalid cases;
- one POSIX boundary case.

Both runs passed and produced digest:

```text
731adb7f3cfd8f3aba6278ced4a630f4c588da0547952b4e9e02666c536fb65f
```

## Harness correction retained

An early local harness attempt reversed the prerequisite patch inside the live candidate directory while constructing a baseline. That restored the old two-value transform loop and produced:

```text
ValueError: too many values to unpack (expected 2)
```

The source candidate had already compiled. The harness was corrected by isolating baseline, prerequisite, and candidate files in separate paths. All reported product results use the corrected harness.

## Cleanup

The packet wrapper creates one `mktemp -d` root, traps `EXIT HUP INT TERM`, and removes the root. The Python matrix creates all archives and reference trees under `TemporaryDirectory`. The executed continuation left no process, socket, mount, container, archive, candidate tree, or Python cache intentionally retained outside the local scratch directory used to create the committed artifacts.

## Parallel-unit review

Every issue #397 unit branch exists. Tarfilter units 15, 16, and 18–22 were reviewed. Unit 15 is the direct prerequisite; unit 16 vendors that prerequisite; units 18–22 own independent paths. See [`artifacts/PARALLEL_UNITS.md`](artifacts/PARALLEL_UNITS.md).

## Gates completed

- [x] Exact user-fork head and base blob.
- [x] Current visible public-upstream relevant file identity from unit 15.
- [x] Clean prerequisite application.
- [x] Historical regex carrier failure classification.
- [x] Regenerated regex patch with zero fuzz/offsets.
- [x] Exact intermediate and final blobs.
- [x] Python compilation.
- [x] Complete direct GNU differential matrix.
- [x] Cleanup-aware immediate rerun.
- [x] Parallel tarfilter unit refresh.

## Gates remaining

- [ ] Select or port upstream-native transform test files.
- [ ] Run focused native tests through current `coverage.py`.
- [ ] Run the appropriate broader upstream-native gate.
- [ ] Compose selected independent tarfilter units and review the complete combined diff.
- [ ] Resolve exact canonical Salsa head and live Salsa issue/MR overlap.
- [ ] Create a candidate branch when desired.
- [ ] Obtain explicit authorization before external contact.
