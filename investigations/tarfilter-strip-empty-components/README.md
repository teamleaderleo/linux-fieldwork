# Tarfilter strip-components and repeated separators

## In simple words

`tarfilter` counts the empty strings created by repeated `/` characters as directory components. GNU tar does not. An archive member such as `a//b/file` therefore lands at `b/file` instead of `file` under `--strip-components=2`. The local candidate scans nonempty components while preserving the exact remaining substring after the final removed component.

## Existing work and duplicate search

Searched Linux Fieldwork issues, pull requests, investigations, tests, and notes for repeated separators, empty path components, and `strip-components` behavior. No focused record covered this mismatch.

- Canonical issue: #81
- Related path-reference work: #25 / PR #48
- Negative-value boundary: #58 / PR #59
- Candidate branch: `fix/tarfilter-strip-empty-components`
- Candidate patch: `tarfilter-strip-empty-components.patch`

## Question

Does the imported `--strip-components` implementation count pathname components the same way as GNU tar when member names contain repeated separators?

## Source

- Project: imported `mmdebstrap`
- Package/revision: Debian `1.5.7-3`
- Imported file: `upstream/mmdebstrap/tarfilter`
- Imported blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Source owner: the `args.strip_components` block in `main()`
- Reference: GNU tar `--strip-components` with `--show-transformed-names` and extraction

## Baseline behavior

The source uses:

```python
comps = member.name.split("/")
member.name = "/".join(comps[args.strip_components:])
```

For `a//b/file`, `split('/')` produces `['a', '', 'b', 'file']`. At count `2`, the empty separator segment consumes one requested component and the output becomes `b/file`. GNU tar returns `file`.

For `a///file` at count `2`, GNU tar extracts nothing because only two nonempty components exist. The imported source emits `/file`.

## Candidate

Scan the original member name:

1. skip separator runs only while locating the next component;
2. count one nonempty component;
3. after the requested component, preserve the original substring beginning after its terminating separator;
4. omit the member when there are not enough nonempty components.

This retains GNU behavior such as `a//b/file` becoming `/b/file` at count `1` and `file` at count `2`.

## Reproduction

```sh
python3 -m unittest tests.test_tarfilter_strip_empty_components -v
```

The test applies the retained patch to an exact temporary copy of the imported source.

## Results required

- Negative control: unmodified `a//b/file` at count `2` must become `b/file`.
- Candidate names must match GNU tar for:
  - `a//b/file` at counts `1` and `2`;
  - `./a//b/file` at count `3`;
  - ordinary `a/b/file` at count `2`.
- GNU tar must extract nothing for `a///file` at count `2`.
- The unmodified source must emit `/file` for that case.
- The candidate must omit it.

## Interpretation

Repeated separators are accepted archive syntax. Counting their empty split fields changes which real pathname components are removed and violates the explicit GNU tar compatibility claim.

## Evidence boundary

- The focused regression covers regular-file member names and GNU tar on the CI runner.
- GNU tar's separate traversal and leading-path sanitization is not reproduced by this candidate.
- Trailing-directory names and all unusual path dialects are not claimed.
- The candidate modifies member names only. Consolidation with #25 should reuse the same scanner for hard-link targets and regenerate PAX reference metadata.
- The imported source remains unchanged; the patch is applied in a disposable directory.

## Cleanup and safety

The test uses in-memory fixtures and `TemporaryDirectory`. GNU extraction is limited to a generated archive with no traversal or absolute member names. No privilege, package installation, mount, or caller-controlled deletion root is used.

## Next step

Verify exact-head CI, then compose this scanner with the active hard-link/PAX path rewrite candidate before any consolidated patch is considered.

## Authority

Internal Linux Fieldwork work only. No upstream issue, email, merge request, patch submission, comment, or review is authorized or made.
