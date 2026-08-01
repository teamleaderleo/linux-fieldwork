# Deep dive

## Question and observed failure

`tarfilter` converts an archive member name into the absolute-looking key used by `--path-exclude` and `--path-include`. Current upstream performs:

```python
name = "/" + member.name.lstrip("./")
```

`str.lstrip()` treats its argument as a character set. It removes every leading `.` and `/`, so `.config`, `./.config`, and `config` all become `/config`. It also turns `../config` into `/config`.

The focused baseline test fails immediately because `--path-exclude=/.config` retains all dotfile spellings. The inverse test also proves `--path-exclude=/config` removes dotfiles and the parent-component spelling `../config`.

## Source mechanism

Path filters are compiled from shell globs by `PathFilterAction`. `path_filter_should_skip()` computes a normalized matching key and evaluates the filters in command-line order. The matching key is local; this unit does not rewrite `member.name` in the output archive.

The defect sits entirely in the matching-key conversion. Filter ordering, glob compilation, parent-retention logic, archive streaming, and member emission remain unchanged.

## Selected correction

The candidate adds:

```python
def normalize_filter_path(name):
    while name.startswith(("./", "/")):
        name = name[2:] if name.startswith("./") else name[1:]
    return "/" + name
```

This loop consumes only complete syntax prefixes:

- `/` — redundant leading absolute marker;
- `./` — explicit current-directory archive prefix.

A leading `.` followed by any character other than `/` remains filename data. A leading `..` remains a complete path component.

The loop also handles alternating prefixes such as `/./.config`, which the earlier combined carrier's `while startswith("./"); lstrip("/")` order leaves as `/./.config`.

## Reproduction matrix

The test creates these member names:

```text
.config
config
..name
...name
./.config
./config
././.config
././config
/./.config
/config
../config
```

It checks:

1. Excluding `/.config` removes only dotfile-equivalent spellings.
2. Excluding `/config` removes only ordinary-name spellings.
3. Multi-dot names and `../config` retain identity.
4. Exclude-all plus include `/.config` restores only dotfile equivalents.
5. Exclude-all plus include `/..name` restores only `..name`.

Baseline: exit 1. Candidate: exit 0. Fresh application and rerun: exit 0.

## Approach history

### Character-set stripping

Rejected. `lstrip("./")` erases filename dots and parent components.

### `posixpath.normpath()`

Rejected. It would collapse `.` and `..` components and would change the identity used for filtering beyond the intended archive-prefix conversion.

### One optional `./` removal followed by slash stripping

Superseded. It repairs common `./.config` inputs, yet alternating prefix spellings such as `/./.config` retain an extra `./` in the matching key. The selected loop handles every leading complete `/` or `./` token.

### Reuse the combined path-matching patch

Rejected for this unit. That patch changes `PathFilterAction` tuple contents and parent-retention logic owned by unit 21. It also traveled in PR #33 beside sparse and no-option changes. Unit 20 has an independent source hunk and regression.

## Compatibility analysis

- Filter patterns remain absolute-looking `/path` values as documented.
- Repeated leading slashes continue to normalize to one leading slash.
- Repeated and alternating `./` prefixes normalize to the underlying member name.
- `.config`, `..name`, and `...name` retain their complete first component.
- `../config` remains `/../config` for matching and cannot alias `/config`.
- Output member names, payload bytes, modes, ownership, timestamps, PAX headers, link targets, and archive ordering are untouched by this patch.
- Filter evaluation order and include-after-exclude behavior are unchanged.
- Parent metadata retention remains unchanged and belongs to unit 21.

## Negative controls

The baseline fails the same upstream-style test that the candidate passes. The failure output contains all dotfile-equivalent names after `--path-exclude=/.config`, proving the detector can lose. A separate five-test unittest execution produced five baseline failures and five candidate passes.

## Current upstream and overlap review

The official repository page observed on 2026-08-01 reports main head `77ec9be5417ee44c96343d2347145585da1b1f94`. The `tarfilter` page reports the file's latest commit as `87b9b385b38795c58bc13ffb33b8724bed27f7a0` and still displays the faulty line.

Searches of the upstream issue and pull-request surfaces for `tarfilter`, `dotfile`, `path normalization`, and `lstrip("./")` produced no active equivalent carrier. This is a search result, not a guarantee against an unindexed private or unpublished change.

## Evidence boundary

Executed locally against an exact byte copy of the current upstream `tarfilter` file. The retained patch also updates `coverage.txt` and adds an upstream-style shell test. A complete upstream checkout and runner invocation remain pending because no controlled fork or checkout was available in this session.

## Remaining discriminator

Apply the patch to a complete checkout at upstream main `77ec9be5417ee44c96343d2347145585da1b1f94` and run:

```sh
CMD=./mmdebstrap ./coverage.py tarfilter-path-dotfiles
```

A passing registered test plus complete three-file diff review would clear the remaining technical gate before authorization review.
