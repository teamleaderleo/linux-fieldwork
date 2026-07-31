# tarfilter type exclusion and hard-link dependencies

## TL;DR

The imported source removes regular `root/base` under `--type-exclude=REGTYPE`, retains payload-free `root/peer -> root/base`, exits 0, and emits an archive GNU tar cannot extract. PR #244 preserves that executed baseline.

PR #248 adds one bounded rule after the canonical transform/PAX candidate from PR #68: when a retained hard link targets a member already skipped by `--type-exclude`, tarfilter exits 1 with a focused diagnostic before writing the broken member. Dpkg-compatible path filtering remains unchanged.

## Explain like I'm five

Input: a box named `root/base` and a label `root/peer` that says “use that box.” The type filter removes the box but keeps the label. The candidate remembers that the box was removed and stops with `root/peer -> root/base` instead of handing the next program a broken label.

## Why care

Without the candidate, tarfilter reports success and the useful failure appears later in GNU tar. The candidate places the error at the option that caused it, emits no dangling member, and preserves successful filtering when the selected types are independent.

## Intent and precedent

The imported help text presents `--type-exclude` as a tarfilter-specific archive-member filter. The source has no hard-link dependency policy. The selected repair therefore treats a retained link to a target already removed by this type filter as an unsupported operation and reports it immediately.

The related path-filter result in #240 / PR #241 follows dpkg's documented current-object semantics and direct dpkg parity. This candidate deliberately does not change that behavior. It also composes with PR #68 rather than recreating transform, hard-link target, or PAX metadata logic.

## Canonical records

- Investigation issue: #243
- Executed characterization: PR #244
- Characterization code/test head: `c853da482a04a5ad49b53478b49e540fd4208b27`
- Characterization CI: Linux Fieldwork run `30590931312`, passed
- Candidate: PR #248
- Candidate branch: `fix/tarfilter-type-excluded-hardlink-target`
- Related path-filter compatibility map: #240 / PR #241
- Canonical transform/PAX composition: issue #63 / PR #68
- Imported source: `upstream/mmdebstrap/tarfilter`
- Imported blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Characterization test: `tests/test_tarfilter_type_excluded_hardlink_target.py`
- Candidate tests: `tests/test_tarfilter_type_excluded_hardlink_candidate.py` and `tests/test_tarfilter_type_excluded_hardlink_patch_contract.py`
- Candidate patch: `0001-reject-hardlinks-to-type-excluded-members.patch`

## Demonstrated baseline

The PAX fixture contains regular `root/base` with `hard-link-payload\n` and hard link `root/peer -> root/base`.

Exact-head characterization established:

- direct GNU tar extraction succeeds and preserves one inode;
- `--type-exclude=REGTYPE` returns 0, retains only the link, and produces a GNU tar extraction failure;
- `--type-exclude=LNKTYPE` returns 0, retains the regular target, and extracts successfully.

This is `target-executed` evidence for the checked-out tarfilter and GNU tar. It is not candidate evidence.

## Candidate policy

The candidate records names skipped by type and normalizes archive-root prefixes before comparison:

```python
hardlink_prefix = re.compile(r"^(?:(?:\.\.?/)|/)+")
type_excluded_members = set()
...
if type_filter_should_skip(member):
    type_excluded_members.add(hardlink_prefix.sub("", member.name))
    continue
```

Before writing a retained hard link, it normalizes `linkname` with the same rule. A known dependency break prints:

```text
hard-link target excluded by type filter: root/peer -> root/base
```

and exits 1.

The candidate preserves independent type filtering, `LNKTYPE` exclusion that leaves a regular target, simultaneous exclusion of both member types, and transform/PAX behavior carried by PR #68. It rejects only a retained hard link whose normalized target is already known to have been removed by the active type filter.

## Prefix-equivalence review

The first candidate compared raw strings and missed GNU tar-equivalent target spellings. A second draft used `lstrip("./")`, which also collapsed `.../root/base` even though GNU tar treats that spelling as distinct.

The retained regex removes repeated leading `/`, `./`, and `../` components while preserving `.../`.

The candidate matrix requires rejection for `./root/base`, `/root/base`, `../root/base`, `../../root/base`, `.//root/base`, and `//root/base`. Each is first proved extractable by GNU tar in the unfiltered archive. A separate `.../root/base` control proves the unfiltered archive fails and the candidate does not invent a dependency relationship.

## Composition with PR #68

The candidate test applies `investigations/tarfilter-transform-target-scopes/tarfilter-transform-target-scopes.patch` before the new patch. That integrated candidate carries replacement semantics, hard-link target rewriting, PAX `path`/`linkpath` regeneration, GNU tar default `rsh` transform scope, and uppercase scope opt-outs.

A combined control excludes `LNKTYPE`, transforms `root/base` to `base`, and requires successful extraction. A separate patch-contract test applies both patches with `--fuzz=0`, compiles the result, and verifies the defining source mechanism.

## Candidate matrix

1. imported-source dangling-output negative control;
2. candidate status 1, focused diagnostic, and no emitted member;
3. syntactically valid empty tar output after the focused failure;
4. GNU tar-equivalent leading-prefix detection;
5. `.../` non-equivalence;
6. successful `LNKTYPE` exclusion plus transform rerun;
7. simultaneous exclusion of both member types;
8. two retained peers stopping at the first dependency;
9. exact zero-fuzz application of PR #68 plus the candidate patch;
10. Python compilation and complete repository CI.

## Why rejection

Silently skipping the dependent link removes an additional allowed member. Materializing bytes changes the meaning of the type filter and requires payload retention. Buffering arbitrary dependency graphs widens the streaming design.

Focused rejection uses bounded name state, identifies the exact dependency, keeps independent filters working, and avoids publishing a broken retained member.

## Ordering boundary

The candidate handles target-before-link ordering, the valid GNU tar reference order. GNU tar already rejects a hard link that precedes its target even when the target appears later. Supporting that order would require a separate buffering design and a different valid baseline.

## Cleanup and rerun

Every fixture, patched source copy, archive, and extraction directory lives below `TemporaryDirectory`. Tests invoke Python, `patch`, and GNU tar only. They create no network activity, package mutation, device nodes, privileged metadata, or persistent output.

## Evidence boundary

Established before current-head candidate execution:

- baseline source mechanism: `source-read`;
- baseline target and neighboring control: `target-executed` at the characterization head;
- candidate implementation, exact patch composition, and tests: `target-test-prepared`.

Execution still required:

- exact two-patch application;
- candidate status, output, and diagnostic;
- transformed rerun and combined exclusions;
- complete current Linux Fieldwork gate.

Outside this candidate: link-before-target buffering, arbitrary hard-link graphs, path-exclusion behavior, package integration, other extractors/platforms, and privileged metadata.

## Authority

Internal Linux Fieldwork work only. No Debian or external upstream contact is authorized or included.

## Disposition

**EXECUTE CURRENT-MAIN CANDIDATE.** PR #244 remains the accepted negative-control carrier. PR #248 requires exact-head CI and a fresh complete-diff review before implementation acceptance.
