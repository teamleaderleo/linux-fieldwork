# Deep dive

## Question and observed failure

Does `--type-exclude=REGTYPE`, including its numeric alias `0`, exclude every member Python classifies as a regular file?

The imported baseline answers no. `TypeFilterAction` stores only `tarfile.REGTYPE` (`b"0"`). Tar readers also accept the legacy NUL type flag exposed by Python as `tarfile.AREGTYPE` (`b"\0"`). `TarInfo.isfile()` returns true for both, while `type_filter_should_skip()` performs raw equality against the one stored byte. A NUL-flagged regular payload therefore survives a regular-file exclusion.

This is a source defect. The fixture parses both encodings distinctly, the baseline exits successfully, and the leaked member remains a regular file. No harness, packaging, privilege, or environment failure explains the result.

## Source mechanism

1. argparse invokes `TypeFilterAction` for each `--type-exclude` value.
2. The `REGTYPE | 0` case appends only `tarfile.REGTYPE`.
3. `type_filter_should_skip()` iterates stored bytes and compares `member.type == type_flag`.
4. A member carrying `tarfile.AREGTYPE` fails that equality check.
5. Later, the output path calls `member.isfile()` and copies the leaked payload as an ordinary file.

The source consequently uses two definitions of “regular file”: a byte-specific definition for filtering and Python's class definition for payload copying.

## Reproduction narrative

The smallest distinguishing archive contains:

- `zero-regular`, type `tarfile.REGTYPE`, payload `zero\n`;
- `nul-regular`, type `tarfile.AREGTYPE`, payload `nul\n`;
- `directory`, type `tarfile.DIRTYPE`.

Baseline under `--type-exclude=REGTYPE` removes `zero-regular`, retains `nul-regular`, and retains `directory`. The candidate under `REGTYPE` and `0` retains only `directory`. A `DIRTYPE` control retains both regular members, proving the correction does not collapse unrelated classes.

## Approach history

### Approach A — add both accepted bytes to the selector mapping

- Mechanism: replace `items.append(tarfile.REGTYPE)` with `items.extend((tarfile.REGTYPE, tarfile.AREGTYPE))`.
- Evidence: focused regression, exact-head CI, and exact-head review on PR #77.
- Result: both selector spellings exclude both regular encodings; other selectors remain independent.
- Compatibility cost: an archive member already classified and copied as a regular file now obeys the regular exclusion.
- Status: selected.

### Approach B — call `member.isfile()` inside the filter

- Mechanism: special-case regular filtering in `type_filter_should_skip()`.
- Result: semantically viable but spreads selector knowledge into the decision loop and requires a richer stored representation.
- Compatibility cost: larger code change and less uniform handling of repeated selectors.
- Status: rejected in favor of the one-line mapping correction.

### Approach C — treat `AREGTYPE` as a separate CLI type

- Mechanism: expose an additional selector name or byte spelling.
- Result: preserves the semantic bug for callers using the documented regular-file selector and expands the public interface needlessly.
- Status: rejected.

## Selected correction

Store both Python constants for `REGTYPE` and `0`. This is the smallest correction aligned with Python's existing tar member classification and the option's user-facing description.

## Why the changes belong together

The source line and archive-level regression define one invariant: the documented regular-file selector maps to every accepted regular-file encoding. Splitting them would leave either an unprotected code change or a test with no candidate.

## Compatibility analysis

- Logical content: only NUL-flagged regular payloads newly disappear when regular exclusion is requested.
- Archive bytes: filtered output is already rewritten by tarfilter; this patch changes membership, not encoding policy.
- Modes, ownership, timestamps, links, and PAX metadata: untouched for retained members.
- Hard links: dependency behavior remains unit 16.
- Paths and transforms: untouched.
- Exit status and stderr: unchanged.
- Repeated selectors: duplicate stored bytes are harmless under the existing loop.
- Python versions: relies on long-standing `tarfile.AREGTYPE` and `TarInfo.isfile()` semantics.
- Unknown type flags: untouched.

## Active overlap

The source hunk is in `TypeFilterAction`, a region adjacent tarfilter units may also edit. Unit 22 remains logically independent, yet final patch ordering requires comparing the final heads for units 01, 15, and 16. Unit 16 also concerns type filtering but owns hard-link dependency semantics after selection, not selector-class membership.

## Current-upstream limitation

The official Salsa project and tags were readable through the web surface. A direct `git clone https://salsa.debian.org/debian/mmdebstrap.git` failed with `Could not resolve host: salsa.debian.org` in the execution runtime. Current `master` commit, blob, clean application, and native test placement therefore remain unclaimed. The retained exact package identity is `debian/1.5.7-3` / `6fde999741f4fe1e7bf38079acf29432ef87a35e`.

## Open discriminators

1. Exact current Salsa `master` commit and `tarfilter` blob.
2. Clean patch application or precise conflict against that commit.
3. Current mmdebstrap-native test location and command.
4. Final source-line ordering against active tarfilter units.
5. Controlled Salsa fork availability and explicit external authorization.
