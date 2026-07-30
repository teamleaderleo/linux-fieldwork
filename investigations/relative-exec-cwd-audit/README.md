# Relative executable after child cwd changes

Tracking: issue #194 follow-on review, PR #222, motivating PR #72, and closed research issue #223.

## TL;DR

A relative executable containing `/` or `\` can change identity when a child also changes its working directory. PR #72 demonstrated both consequences: a temporary installed-package proxy disappeared after `env --chdir`, and an apparently stable source path would have executed the wrong subject.

PR #222 adds a literal-pattern review scanner for Python, Rust, and shell. Repeated peer review has repaired twelve executable-identity errors. The current focused matrix contains 23 tests and passes locally on Python 3.13.5. Exact-head repository and Windows workflows remain required.

Findings are prompts for source review, not automatic defects. The RPFM Windows hypothesis did not reproduce on the tested runner and remains a retained negative result.

## Explain like I'm five

A child process receives two directions:

1. which program to run;
2. which room to start in.

`./tool` means “the tool in this room.” If the child moves rooms first, the same name can disappear or point to another tool.

```text
proxy lives at /tmp/autopkgtest/mmdebstrap
→ child changes cwd to /tmp/debian-chroot
→ child executes ./mmdebstrap
→ lookup happens in /tmp/debian-chroot
→ launch fails with ENOENT
```

A more dangerous version succeeds because a decoy exists in the new room. The command is green, but the claimed program never ran.

## Why care

This class can cause:

- false missing-file failures;
- execution of source code instead of an installed package;
- green tests against a decoy wrapper;
- platform-specific build behavior;
- identity changes across chroot, container workdir, privilege, or namespace transitions.

The central question is not merely whether a path is relative. It is which executable identity the author intended and which identity the platform selected.

## Source and files

- scanner: `tools/relative_exec_cwd_audit.py`;
- focused matrix: `tests/test_relative_exec_cwd_audit.py`;
- repository inventory workflow: `.github/workflows/relative-exec-cwd-audit.yml`;
- Windows probe: `investigations/relative-exec-cwd-audit/windows_probe.rs`;
- marker fixture: `investigations/relative-exec-cwd-audit/windows_marker.rs`;
- motivating package-test carrier: PR #72.

## Candidate behavior

### Python

Report subprocess-style calls with `cwd=` when the selected executable is a literal relative path containing a separator.

Identity rules distinguish:

- positional commands and `args=`;
- literal `executable=` overrides;
- `executable=None`;
- dynamic executable overrides as unknown identity;
- `shell=True` command text as shell input rather than executable identity;
- a literal custom shell in `executable=` as the selected identity.

Python matching remains intentionally call-name-based. An unrelated method named `run` or `Popen` can still become a review prompt.

### Rust

Report a literal `Command::new("relative/path")` only when `.current_dir(...)` belongs to that same builder chain.

The scanner supports ordinary one-line and multiline literals with a trailing comma. It does not resolve builder variables, macros, raw strings, or dynamically constructed program paths.

### Shell

Report GNU-style `env --chdir`, `env -C`, attached `-Cdir`, and absolute `/.../env` forms when their selected command is a relative path containing a separator.

The parser:

- consumes common value-taking options;
- accepts environment assignments before and after `--`;
- treats `env` only at executable command position;
- refuses to guess through `-S/--split-string`;
- does not assume a repository-local `./env` or `tools/env` implements GNU `env` semantics.

Compound commands, wrappers such as `command env`, and shell strings assembled at runtime remain outside this small parser.

### Cross-platform path identity

Controls treat these as non-relative:

- POSIX absolute paths;
- Windows drive-absolute paths;
- Windows single-backslash rooted paths;
- UNC paths.

Drive-relative paths such as `C:relative\tool.exe` remain findings.

## Review findings and repairs

The scanner improved through several independent passes.

1. Python `args=` calls were missed.
2. Python `executable=` identity could differ from displayed argv.
3. Multiline Rust `Command::new` and trailing commas were missed.
4. GNU `env -C`, absolute `env`, and value-taking options were missed.
5. Windows absolute forms were judged with Linux-only path rules.
6. Python `shell=True` command text was mistaken for executable identity.
7. `env -- NAME=VALUE ../tool` could mistake the assignment for the command.
8. `env -S/--split-string` was skipped like a normal option even though it creates a second parser.
9. An `env` token used as argument text to `printf` or `logger` was treated as an executed command.
10. A repository-local binary named `./env` or `tools/env` was assumed to have GNU `env` semantics merely because its basename matched.
11. One Rust `Command::new` could borrow `.current_dir()` from another command later in the same statement. During the same review, Python 3.13.5 exposed that `ntpath.isabs()` no longer classifies a single-backslash Windows rooted path as absolute, so the scanner now handles that form explicitly.
12. Python `cwd=None` was rendered as a directory change to the literal text `None`, even though it explicitly leaves the child's working directory unchanged.

Direct positive and negative controls cover every listed repair.

## Focused reproduction

```sh
python3 -m unittest -v tests/test_relative_exec_cwd_audit.py
python3 -m py_compile tools/relative_exec_cwd_audit.py tests/test_relative_exec_cwd_audit.py
```

Local result after the latest review repair:

```text
Python 3.13.5
Ran 23 tests
OK
```

The matrix covers:

- Python positional, keyword, executable-override, shell, absolute, and simple-name cases;
- Rust one-line, multiline, adjacent-command false-positive, and separately owned adjacent-chain cases;
- GNU `env` long, short, attached-short, assignment, separator, split-string, command-position, and relative-`env` controls;
- POSIX and Windows absolute controls plus a drive-relative finding;
- CLI JSON, clean status, and fail-on-findings behavior.

Repository CI and the dedicated Windows workflow remain exact-head gates.

## Windows experiment

The RPFM candidate used:

```rust
Command::new("./../nuget.exe")
    .current_dir(renderer_path)
