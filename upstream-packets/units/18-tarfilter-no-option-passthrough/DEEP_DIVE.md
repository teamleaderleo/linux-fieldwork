# Deep dive

## Mechanism

`PathFilterAction`, `PaxFilterAction`, `TypeFilterAction`, and `TransformAction` create their namespace attributes only when invoked. Normal `argparse` options behave differently: `--strip-components` and `--idshift` always create attributes and use `None` when omitted.

The baseline guard asks whether `strip_components` exists. That attribute always exists, so the byte-copy branch can never run. The source then opens stdin through `tarfile` and writes a new uncompressed PAX stream.

## Selected correction

The selected predicate uses the parser's actual representation:

- absence of `pathfilter`, `paxfilter`, `typefilter`, and `trans` means those custom actions were unused;
- `strip_components in (None, 0)` means no strip operation is active;
- `idshift in (None, 0)` means no ID shift is active.

This is deliberately small. It changes only entry into the already-present copy path.

## Distinguishing packaging observation

The merged PR #46 patch carrier contained the right source change but its hunk header/context applied to exact blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` with:

```text
Hunk #1 succeeded at 201 with fuzz 2 (offset -1 lines).
```

That fails the priority-zero clean-application gate. Regenerating the diff from the exact baseline produced hunk `@@ -204,7 +204,9 @@`, which applies with `patch --fuzz=0` and no offset.

## Active-operation completeness

The earlier focused regression proved transform and nonzero ID shift. Unit #397 names six operation categories, so the regression now exercises all six:

| Operation | Control | Expected result |
| --- | --- | --- |
| path | `--path-exclude=/dir/original.txt` | member removed |
| PAX | `--pax-exclude=SCHILY.xattr.user.*` | matching extended header removed |
| type | `--type-exclude=REGTYPE` | regular member removed |
| strip | `--strip-components=1` | `dir/original.txt` becomes `original.txt` |
| transform | `--transform=s,original,renamed,` | member becomes `dir/renamed.txt` |
| ID shift | `--idshift=1` | uid/gid become 124/457 |

Each result also differs from the input bytes, proving the copy branch was bypassed.

## No-operation classes

The byte identity matrix covers:

- uncompressed PAX;
- gzip;
- bzip2;
- xz;
- GNU PAX sparse;
- explicit strip zero;
- explicit ID-shift zero.

Compression bytes are part of the contract. Extractability alone would miss the defect.

## Exact execution observation

The shell could not clone the branch because network DNS was unavailable. The three branch files required by the focused regression were therefore reconstructed from GitHub content responses, and their Git blob hashes were recomputed before execution:

- source: `ad776167a8473d5d15dbe22e850f4f6db35cf278`;
- Linux Fieldwork patch: `44428ecf8d83a6edf2fca4f4da030129daacb13f`;
- committed regression: `0b8a0e092a6dd2bf7481e077e7c7ec0f27b461bb`.

The exact focused suite passed 3/3 twice. The upstream-shaped patch blob `9f856f389c7a991813dbe9d959edaf94c1155dec` also applied with `--fuzz=0`, and the resulting file compiled.

## Approaches rejected

### Check only `args.strip_components is None`

This would leave transforms and ID shifting outside the predicate and could copy input despite a requested operation.

### Remove the copy path

This preserves the defect and guarantees reserialization for no-operation calls.

### Treat every explicitly supplied option as active

The implementation already treats numeric zero as no change. The selected correction preserves that behavior for strip and ID shift.

### Bundle active sparse repair or path semantics

Those changes have separate mechanisms, compatibility questions, and unit ownership. Combining them would enlarge review and obscure the no-operation contract.

## Compatibility analysis

- Python versions supporting the existing `match` syntax and `removeprefix` already support the selected tuple membership checks.
- Custom action attribute behavior is unchanged.
- Explicit zero behavior matches existing truthiness checks later in the program.
- A semantically inert transform remains an active requested rewrite. This preserves parser intent and avoids inspecting expression effects before reading members.
- The copy path intentionally performs no archive validation. It preserves the caller's byte stream.

## Current upstream comparison

On 2026-08-01, canonical upstream `main` remained at `77ec9be5417ee44c96343d2347145585da1b1f94`. Its `tarfilter` page identified file commit `87b9b385b38795c58bc13ffb33b8724bed27f7a0` and displayed the same parser and unreachable guard as local blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`.

The upstream issue index displayed six open issues; their titles cover initramfs/cpio, hook variables, package caching, eatmydata, CI integration, and old key failures. None concerns tarfilter no-option behavior. Targeted searches for `tarfilter`, `no option`, `no-option`, and `passthrough` across visible upstream issue and pull-request pages found no equivalent report or patch. The visible pull-request search returned only unrelated work such as merged PR #44.

## Complete-diff conclusion

The branch comparison against `main` was reviewed before the final receipt updates. Product-relevant changes are limited to:

1. regenerate the existing source hunk so it applies with zero fuzz;
2. enforce zero-fuzz patch application in the regression;
3. add direct active controls for path, PAX, type, and strip alongside the retained transform and ID-shift controls;
4. retain the upstream-shaped patch and durable packet.

No production/imported source is edited on the Linux Fieldwork branch. No workflow, dependency, unrelated test, archive fixture, or adjacent tarfilter semantic change enters the unit.

## Remaining boundary

Technical discriminators are closed. The remaining steps require an explicit human decision:

1. authorize creation or use of a controlled public fork;
2. create one fork-native candidate commit from patch blob `9f856f389c7a991813dbe9d959edaf94c1155dec`;
3. submit the prepared pull request only under explicit upstream-contact authorization.
