# Tarfilter regex candidate results

## Run 30548851623 — failed before candidate execution

- Reviewed branch head: `ac6d5eaa3900dc4b86348c4497e8d5e0ba684f12`.
- Pull-request merge checkout: `e510023980545709417c696945530a9daed2af6b`.
- Runner: Ubuntu 24.04.4, Python from the hosted image, GNU tar 1.35.
- Repository tests reached all predecessor tarfilter controls successfully.
- Four candidate test methods failed while applying `tarfilter-transform-regex-dialects.patch`.
- GNU patch diagnostic:

```text
patch: **** malformed patch at line 123:
@@ -150,7 +272,7 @@ class TransformAction(argparse.Action):
```

### Cause

The first hunk header declared 128 new lines while the hunk contained 118. Every later new-file line number was consequently ten lines too high.

### Correction

Commit `e7498db21e1499fd46540f6571e3a3268067a1a6` changes only retained patch metadata:

```text
@@ -120,6 +120,118
@@ -150,7 +262,7
@@ -174,7 +286,10
```

No translator or regression semantics changed. The next run owns the first actual GNU differential result.

## Current execution state

A new exact-head run must apply the corrected patch, then execute:

```sh
python3 -m unittest tests.test_tarfilter_transform_regex_candidate -v
python3 -m unittest discover -s tests -v
```

Retain every subsequent run below this entry, including parser or harness failures. No imported source or external system was changed by the failed run.

## Local Packet H review — live head repair

- Reviewed predecessor head: `beb4ff0c33722f78123da4d3c33d016bd7e9e83d`.
- Environment: Python 3.12.13, GNU tar 1.35, `LC_ALL=C`.
- Linux Fieldwork CI run `30562745367`, job `90939637733`, failed 100 of 103 discovered tests at the same generated-source `SyntaxError`; the failure was patch packaging, before candidate semantics.
- The retained regex tail hunk applied with fuzz to the occurrence-selector loop and inserted `_translate_pattern()` before an indented `number_text = ""`. Every candidate comparison then stopped at `IndentationError`.
- The retained edge patch also used one-line hunks that applied with fuzz inside incomplete statements, producing `SyntaxError`.
- After regenerating both patch boundaries around their exact predecessor source, the original matrix exposed a second product gap: extended middle-position `^` and `$` were translated as literals even though GNU tar keeps them active.
- A final differential control found that GNU tar rejects consecutive basic intervals while accepting the tested extended nested intervals. The candidate now rejects the proven basic form and retains broader malformed interval grammar as a separate boundary.

Focused repair gate:

```text
python3 -m unittest discover -s tests -p 'test_tarfilter_transform_regex*.py' -v
Ran 20 tests in 3.552s
OK
```

The focused run used only `TemporaryDirectory` state. The explicit cleanup and rerun receipt follows below.

Repository discovery in the local sandbox ran 78 tests. All tarfilter regex candidate and adjacent transform tests passed. Three environment controls failed outside this diff:

- two LF-14 archive tests expected effective UID 0 to preserve numeric archive ownership, while this restricted root sandbox could not apply that ownership;
- the chrootless TMPDIR negative control requires a host `/tmp`, which this sandbox does not provide.

Setting `TMPDIR` to a writable disposable directory removed the other temporary-path safety failure. The exact pushed head still requires hosted CI on its ordinary non-root runner.

After deleting the disposable roots, the focused 20-test gate passed again in 3.695 seconds and the caller-selected temporary directory was empty after explicit cleanup.

## Helper E second-pass — Python special-group rejection

- Reviewed exact predecessor head: `7f1865e48b77b89d4989b7de0fe4b85bad4377ec`.
- Reviewed retained patch blobs: regex dialects `2d7c457b83700d51b173efd0825128b6853a5f47`; edge cases `a85ae4ef49e350061e42200f55857fe2bed23f17`.
- Environment: Python 3.13.5, GNU tar 1.35, `LC_ALL=C`.
- New probes showed that explicit `x` passed Python-only `(?...)` syntax to `re.compile()` while GNU tar rejected it:

```text
member  expression          predecessor result  GNU tar
ab      s/a(?=b)/X/x        Xb                  status 2
a       s/(?:a)/X/x         X                   status 2
A       s/(?i)a/X/x         X                   status 2
a       s/(?P<n>a)/X/x      X                   status 2
```

The inline-flag case activated case-insensitive Python matching without GNU's `i` flag. Review `4822922810` classified the exact head as `REPAIR`.

Repair commits:

- `7291bb3ca7e30359dffe5a5f8200768d54f75479`: reject active `(?` in extended mode before Python compilation;
- `4d6cfc383df94cb21f4b86000398e948b65d6da7`: add direct GNU differential regressions for lookahead, noncapturing groups, inline flags, and named groups.

The retained edge patch parses cleanly with `git apply --numstat`. The four local GNU reference probes used disposable directories and left no persistent state. Exact stacked application, full inherited regression, repository discovery, cleanup/rerun, and hosted CI remain the acceptance gates for the repaired head.

## Helper H follow-up — malformed interval and unmatched-close parity

Post-merge differential probes found three success-versus-error gaps:

```text
expression      merged candidate         GNU tar 1.35
s/a{}/X/x       success, literal {}      status 2
s/a{2/X/x       success, literal {2      status 2
s/a)/X/x        Python pattern error      success, literal )
```

The follow-up changes the retained edge patch only:

- an active `{` that does not begin a parsed interval now fails before archive
  output in both basic and extended mode;
- an unmatched closing `)` is escaped as a literal only in extended mode;
- balanced extended groups and active basic `\)` keep their prior behavior.

New controls cover six malformed intervals and three unmatched-close matches
directly against GNU tar 1.35 under `LC_ALL=C`.

Local gate:

```text
git apply --numstat tarfilter-transform-regex-edge-cases.patch
113  1  upstream/mmdebstrap/tarfilter

python3 -m unittest discover -s tests -p 'test_tarfilter_transform_regex*.py' -v
Ran 23 tests
OK

python3 -m unittest discover -s tests -p 'test_tarfilter_transform_regex*.py' -q
Ran 23 tests
OK
```

The caller-selected temporary root and generated Python caches were removed
after the rerun. Hosted exact-head CI and an independent final diff review
remain before release-candidate promotion.
