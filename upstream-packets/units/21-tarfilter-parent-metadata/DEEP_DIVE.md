# Deep dive

## Question and observed failure

Can `tarfilter` retain explicit directory or symlink parents when a later `--path-include` can select a nested member, while preserving last-match-wins behavior and avoiding pathname-prefix aliases?

The current algorithm stores only the compiled `fnmatch.translate()` regex. For `/usr/bin/tool`, the compiled pattern starts with Python regex wrapper syntax. The code applies a shell-glob prefix regex to that translated regex and obtains a useless prefix. With `--path-exclude='/*' --path-include='/usr/bin/tool'`, the output contains only `usr/bin/tool`.

The omission belongs to `tarfilter`: the input archive contains explicit parent entries and metadata, and the filter removes them before the extraction tool runs.

## Source mechanism

`PathFilterAction` converts each path glob to a compiled regex and stores `(destination, regex)`. `path_filter_should_skip()` applies these matchers in order, preserving the last matching decision. When an excluded member is a directory or symlink, it tries to retain the member if an include can match beneath it:

```python
prefix = prefix_prog.sub(r"\1", r.pattern)
prefix = prefix.rstrip("/")
if name.startswith(prefix):
    return False
```

Two independent defects appear here:

1. `r.pattern` is translated Python regex text, while `prefix_prog` expects shell-glob text.
2. For an exact include, parenthood points from the include toward the current member: `/usr/bin/tool` starts with `/usr/`; `/usr` does not start with `/usr/bin/tool`.

A correction therefore needs the original glob and a relation that covers both fixed-prefix ancestors and conservative descendants after the first metacharacter.

## Reproduction narrative

The retained script creates a PAX archive with:

- `usr/`: mode `0700`, uid/gid `11/21`, mtime `1700000001`, PAX marker `usr-parent`;
- `usr/bin/`: mode `0711`, uid/gid `12/22`, mtime `1700000002`, PAX marker `bin-parent`;
- `usr/bin/tool`: mode `0755` and content `tool\n`;
- `/usr2` and `/opt` controls.

The baseline model reproduces the current source path and emits only `usr/bin/tool`. GNU tar 1.35 creates omitted parents as mode `0755`. The candidate emits all three entries, retaining archive metadata; GNU tar extracts the explicit parents as `0700` and `0711`.

Full commands and hashes live in `TESTS.md`.

## Approach history

### Approach A — use original glob with the existing one-direction check

- mechanism: store raw glob and replace `r.pattern` with the raw text;
- evidence: exact include `/usr/bin/tool` yields literal prefix `/usr/bin/tool`;
- result: `/usr`.startswith(`/usr/bin/tool`) remains false;
- compatibility cost: none, but the headline case stays broken;
- disposition: rejected.

### Approach B — exact ancestor check only

- mechanism: retain when the literal prefix equals the current path or starts with `current_path + '/'`;
- evidence: exact include and `/usr/bin/*` work;
- result: `/usr/*/tool` fails to retain `/usr/bin`, because the wildcard occurs before the current directory's final component;
- compatibility cost: less conservative than dpkg and risks dropping needed parents;
- disposition: rejected.

### Approach C — conservative bounded two-direction relation

- mechanism: retain the original glob, extract its literal prefix, normalize the current member without a trailing slash, then retain when either path is the same as or a component-bounded ancestor of the other. An empty literal prefix retains all candidate parents.
- evidence: eight-case local relation matrix; focused exact/wildcard/class/boundary test;
- result: preserves exact ancestors and wildcard descendants while rejecting `/usr` versus `/usr2`;
- compatibility cost: can retain extra directories after an early wildcard, consistent with dpkg's documented conservative policy;
- disposition: selected for retained patch.

### Approach D — full glob-language prefix viability automaton

- mechanism: parse shell glob syntax and determine whether any suffix can complete a match below the current path;
- evidence: conceptual review only;
- result: potentially tighter retention;
- compatibility cost: substantially more code and more room for divergence from Python `fnmatch` edge cases;
- disposition: deferred. Reopen only if maintainers require minimal rather than conservative parent retention.

## Selected correction

`PathFilterAction` stores `(destination, original_glob, compiled_regex)`. Ordinary filtering continues to use the compiled regex. The excluded directory/symlink special case derives the literal prefix from `original_glob`, then checks equality or component-bounded ancestry in both directions.

This is the smallest coherent correction because the raw glob and descendant predicate solve separate halves of the same exact failure. The focused test belongs in the same patch.

## Why the changes belong together

The tuple change feeds the only new data consumed by the parent-retention branch. The regression detects the metadata consequence of that branch and includes the boundary case that constrains the implementation. Splitting these changes would leave either unused data or an unprotected behavior change.

## Compatibility analysis

### Files and metadata

Surviving parent entries retain their original `TarInfo`, including mode, uid, gid, mtime, link target, and PAX headers. The patch changes membership only for directories and symlinks already excluded by path rules.

### Path-rule behavior

Ordinary files keep current last-match-wins matching against compiled `fnmatch.translate()` regexes. The special branch remains limited to excluded directories and symlinks.

### Conservative over-inclusion

An include whose first metacharacter occurs early can retain extra parents. dpkg documents this conservative behavior to avoid unpack failures. The candidate preserves that policy and adds component boundaries.

### Adjacent features

PAX filtering, type filtering, transforms, component stripping, id shifting, hard links, and no-option passthrough remain outside this patch.

## Negative controls and losing mutations

- Current algorithm: exact include emits only the leaf and loses parent metadata.
- Original-glob-only mutation: exact ancestors still fail because comparison direction remains wrong.
- One-direction ancestor-only mutation: wildcard `/usr/*/tool` fails for `/usr/bin`.
- Boundary mutation using raw `startswith()` would retain `/usr` for `/usr2/tool`; the matrix requires false.
- Unrelated `/opt` with include `/usr/bin/tool` remains excluded.

## Current upstream and historical review

Current upstream still presents the affected source logic. The implementation comment cites dpkg's filter logic. Historical dpkg code stores the raw glob and uses its literal prefix, while current dpkg documentation explicitly permits retaining more directories and symlinks than required. No equivalent active upstream carrier surfaced in the 2026-07-31 search.

## Remaining questions

1. **Exact patch application:** discriminator is `git apply --check` on canonical `main@77ec9be5417ee44c96343d2347145585da1b1f94`.
2. **Upstream-native focused gate:** discriminator is `CMD=./mmdebstrap ./coverage.py tarfilter-parent-metadata` or the exact current invocation selected from the checkout.
3. **Formatting gate:** discriminator is the repository's shell/Python formatting and line-length checks on the candidate.
4. **Conservative policy acceptance:** discriminator is maintainer review after explicit authorization; no contact has occurred.

## Evidence boundary

Demonstrated on Debian 13, x86_64, Python 3.13.5, GNU tar 1.35 using a self-contained source-path model and a focused candidate executable. The retained patch received synthetic exact-context application, Python compilation, shell parsing, and focused test execution. Full upstream checkout and integration evidence remain open.

## Reopen triggers

- upstream changes `PathFilterAction` tuple ownership or parent-retention logic;
- current dpkg policy removes conservative over-inclusion;
- exact upstream patch application conflicts;
- focused upstream test exposes a trailing-slash, symlink, or glob-class incompatibility;
- a public equivalent issue or pull request appears;
- external authorization changes.
