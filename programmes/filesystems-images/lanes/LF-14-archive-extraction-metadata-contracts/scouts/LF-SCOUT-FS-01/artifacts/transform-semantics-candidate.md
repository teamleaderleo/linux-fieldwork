# tarfilter transform semantics candidate

## Finding

`tarfilter --transform` claims GNU tar-style substitution but calls Python `re.sub()` without a replacement count. The default expression therefore replaces every match, while GNU tar replaces only the first match unless the `g` flag is present. The parser also rejected explicit `g`, `gi`, and `ig` forms.

Minimal member: `a/a`

| Expression | GNU tar | Imported tarfilter |
|---|---|---|
| `s/a/b/` | `b/a` | `b/b` |
| `s/a/b/g` | `b/b` | rejected |
| `s/A/b/i` | `b/a` | `b/b` |
| `s/A/b/gi` | `b/b` | rejected |

## Impact

Severity: **medium (5/10)**.

Archive paths can be renamed more broadly than the caller requested. This can create a wrong directory layout or unexpected name collisions. It is not a remote-code-execution finding by itself; impact depends on a caller using transformations and trusting GNU tar compatibility.

## Candidate

Issue: #51

Pull request: #52

The candidate:

- parses escaped delimiters with an explicit state machine;
- defaults to one replacement;
- accepts `g`, `i`, `gi`, and `ig`;
- rejects unsupported and duplicate flags;
- compares resulting member names directly with GNU tar.

## Validation

Linux Fieldwork CI run `30534769266`: success.

The regression applies the sparse/path patch stack first, applies the transform patch second, and checks ordinary, global, case-insensitive, combined, and escaped-delimiter expressions.

## Upstream status

Checked the current mmdebstrap issue index, Debian BTS search results, and current upstream repository on 2026-07-30. No exact existing report was found. No upstream issue, email, or patch was submitted.

## Integration note

PR #48 independently fixes hard-link and stale PAX path rewriting. Its transform code must be composed with this replacement-count parser rather than retaining unconditional global `re.sub()` calls. GNU tar also transforms symlink and hard-link targets by default (`rsh` scope); review `4817835777` records that required correction.
