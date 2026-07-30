# Debian mmdebstrap autopkgtest 1141078 transition triage

## In simple words

Debian CI run `72574145` has been recovered and classified. The failure belongs to the `mmdebstrap` **test fixture**, not to mmdebstrap runtime behavior.

The `dev-ptmx` test executes `script(1)` inside an apt-variant root but did not explicitly install `bsdutils`, the package that provides `/usr/bin/script`. The test passed while `bsdutils` was Essential. Debian's util-linux 2.42 packaging removed that Essential flag, so the valid minimal root no longer contained `script`.

The focused fix is tracked in issue #84 and PR #86: add `bsdutils` to the root's existing `--include` list.

## Coordination and existing-work search

- Central Linux Fieldwork issue: #53
- Historical capture: closed PR #82
- Focused dependency fix: issue #84 and PR #86
- Reusable reproduction tooling: PR #72
- Primary earlier draft investigation: PR #9
- Local formatting repair: PR #26
- Repository workflow/tooling defect: #54
- Non-Debian suite-selection classification defect: #55
- Privileged fork-PR guard: #75
- Mirror-server readiness defect: #79
- Exact subordinate-ID account matching: #80

Open and closed issues, pull requests, `targets/`, `notes/`, `investigations/`, the imported source, and the immutable Debian result directory were searched. Issue #53 is the central coordination record.

## Exact source boundary

- Project: Debian `mmdebstrap`
- Package revision: `1.5.7-3`
- Imported source commit recorded by the target map: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Local source: `upstream/mmdebstrap/`
- Package-test metadata: `upstream/mmdebstrap/debian/tests/control`
- Package-test entrypoint: `upstream/mmdebstrap/debian/tests/testsuite`
- Suite driver: `upstream/mmdebstrap/coverage.sh`
- Case scheduler: `upstream/mmdebstrap/coverage.py`
- Case registry: `upstream/mmdebstrap/coverage.txt`
- Failing test source: `upstream/mmdebstrap/tests/dev-ptmx`

This branch does not edit the imported mmdebstrap source.

## Recovered historical run

PR #82 retrieved the immutable Debian CI files from:

```text
https://ci.debian.net/data/autopkgtest/testing/amd64/m/mmdebstrap/72574145/
```

Captured facts:

- run: `72574145`
- started: `2026-06-27 09:17:44+0000`
- trigger: `migration-reference%2F0`
- package: `mmdebstrap 1.5.7-3`
- testbed: Debian testing amd64
- autopkgtest: `5.55`
- kernel package: Debian `6.12.94-1`
- `bsdutils`: `1:2.42.2-1`
- duration: `2871` seconds
- generated cases passed: `158`
- generated cases skipped: `93`
- final autopkgtest exit: `6`

Artifact digest:

```text
sha256:9e9ded80793210b59ff34398e7d78a6e33be2723515b77eee26e9b40fc5a138a
```

The raw log is retained only in the time-bounded workflow artifact. PR #86 carries a compact asserted JSON summary.

## First failing operation

The first and only failed generated case was:

```text
(252/283) dev-ptmx
dist: testing
mode: root
variant: apt
format: auto
```

The generated root command included:

```text
--include=gcc,libc6-dev,python3,passwd
```

The first unavailable command was:

```text
chroot "$1" script -c "echo foobar"
```

with:

```text
chroot: failed to run command ‘script’: No such file or directory
```

The root cleanup completed successfully.

## Ownership

Debian `bsdutils` provides `/usr/bin/script`.

- `bsdutils 1:2.41-5` in trixie was Essential;
- `bsdutils 1:2.42.2-1` in the failing testing archive was not Essential.

The apt variant installs the Essential set plus requested includes. Once `bsdutils` left the Essential set, the root correctly omitted `script`.

The util-linux packaging transition exposed the assumption, but it did not remove or break `script`. The owning defect is that `tests/dev-ptmx` executes a non-Essential command inside its generated root without naming the provider package.

