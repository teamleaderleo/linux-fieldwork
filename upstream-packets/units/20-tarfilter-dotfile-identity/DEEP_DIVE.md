# Deep dive

## Bounded question

How should `tarfilter` convert an archive member name into the absolute-looking key used by `--path-exclude` and `--path-include` while preserving filename identity, archive-root identity, filter ordering, and the existing output archive?

The current source performs:

```python
name = "/" + member.name.lstrip("./")
```

`str.lstrip()` treats `"./"` as a character set. It therefore erases every leading dot and slash instead of parsing complete pathname prefixes.

Examples:

```text
.config       -> /config
./.config     -> /config
config        -> /config
..name        -> /name
...name       -> /name
../config     -> /config
```

The failure belongs to source matching-key construction. It is independent of archive emission, payload reading, packaging, environment, and the original test harness.

## Source mechanism

`PathFilterAction` compiles each shell glob with `fnmatch.translate()` and stores filters in command-line order. `path_filter_should_skip()`:

1. constructs one matching key from `member.name`;
2. evaluates every include/exclude matcher in order;
3. retains the last matching decision;
4. has separate parent-retention behavior for directories and symlinks;
5. returns a boolean without rewriting `member.name`.

This unit changes only step 1. Member emission, link targets, payload bytes, PAX filtering, type filtering, transforms, stripping, ID shifting, and parent-prefix code remain untouched.

## Deep-work chronology

### Observation 1 — the canonical defect is broader than one dotfile

The original report centered on `.config` versus `config`. Direct source review shows the same call aliases multi-dot names and a leading `..` component. The bounded invariant became:

> Matching-key construction may remove complete leading archive syntax prefixes. It may not delete bytes from the first real pathname component.

### Observation 2 — the first green replacement changed root identity

The first candidate consumed leading `/` and `./` tokens and returned `"/" + name`. It repaired dotfiles and parent components, yet produced:

```text
.     -> /.
./.   -> /.
/./.  -> /.
```

GNU tar treats these as archive-root spellings, and the old implementation mapped them to `/`. This was a candidate regression hidden by the first test matrix.

The selected correction adds one explicit root case:

```python
if name == ".":
    name = ""
```

### Observation 3 — dpkg and tar answer different compatibility questions

A disposable `.deb` differential ran dpkg 1.22.22 against isolated roots and admin directories.

Results:

- `./.config` matches `/.config` and stays distinct from `/config`.
- `./config` matches `/config` and stays distinct from `/.config`.
- `./..name` and `./...name` retain their first component.
- bare `.config` and repeated `././.config` extract to `.config` but do not match dpkg's native filter path.

Therefore:

- dpkg compatibility directly supports the ordinary package-member spelling `./path`;
- repeated and alternating leading prefixes are a consumer-path extension, not evidence of exact dpkg equivalence.

A separate GNU tar 1.35 probe shows that these leading spellings all extract to the same `.config` pathname:

```text
.config
./.config
././.config
/./.config
//./.config
.//.config
/.//.config
```

It also shows that `.`, `./`, `./.`, `/.`, `/./`, and `//./.` all address extraction root.

### Observation 4 — whole-path normalization is a different unit

GNU tar also maps `foo/./.config` and `foo/.config` to the same extracted pathname. Applying `posixpath.normpath()` would reproduce that consumer behavior, but it would also collapse `../config`, erase internal components everywhere, and broaden the claim from leading syntax prefixes to whole-path component semantics.

The internal-dot case is retained as a residual successor question. It does not enter this patch silently.

### Observation 5 — the evidence executable had ambiguous authority

The first test selected `/usr/bin/mmtarfilter` before `./tarfilter`. A host package could therefore make the registered test pass or fail against a system executable while the checkout candidate remained untested.

The current order is:

1. explicit `MMTARFILTER`;
2. checkout-local `./tarfilter`;
3. `/usr/bin/mmtarfilter` fallback.

The workflow also passes an explicit exact path for direct execution.

### Observation 6 — patch content and executable mode require separate checks

A Git patch can declare `new file mode 100755`, while GNU `patch` applies text and commonly creates a non-executable file. The exact gate now performs:

1. `patch --dry-run --fuzz=0` to detect offsets or fuzz;
2. `git apply --check --verbose` for Git patch validity;
3. `git apply --verbose` to preserve file mode;
4. `test -x tests/tarfilter-path-dotfiles`.

This prevents a clean hunk application from certifying an unusable upstream test.

## Approach history

### A — current character-set stripping

**Mechanism:** `member.name.lstrip("./")`.

**Result:** rejected. It aliases dotfiles, multi-dot names, and parent-component spellings with ordinary names.

**Losing controls:** `.config`, `..name`, `...name`, `../config`.

### B — remove one optional `./`, then leading slashes

**Mechanism:** one `removeprefix("./")`-style operation followed by slash removal.

**Result:** rejected. Repeated and alternating leading archive spellings remain partially unparsed.

**Losing control:** `././.config`.

### C — whole-path `posixpath.normpath()`

**Mechanism:** canonicalize all dot components.

**Result:** rejected for this unit. It collapses `../config` and internal `foo/./.config`, changing identity outside the leading-prefix boundary.

**Losing controls:** `../config`, `foo/./.config`.

### D — consume all leading `/` and `./` tokens

**Mechanism:** loop over complete leading tokens.

**Initial result:** repaired dotfiles and traversal-looking names, but mapped archive-root marker `.` to `/.`.

**Disposition:** superseded by E.

### E — complete leading-token parsing plus explicit root marker

**Mechanism:** consume complete leading `/` and `./` tokens; map a remaining lone `.` to empty; prepend one `/`.