```

A Windows Server 2025 probe placed marker executables at both plausible resolution points. Retained artifact:

```text
relative-exec-cwd-windows-30584306362-1
sha256:9be2f5cd3e4bf7f293ade3f8b2e4fb11591f41f59c2c045a2f7b64749d275d7c
```

Observed result:

```text
relative launch with both markers    → repository-root marker
absolute control                     → repository-root marker
relative launch after decoy deletion → repository-root marker
```

### Demonstrated behavior

On that runner, Rust resolved the relative executable from the caller directory rather than the child `current_dir`.

### Interpretation

The hypothesized current Windows failure did not reproduce. The line remains a portability and identity prompt because Rust documents the boundary as platform-specific. It is not classified as a demonstrated RPFM defect.

Other Windows and Rust versions, toolchain wrappers, and the full Qt/NuGet build remain untested.

## Decision method

For each finding, answer:

1. Where is the executable created or selected?
2. Which directory interprets its path on each supported platform?
3. Can a different file occupy the spelling after the cwd change?
4. Which executable identity does the test or product claim to exercise?

A strong regression plants distinct exit codes or output markers at every plausible location and proves which one runs.

## Evidence boundary

The checker recognizes literal high-signal syntax. It does not execute targets, resolve variables, prove supported-platform behavior, parse every shell grammar form, or close check/execute races.

Findings require source reading and, where material, an executable identity probe. The Windows probe used a reduced marker tree, not RPFM's full build.

## Next step

The reviewer is deciding whether the six-file audit aid is useful and honest enough to merge locally after:

- focused exact-head tests;
- repository CI;
- Windows workflow;
- complete six-file diff review;
- confirmation that findings remain prompts rather than automatic failures.

## Authority

Internal Linux Fieldwork work only. No Debian, RPFM, or other external issue, pull request, comment, email, or message is authorized or included.
