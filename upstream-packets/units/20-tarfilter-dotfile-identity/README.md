# Unit 20 — tarfilter dotfile identity

## State

- Initiative: Linux Fieldwork issue #397, unit 20
- State: `ACTIVE`
- Linux Fieldwork branch: `upstream/unit-20-tarfilter-dotfile-identity`
- Linux Fieldwork base: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Internal review and exact-execution carrier: Linux Fieldwork draft PR #408
- External-contact state: unauthorized; internal work only
- Intended upstream destination: Muffin Forgejo fork and pull request
- Controlled upstream fork: `NEEDS FORK`

The unit remains active because the exact canonical-upstream workflow has yet to produce a completed receipt on the final documentation head. A green first-pass direct test is insufficient under the repository's deep-work and stop-rule guidance.

## Exact upstream identities

- Project: `josch/mmdebstrap`
- Intended base branch: `main`
- Main head observed 2026-08-01: `77ec9be5417ee44c96343d2347145585da1b1f94`
- `tarfilter` last-change commit: `87b9b385b38795c58bc13ffb33b8724bed27f7a0`
- Last-change title: `tarfilter: do not rely on paths being absolute (starting with a single slash)`
- Imported source path: `upstream/mmdebstrap/tarfilter`
- Imported source blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Imported `coverage.txt` blob: `87f4cccf5fc646c82600672113830419e20b95dd`
- Imported `coverage.py` blob: `9a522484aef05deae514a98e4b6adf5feb6c886d`
- Imported `run_null.sh` blob: `e0a8c106f9d3d636baea286d2ab33834748dffc9`

## Selected candidate

- Patch: `patches/0001-tarfilter-preserve-dotfile-identity.patch`
- Current patch blob: `fca86c0a45cb7f7c2e8534b4dacf8b2dafd55342`
- Locally computed patch SHA-256: `e9a71c6afe34f3170c27cc81a93006bf5d6eb2fe863fd7dd32e7f46c8719171b`
- Upstream-style regression: `tests/tarfilter-path-dotfiles`
- Current test blob: `516f4e1f3a38175257b68a9d9e524495d7531564`
- Locally computed test SHA-256: `9fbc4c1146bdeb199713eb51279ce439e78ff96fc7be711f68b2278aa052e910`
- Exact-execution workflow: `.github/workflows/unit-20-tarfilter-dotfile-identity.yml`
- Current workflow blob before this documentation batch: `bf769608742c71e4f3bdd2a1c700905ac1d0c02a`

The source hunk removes complete leading `/` and `./` archive prefixes, preserves filename dots and `..` components, and maps archive-root spellings back to `/`:

```python
def normalize_filter_path(name):
    while name.startswith(("./", "/")):
        name = name[2:] if name.startswith("./") else name[1:]
    if name == ".":
        name = ""
    return "/" + name
```

The upstream diff remains three files: `tarfilter`, `coverage.txt`, and `tests/tarfilter-path-dotfiles`.

## Distinguishing findings from the deeper pass

1. Current upstream aliases `.config`, `config`, multi-dot names, and `../config` because `str.lstrip("./")` removes a character set.
2. The first replacement candidate repaired dotfiles but mapped `.`, `./.`, and `/.` to `/.`, changing archive-root matching. The selected helper restores them to `/`.
3. A real dpkg 1.22.22 differential shows that dpkg path filters own the ordinary package-member spelling `./path`. Bare and repeated `./` spellings extract to the same consumer pathname but fall outside dpkg's native filter match.
4. GNU tar 1.35 treats repeated leading `/` and `./` spellings as one consumer pathname and treats `.`, `./.`, and `/.` as archive-root aliases. That supports the candidate's leading-prefix extension while requiring the root repair.
5. GNU tar also aliases internal `foo/./.config` with `foo/.config`. That is a separate successor question because it changes the bounded claim from leading-prefix parsing to whole-path component normalization.
6. The original test selected `/usr/bin/mmtarfilter` before the checkout binary. The revised test uses explicit `MMTARFILTER`, then `./tarfilter`, then the system binary.
7. GNU `patch` does not preserve Git's `new file mode 100755`. The exact gate now uses a zero-fuzz `patch --dry-run`, followed by `git apply --check`, `git apply`, and an executable-bit assertion.

## Test ownership and coverage

The current regression covers:

- both dotfile/plain-name exclusion directions;
- include-after-exclude and reverse rule ordering;
- `.config`, `config`, `..name`, `...name`, `../config`, and `./../config`;
- repeated and alternating leading `/` and `./` prefixes;
- archive-root aliases;
- regular files, directories, symlinks, and hard links;
- payload bytes, modes, uid/gid, timestamps, PAX headers, and link targets;
- exact checkout-binary selection.

See `TESTS.md`, `DEEP_DIVE.md`, and `artifacts/`.

## Scope boundary

This unit owns matching-key normalization and its focused include/exclude regression. It excludes:

- no-option passthrough, owned by unit 18 / issue #29;
- parent metadata retention, owned by unit 21 / issue #39;
- sparse archive rewriting;
- transform, strip, PAX-filter, type-filter, and link-target rewrite semantics;
- internal dot-segment normalization such as `foo/./.config`.

The older PR #33 combined several of those behaviors. Unit 20 retains the smallest independent source hunk and upstream test.

## Current exact-execution state

- Internal draft PR: #408
- Last semantic technical head before this documentation batch: `7b92189ace1de4138d753830f8032c244f1276c6`
- Exact-head workflow run for that head: `30691603829`
- Last observed state: queued
- The workflow verifies canonical source identities, losing baseline behavior, zero-offset applicability, Git mode preservation, exact three-file diff, syntax and formatting, direct execution, registered `coverage.py` execution, cleanup, immediate rerun, dpkg differential, GNU tar differential, and mutation controls.

## First incomplete step

Inspect the newest exact-head workflow generated after this documentation batch. Classify its first result by owner, preserve the logs and artifact identities in the packet, and repair any candidate, test, runner, environment, or evidence failure before changing disposition.

A successful exact-head run still requires final complete-diff and search-saturation review before `READY FOR AUTHORIZATION`.
