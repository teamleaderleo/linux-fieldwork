# Relative executable after child cwd changes

State: `reviewed — documentation refresh pending exact gates`

Tracking: issue #194 follow-on review, predecessor PR #222, current-main carrier PR #285, motivating PR #72, and closed research issue #223.

## TL;DR

A relative executable containing `/` or `\` can change identity when a child also changes its working directory. PR #72 demonstrated both consequences: a temporary proxy disappeared after a cwd transition, and a plausible alternate repair could have executed the wrong subject.

The retained seven-file unit adds a literal-pattern review scanner for Python, Rust, and GNU-style `env`. Repeated review repaired executable-identity, parser, platform, artifact-receipt, and dedicated-workflow gaps. The current carrier is PR #285 on branch `restack/relative-exec-cwd-audit-current-main-v2`; its PR body carries the exact live head.

Findings are source-review prompts. The retained Windows probe produced a negative result for the motivating RPFM hypothesis.

## Explain like I'm five

A child receives two directions: which program to run and which room to start in.

`./tool` means “the tool in this room.” Moving first can make that name disappear or select another file.

```text
proxy lives at /tmp/autopkgtest/mmdebstrap
→ child changes cwd
→ child executes ./mmdebstrap
→ lookup uses a different room
→ launch fails or selects a decoy
```

## Why care

This class can produce false missing-file failures, green tests against a decoy, source-versus-installed-package confusion, and platform-specific build behavior. Review needs the intended executable identity and the identity actually selected by the platform.

## Seven-file fence

1. `.github/workflows/relative-exec-cwd-audit.yml`;
2. this investigation record;
3. `windows_marker.rs`;
4. `windows_probe.rs`;
5. scanner behavior tests;
6. workflow and artifact-receipt tests;
7. `tools/relative_exec_cwd_audit.py`.

## Candidate behavior

### Python

Report subprocess-style calls with a real `cwd=` when the selected executable is a literal relative path containing a separator.

Identity handling covers positional commands, `args=`, literal `executable=`, `executable=None`, dynamic overrides, `shell=True`, a literal custom shell, and `cwd=None`.

Matching is call-name-based. Unrelated methods named `run`, `Popen`, `call`, `check_call`, or `check_output` can appear as prompts.

### Rust

Report literal `Command::new("relative/path")` when `.current_dir(...)` belongs to the same builder chain. One-line and multiline literals are covered. Variables, macros, raw strings, dynamic paths, and builder use across statements remain outside the scanner.

### Shell

Report GNU-style `env --chdir`, `env -C`, attached `-Cdir`, and absolute `/.../env` forms when the selected program is relative and contains a separator.

The parser consumes common value-taking options, accepts assignments before and after `--`, requires `env` at executable command position, declines `-S/--split-string`, and avoids assuming repository-local `./env` has GNU semantics.

Compound grammar and wrappers such as `command env` remain outside this bounded parser.

### Cross-platform paths

POSIX absolute, Windows drive-absolute, single-backslash rooted, and UNC paths are controls. Drive-relative paths such as `C:relative\tool.exe` remain findings.

## Review repairs

1. Python `args=` calls were missed.
2. `executable=` could select a different identity from argv.
3. Multiline Rust literals and trailing commas were missed.
4. GNU `env -C`, absolute `env`, and value-taking options were missed.
5. Windows absolute forms were judged with Linux-only path rules.
6. `shell=True` command text was mistaken for executable identity.
7. Assignments after `env --` could be mistaken for the command.
8. `-S/--split-string` created an unparsed second layer.
9. `env` used as argument text was misclassified as command position.
10. Repository-local binaries named `env` were assumed to implement GNU semantics.
11. One Rust builder could borrow another builder's `.current_dir()`; Python 3.13.5 also required an explicit single-backslash rooted-path control.
12. Python `cwd=None` was rendered as a real directory change.
13. Downloaded Windows evidence relied on optimizer-removable assertions and lacked a focused workflow-contract regression.
14. The dedicated workflow omitted its receipt test from both path triggers and focused execution.
15. The downloaded Linux inventory receipt only checked that the artifact was a list; the Windows receipt used raw path equality and incomplete schema validation.

The current workflow runs both focused modules, revalidates exact downloaded finding fields and types, validates the complete Windows schema, and compares Windows identity with normalized Windows path semantics. Workflow permissions remain read-only.

## Focused execution

```sh
python3 -m unittest -v \
  tests.test_relative_exec_cwd_audit \
  tests.test_relative_exec_cwd_audit_receipt
python3 -m py_compile \
  tools/relative_exec_cwd_audit.py \
  tests/test_relative_exec_cwd_audit.py \
  tests/test_relative_exec_cwd_audit_receipt.py
```

The dedicated workflow also inventories current repository findings, uploads a typed JSON artifact, downloads and revalidates it, runs the Windows Rust resolution probe, uploads its evidence, and validates the downloaded Windows receipt.

## Windows result

A Windows Server 2025 probe placed marker executables at the repository candidate and child-relative candidate locations.

Observed:

```text
relative launch with both markers    → repository-root marker
absolute control                     → repository-root marker
relative launch after decoy deletion → repository-root marker
```

The tested runner resolved the relative Rust executable from the caller directory. The hypothesized RPFM failure did not reproduce. Other Windows/Rust versions and the full Qt/NuGet build remain untested.

## Evidence boundary

The checker recognizes literal high-signal syntax. It does not execute findings, resolve variables, parse complete shell or Rust grammar, prove platform behavior, or close replacement races. Findings require source review and, where consequential, executable markers at every plausible location.

The inventory is a review aid and does not fail merely because findings exist unless a caller selects `--fail-on-findings`.

## Gate history

Predecessor PR #222 head `06ed175d15829d7840c241a3b9d6e6b859e5e0d7` passed Linux Fieldwork CI `30598820991` / 796 and dedicated audit `30598820954` / 22.

Current-main restack head `b4ce9c5fd8496072f1c5e81a56a0ee6ca2f050df` passed:

- Linux Fieldwork CI `30623361983` / 821, including 262 repository tests;
- dedicated audit `30623362015` / 23;
- Linux inventory job;
- Windows Rust identity probe;
- downloaded Linux artifact receipt;
- downloaded Windows receipt.

A complete seven-file review found no mechanism blocker. This documentation refresh corrects stale routing language only and therefore requires fresh exact-head repository and dedicated workflow receipts before landing.

## Landing rule

1. the PR body names the exact current head;
2. Linux Fieldwork CI passes on that head;
3. the dedicated audit, Windows probe, and both receipt jobs pass on that head;
4. the direct diff remains the declared seven-file unit;
5. any main-side drift is reviewed before merge;
6. no external contact is made.

## Authority

Internal Linux Fieldwork work only. No Debian, RPFM, or other external interaction is authorized or included.
