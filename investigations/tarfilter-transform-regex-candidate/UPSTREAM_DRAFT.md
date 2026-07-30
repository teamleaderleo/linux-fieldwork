# Draft upstream packet: tarfilter transform regex dialects

State: `INTERNAL DRAFT — REVIEW BEFORE CONTACT`

Proposed destination: mmdebstrap maintainers at the canonical Salsa project.

## TL;DR

`tarfilter --transform` currently passes sed-style patterns to Python `re`.
GNU tar uses basic regex by default and extended regex only with the `x` flag,
so the same command can rename different archive members. The retained
candidate adds a scanner for the characterized basic/extended subset, rejects
unresolved syntax before archive output, and carries a direct GNU tar 1.35
differential matrix.

The core subset is internally merged. A follow-up candidate now repairs
malformed active intervals and unmatched extended `)`. Hosted exact-head CI and
one more complete-diff review remain before this packet should leave Linux
Fieldwork.

## Explain like I'm five

The command contains a tiny pattern language. GNU tar and Python use some of
the same punctuation with different meanings. The old filter hands GNU's
sentence to Python without translating it, like using the wrong phrasebook.
The command can succeed and put a file under the wrong name.

## Why care

This runs while rewriting archive member names and hard-link or symlink
targets. A silent dialect mismatch can create a plausible archive whose paths
do not match the requested transform. Exact rejection of unsupported syntax
also prevents Python-only features from slipping into a GNU-compatible command
surface.

## Issue draft

### Suggested title

`tarfilter --transform interprets GNU basic expressions as Python regex`

### Observed behavior

Imported source blob:
`upstream/mmdebstrap/tarfilter`
`ad776167a8473d5d15dbe22e850f4f6db35cf278`.

Under `LC_ALL=C`, default transform `s/a+/b/` applied to member `aaa` produces
member `b` in the current filter because Python treats `+` as active. GNU tar
1.35 keeps `+` literal in basic mode and produces member `aaa`.

The inverse spelling also differs: GNU basic `s/a\+/b/` treats `\+` as the
one-or-more operator, while direct Python compilation treats it as a literal
plus. The filter also rejects GNU tar's `x` flag even though `x` is the switch
that selects extended regex syntax.

### Expected behavior

- default transforms follow the supported GNU basic-regex spelling;
- transforms with `x` follow the supported GNU extended-regex spelling;
- unsupported GNU/POSIX and Python-only constructs fail before any archive
  output;
- member names, hard-link targets, symlink targets, and numeric occurrence
  selectors use the same selected dialect.

### Minimal reproduction

```sh
LC_ALL=C tar --transform='s/a+/b/' -cf gnu.tar aaa
python3 tarfilter --transform='s/a+/b/' < input.tar > filtered.tar
tar -tf gnu.tar
tar -tf filtered.tar
```

Expected listing for the default basic expression: `aaa`.
Current direct-Python result: `b`.

The tracked executable regression creates both archives directly and compares
metadata, so it does not infer correctness from exit status alone.

### Evidence

- characterization and predecessor controls: merged PR #113;
- candidate and repair history: merged PR #151;
- tracked record: this investigation directory;
- reusable lesson:
  `notes/filesystems/archive-transform-regex-dialects-need-an-explicit-parser.md`;
- reference: GNU tar 1.35, `LC_ALL=C`;
- reviewed candidate head:
  `4555c5c250c1afedb3947fd1a7b5a0323bd9d262`;
- internal merge:
  `1a1952a78f79b2473f1f9513c1d5820f58987594`.

### Evidence boundary

The executed matrix covers basic/extended operator spelling, contextual
anchors, captures/backreferences, numeric selectors, member/link targets,
repeated quantifiers, repeated intervals, branch-leading basic `*`, literal
`\0`, unsupported POSIX bracket forms, and Python-only `(?...)` groups.

Separate work owns POSIX classes and locale behavior (#146), expression lists
(#117), replacement case state (#125), and zero-length reference hangs (#144).
Persistent `flags=` statements and broader diagnostic parity also remain
separate.

The post-merge malformed-grammar probe found:

| Expression | Retained candidate | GNU tar 1.35 |
| --- | --- | --- |
| `s/a{}/X/x` | early error | error |
| `s/a{2/X/x` | early error | error |
| `s/a)/X/x` | success, literal `)` | success, literal `)` |

The follow-up regression locks this table. It remains a bounded grammar claim,
not a claim of complete POSIX parity.

## Pull-request draft

### Suggested title

`tarfilter: honor basic and extended transform regex dialects`

### Proposed summary

Translate the characterized GNU tar transform pattern subset before compiling
with Python `re`. Accept `x` as the per-expression extended-regex selector.
Track bracket and branch state for contextual anchors, preserve capture
numbering and backreferences, normalize the GNU repeated-quantifier cases in
the matrix, and reject unsupported POSIX/Python-only syntax before processing
archive data.

The implementation composes after target-scope and numeric-occurrence handling.
It leaves expression lists, persistent flags, and replacement case state for
their owning changes.

### Proposed test plan

- retain direct-Python predecessor failures as negative controls;
- compare both active and literal spellings for every operator family;
- compare actual archive metadata with GNU tar 1.35 under `LC_ALL=C`;
- exercise member names, hard-link targets, and symlink targets;
- exercise numeric selector composition;
- reject POSIX bracket forms and Python-only `(?...)` groups early;
- retain the malformed interval/unmatched-close table above;
- run the focused matrix twice after cleanup;
- run Python compilation, shell syntax, command help, and the repository suite;
- review the exact composed source diff after every semantic change.

### Compatibility boundary

The first upstream version should either implement or explicitly reject every
syntax outside the characterized subset. It should avoid claiming full POSIX
regex or locale parity. Follow-up work can add POSIX classes, locale-sensitive
matching, expression lists, persistent flags, and replacement case conversion
behind independent differential tests.

## Review passes

- [x] Complete merged Packet H diff reviewed.
- [x] Exact candidate head recorded.
- [x] Focused GNU differential matrix passed twice on current-main composition.
- [x] Cleanup and rerun checked.
- [x] Target-scope and occurrence-selector composition checked.
- [x] Second pass found and repaired Python-only `(?...)` acceptance.
- [x] Repair malformed active intervals and unmatched extended `)`.
- [ ] Review the repaired exact head twice.
- [ ] Rebase the proposed source patch onto the current canonical upstream
      revision and run the upstream test entry points.
- [ ] Record explicit authorization before any Salsa issue, merge request,
      comment, or review.

## Authority

External contact authorized: `false`.

This packet is an internal draft. No Salsa issue, merge request, email, comment,
or review has been created.