## Focused correction

PR #86 retains this one-line candidate:

```diff
- --include=gcc,libc6-dev,python3,passwd
+ --include=bsdutils,gcc,libc6-dev,python3,passwd
```

Its exact-head regression proves:

- the baseline contains two inner `script` hooks and omits `bsdutils`;
- the patch applies to the imported test source;
- exactly one source line changes;
- all customize hooks and their order remain unchanged;
- the compact historical evidence names the run, case, missing command, provider package and binary path.

## Other apparent errors in the historical log

Two earlier messages are expected controls rather than preceding failures:

- missing `curl` occurred in the third proxy-readiness fallback; mirror construction continued and succeeded through an earlier probe;
- missing `lz4` occurred in the deliberate `fail-with-missing-lz4` case and produced the expected result.

No hidden behavioral failure preceded `dev-ptmx`.

## Separate valid defects

The investigation also found repository and package-test defects that did not cause run `72574145`:

- unsupported non-Debian archive identities hard-fail a `skippable` test (#55, PR #64);
- reusable workflow jobs referenced tooling absent from `main` (#54, PR #72);
- privileged jobs required a same-repository PR guard (#75, PR #72);
- the background HTTP mirror server discards startup errors and lacks a readiness check (#79);
- subordinate-ID detection uses an unanchored account-name grep (#80, PR #92).

Keep these fixes independent from the historical `dev-ptmx` disposition.

## Executable log classifier

Classify a retained transcript with:

```sh
python3 tools/mmdebstrap_autopkgtest_log.py path/to/log
python3 tools/mmdebstrap_autopkgtest_log.py path/to/log --json
```

The parser distinguishes:

- `mirror` — local cache construction failed;
- `coverage-preflight` — formatter, lint, POD, or helper gate failed before named cases;
- `coverage-case` — a named case emitted `result: FAILURE`;
- `pass` — autopkgtest reported success;
- `unknown` — only wrapper-level failure evidence exists.

Synthetic tests cover passing and wrapper-only negative controls, first-failure retention, ANSI/timestamp prefixes, mirror failure, preflight failure and named case failure.

## Current-sid validation

PR #72 is building a reusable current-sid execution path. Its earlier runs exposed and fixed several harness defects before behavioral cases:

- direct execution of mode-`0644` repository shell files;
- missing `patch` in the outer container bootstrap;
- empty early-exit artifacts;
- malformed wrapper patch hunk counts;
- a shell proxy without POD.

The current proxy is a formatted Perl forwarding script checked with `perl -c` and `pod2man`. A current-sid result is supporting validation only; the recovered June transcript is the ownership evidence.

## Evidence limits

The exact June mirror is not reconstructed locally. The recovered immutable log and metadata identify the failed command and package universe directly, so a frozen local mirror is no longer needed to assign the historical owner.

A current-sid pass or failure can reveal present archive behavior but must not silently replace the historical evidence.

## Cleanup and rerun

The classifier is read-only and accepts a path or standard input. Its tests use in-memory synthetic text. The historical capture job was non-privileged, bounded to 64 MiB per candidate file, and closed without merge after artifact inspection.

## Self-review

- the immutable historical transcript was recovered;
- the first named failure and command were identified;
- the command provider and old/new Essential status were verified;
- expected fallback/control errors were separated from the real failure;
- ownership is limited to the test fixture;
- the focused candidate changes one dependency line;
- unrelated valid defects remain separate;
- raw logs are not committed;
- no external tracker or upstream repository was changed.

## Reusable notes

- `notes/debian/autopkgtest-observer-package-transition-triage.md`
- PR #86: `notes/debian/tests-must-declare-command-providers-not-essential-set-assumptions.md`

## Disposition

**Fix identified.** Review and dynamically validate PR #86, retain the classifier, and continue separate work on issues #55, #79 and #80.

## Authority

No Debian, Ubuntu, or other upstream issue, email, merge request, patch submission, comment, or review is authorized by this investigation.