**Result:** selected.

**Why selected:** it is the smallest implementation that wins the current defect, repeated-prefix controls, parent-component controls, and root-alias controls without entering internal component normalization.

## Selected correction

```python
def normalize_filter_path(name):
    # Remove only complete archive syntax prefixes. Leading dots that are
    # part of the first pathname component remain part of its identity.
    while name.startswith(("./", "/")):
        name = name[2:] if name.startswith("./") else name[1:]
    if name == ".":
        name = ""
    return "/" + name
```

The retained upstream patch adds this helper, replaces one call site, registers one test, and adds that test.

## Expanded regression ownership

The current upstream-style test verifies:

### Matching semantics

- `/.config` excludes only dotfile-equivalent leading spellings.
- `/config` excludes only plain-name equivalents.
- `..name`, `...name`, `../config`, and `./../config` retain identity.
- include-after-exclude restores the expected dotfile set.
- reversing include/exclude order produces the opposite last-match result.
- `/..name` restores only `..name`.
- `/` matches all tested archive-root aliases.

### Representation and metadata

- regular file payload bytes survive for retained members;
- modes, uid/gid, timestamps, and custom PAX headers survive;
- directory type and metadata survive;
- symlink type and target survive;
- hard-link type and target survive;
- excluding each dot-prefixed type removes only that member.

### Evidence authority

- explicit executable selection is supported;
- checkout-local executable wins over a system package;
- the Git patch preserves executable test mode;
- the registered runner invokes the copied checkout test.

## Compatibility analysis

### Preserved

- documented filter patterns remain absolute-looking `/path` values;
- filter ordering remains last-match-wins;
- member names in output remain byte-for-byte the same strings supplied by `tarfile`;
- retained payload bytes and metadata remain under existing emission behavior;
- link targets remain untouched;
- parent-retention code remains untouched;
- leading slashes still collapse to one matching slash;
- ordinary `./path` package members follow dpkg's path identity;
- archive-root spellings continue to match `/`.

### Deliberately extended

Repeated and alternating leading `/` and `./` spellings receive the same matching identity because GNU tar consumes them as the same pathname. The packet labels this as a tar-consumer extension instead of calling it native dpkg behavior.

### Deliberately held outside

Internal `.` components, such as `foo/./.config`, stay unchanged in the matching key. GNU tar consumer behavior suggests a possible successor, while resolving it requires a broader compatibility matrix for `.` and `..` across all components.

## Negative controls and mutation adequacy

The retained mutation script makes four attractive alternatives lose:

- source baseline: dotfile and parent-component aliases;
- one-prefix implementation: repeated prefix failure;
- `normpath`: traversal and internal-component over-normalization;
- first candidate: root-marker regression.

This prevents the detector from classifying every implementation as success and shows that the selected logic wins for the intended reason.

## Current upstream and historical review

The canonical repository page observed on 2026-08-01 reports main `77ec9be5417ee44c96343d2347145585da1b1f94`. The `tarfilter` file still carries the faulty line. Its latest commit title records a 2024 intent to accept paths beyond one leading slash, which is consistent with reviewing relative and repeated leading spellings instead of assuming canonical package paths only.

Directed public searches covered:

- `tarfilter`;
- `dotfile`;
- `path normalization`;
- `lstrip("./")`;
- the exact source commit and title.

No active equivalent public carrier was found. This is bounded search evidence, not proof against unpublished or unindexed work.

## Known/unknown matrix

| Area | Known | Remaining discriminator |
| --- | --- | --- |
| Source owner | Matching-key conversion in `path_filter_should_skip()` | None for unit boundary |
| Ordinary dpkg path | `./path` matches absolute-looking filter key | Exact-head runner receipt |
| Repeated leading prefixes | GNU tar extracts them to one consumer pathname | Maintainer compatibility review after authorization |
| Archive root | Selected helper preserves `/` identity | Exact-head regression run |
| Internal `.` component | GNU tar collapses it | Separate successor design and matrix |
| Parent metadata | Existing independent defect in unit 21 | Unit 21 work |
| Output metadata | Current regression covers retained member forms | Exact runner artifact |
| Patch transport | Git application preserves executable mode | Exact runner log |
| Binary authority | Checkout-local selection fixed | Exact runner trace |
| Active overlap | Directed public search found none | Recheck immediately before authorization |

## Review saturation and stop rule

The unit may advance from `ACTIVE` only after all of these are true on one exact final head:

1. canonical source commit and blobs are verified;
2. current expanded baseline loses;
3. current candidate passes directly;
4. the registered `coverage.py` test passes;
5. zero-offset dry-run and Git application pass;
6. exact three-file upstream diff is reviewed;
7. syntax, shellcheck, and shfmt pass;
8. cleanup and immediate rerun pass;
9. dpkg, GNU tar, and mutation probes pass;
10. artifacts and hashes are retained;
11. active overlap is rechecked;
12. the internal-dot residual is recorded without broadening this unit.

A green first candidate or one direct shell invocation does not satisfy this stop rule.

## Reopen triggers

Reopen or redesign the selected correction if any of these occur:

- canonical upstream changes `tarfilter` or the test runner;
- exact-head CI exposes a source, test, runner, environment, or cleanup failure;
- a public equivalent patch appears;
- maintainer guidance rejects repeated-prefix consumer normalization;
- internal dot-segment review proves the leading-only boundary incoherent;
- Python `tarfile`, GNU tar, or dpkg behavior changes in a supported environment.

## Current incomplete discriminator

The latest exact-head workflow must complete and its first result must be classified. The workflow is the authoritative gate for canonical checkout, real patch application, registered test execution, cleanup/rerun, and artifact capture.
