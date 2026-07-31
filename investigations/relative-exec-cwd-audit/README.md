# Relative executable after child cwd changes

State: `repair-complete — exact-head audit pending`

Tracking: issue #194 follow-on review, PR #222, motivating PR #72, and closed research issue #223.

## TL;DR

A relative executable containing `/` or `\` can change identity when a child also changes its working directory. PR #72 demonstrated both consequences: a temporary proxy disappeared after a cwd transition, and a plausible alternate repair could have executed the wrong subject.

PR #222 adds a literal-pattern review scanner for Python, Rust, and GNU-style `env`. Repeated review repaired executable-identity, parser, platform, artifact-receipt, and dedicated-workflow gaps. Exact head `e588f2178f8037119f47c021677e35fd0cfdd6dc` contains seven files and requires fresh repository CI plus the dedicated Linux/Windows audit workflow.

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

## Current gates

Prior head `e498a7a989967fec8d1d0ea33984491dc647ca8f` passed Linux Fieldwork CI `30592552612` / 730. Its dedicated audit `30592552608` / 19 was queued when the workflow repair changed the head.

That prior CI does not clear the new workflow and receipt changes.

Current exact head: `e588f2178f8037119f47c021677e35fd0cfdd6dc`.

Required:

1. Linux Fieldwork CI on the exact head;
2. dedicated audit and Windows jobs on the exact head;
3. artifact and Windows receipt jobs complete successfully;
4. complete seven-file review;
5. repository inventory interpretation remains explicit;
6. branch relation remains suitable for internal landing.

## Authority

Internal Linux Fieldwork work only. No Debian, RPFM, or other external interaction is authorized or included.
