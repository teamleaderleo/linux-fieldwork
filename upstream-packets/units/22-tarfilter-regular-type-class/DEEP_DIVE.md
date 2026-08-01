# Deep dive

## Question and observed failure

Does `--type-exclude=REGTYPE`, including its numeric alias `0`, exclude every member Python classifies as a regular file?

The current upstream source answers no. `TypeFilterAction` stores only `tarfile.REGTYPE` (`b"0"`). Tar readers also accept the legacy NUL type flag exposed by Python as `tarfile.AREGTYPE` (`b"\0"`). `TarInfo.isfile()` returns true for both, while `type_filter_should_skip()` performs raw equality against the one stored byte. A NUL-flagged regular payload therefore survives a regular-file exclusion.

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

Baseline under `--type-exclude=REGTYPE` removes `zero-regular`, retains `nul-regular`, and retains `directory`. The candidate under `REGTYPE` and `0` retains only `directory`. A `DIRTYPE` control retains both regular members and their payloads, proving the correction does not collapse unrelated classes or damage retained regular content.

## Approach history

### Approach A — add both accepted bytes to the selector mapping

- Mechanism: replace `items.append(tarfile.REGTYPE)` with `items.extend((tarfile.REGTYPE, tarfile.AREGTYPE))`.
- Evidence: focused regression, exact-head CI, and exact-head review on PR #77; current-upstream source identity; native packet gate on draft PR #410.
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

The source line and archive-level regression define one invariant: the documented regular-file selector maps to every accepted regular-file encoding. The proposed upstream change remains one commit containing the source edit, one executable test file, and one `coverage.txt` registration stanza.

## Compatibility analysis

- Logical content: only NUL-flagged regular payloads newly disappear when regular exclusion is requested.
- Archive bytes: filtered output is already rewritten by tarfilter; this patch changes membership, not encoding policy.
- Modes, ownership, timestamps, links, and PAX metadata: untouched for retained members.
- Retained payloads: the `DIRTYPE` control checks both regular encodings and their exact bytes.
- Hard links: dependency behavior remains unit 16.
- Paths and transforms: untouched.
- Exit status and stderr: unchanged for valid selectors and archives.
- Repeated selectors: duplicate stored bytes are harmless under the existing loop.
- Python versions: relies on long-standing `tarfile.AREGTYPE` and `TarInfo.isfile()` semantics.
- Unknown type flags: untouched.

## Adjacent-context review

### Transform grammar and metadata — units 01 and 15

Those units modify `TransformAction`, name/link rewriting, and PAX invalidation. They do not own `TypeFilterAction` or selector membership. Their completion order cannot change unit 22's mechanism or focused expected result.

### Hard-link dependency state — unit 16

Unit 16 runs after member selection and reasons about whether an emitted hard link has an emitted target. It can affect a later composed archive gate, but it does not change whether `REGTYPE` denotes both accepted regular encodings.

### Test framework ownership

`coverage.py` copies `./tarfilter` into `shared/tarfilter`, requires a one-to-one match between files under `tests/` and `Test:` entries in `coverage.txt`, materializes the selected shell test as `shared/test.sh`, runs shellcheck and shfmt, and dispatches through the normal null, sudo, or QEMU runner. The native unit-22 asset therefore belongs at `tests/tarfilter-regular-type-class` with `Test: tarfilter-regular-type-class` in `coverage.txt`.

**Stop condition:** adjacent work reopens unit 22 only if current upstream rewrites `TypeFilterAction`, changes the public meaning of `REGTYPE`, changes Python/tar member classification, or demonstrates a composed archive result that invalidates the focused class invariant.

## Current-upstream result

Canonical implementation upstream is `https://gitlab.mister-muffin.de/josch/mmdebstrap` on `main`. The exact current head inspected is `77ec9be5417ee44c96343d2347145585da1b1f94`. Its relevant `tarfilter` content matches Linux Fieldwork Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`, including the defective `items.append(tarfile.REGTYPE)` mapping.

Direct Git transport from this execution runtime cannot resolve the upstream, Salsa, or GitHub hosts. That is an environment transport limitation, not a source ambiguity. The connector can materialize the exact reviewed blob and run hosted Linux Fieldwork CI against it; a complete upstream checkout remains necessary for the final project-level gate.

## Native-test design

The packet now carries:

- `native/tests/tarfilter-regular-type-class` — upstream-style POSIX shell test;
- `native/coverage.txt.fragment` — exact registration stanza;
- `tests/test_unit22_tarfilter_native_packet.py` — Linux Fieldwork gate that verifies source blob identity, requires the native test to fail on baseline, applies the patch with `--fuzz=0`, and requires two clean candidate passes.

The shell test creates the archive with Python's standard library, exercises `REGTYPE`, `0`, and `DIRTYPE`, checks member type bytes, and checks retained payload bytes. It is intentionally mirror-free, unprivileged, disposable, and cleanup-complete.

## Open discriminators

1. Draft PR #410 exact-head CI result and raw first failure if it does not pass.
2. Shellcheck and shfmt acceptance through the real upstream `coverage.py` path.
3. Clean application and execution inside a complete checkout at `77ec9be5417ee44c96343d2347145585da1b1f94`.
4. Relevant broader tarfilter test execution and immediate clean rerun in that checkout.
5. Complete final diff review, including executable mode for the native test.
6. Controlled Forgejo fork availability and explicit external authorization only after the technical gates pass.
