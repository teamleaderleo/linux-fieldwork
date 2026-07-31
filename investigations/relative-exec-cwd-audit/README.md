# Relative executable after child cwd changes

State: `current-main carrier — fresh exact-head gates pending`

Tracking: issue #194 follow-on review, predecessor PRs #222 and #285, current carrier PR #321, motivating PR #72, and closed research issue #223.

## In simple words

A child process may receive both a program name and a working directory. A relative program containing `/` or `\` can resolve to a different file after that directory change.

```text
program: ./tool
child cwd: another/directory
result: lookup occurs from the child directory
```

The retained seven-file unit adds a literal review scanner for high-signal Python, Rust, and GNU-style `env` forms. Findings are prompts for source review. They become failures only when a caller selects `--fail-on-findings`.

## Why care

This class can produce missing-file errors, execution of a plausible decoy, source-versus-installed-package confusion, and platform-specific build behavior. Review needs both the intended executable identity and the identity the platform actually selects.

## Exact carrier

- current carrier: PR #321;
- branch: `restack/relative-exec-cwd-audit-main-20260731-v3`;
- predecessor documentation head: PR #285 at `63ae0735829067a13b94e74ccf063a48073c28b9`;
- predecessor transfer head: `3d5e155bc005411807822c86c2e4cbd77a857e7f`;
- all scanner, workflow, test, and Rust-probe blobs are unchanged from the reviewed predecessor;
- this record is refreshed because PR #285 is closed and current `main` advanced.

The PR body carries the exact live head and gate receipts.

## Seven-file fence

1. `.github/workflows/relative-exec-cwd-audit.yml`;
2. this investigation record;
3. `windows_marker.rs`;
4. `windows_probe.rs`;
5. scanner behavior tests;
6. workflow and artifact-receipt tests;
7. `tools/relative_exec_cwd_audit.py`.

## Scanner contract

### Python

Report subprocess-style calls with a real `cwd=` when the selected executable is a literal relative path containing a separator.

Controls cover positional commands, `args=`, literal `executable=`, `executable=None`, dynamic overrides, `shell=True`, a literal custom shell, and `cwd=None`.

Matching is call-name-based. Unrelated methods named `run`, `Popen`, `call`, `check_call`, or `check_output` can appear as review prompts.

### Rust

Report literal `Command::new("relative/path")` when `.current_dir(...)` belongs to the same builder chain. One-line and multiline literals are covered.

Variables, macros, raw strings, dynamic paths, and builder use across statements remain outside the scanner.

### Shell

Report GNU-style `env --chdir`, `env -C`, attached `-Cdir`, and absolute `/.../env` forms when the selected program is relative and contains a separator.

The parser consumes common value-taking options, accepts assignments before and after `--`, requires `env` at executable command position, declines `-S/--split-string`, and avoids assigning GNU semantics to repository-local `./env` programs.

Compound shell grammar and wrappers such as `command env` remain outside this bounded parser.

### Cross-platform paths

POSIX absolute, Windows drive-absolute, single-backslash rooted, and UNC paths are controls. Drive-relative paths such as `C:relative\tool.exe` remain findings.

## Review repairs retained

Complete review previously repaired these gaps:

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
11. One Rust builder could borrow another builder's `.current_dir()`.
12. Python `cwd=None` was rendered as a real directory change.
13. Downloaded Windows evidence used optimizer-removable assertions and lacked a focused workflow-contract regression.
14. The dedicated workflow omitted its receipt test from path triggers and focused execution.
15. Downloaded Linux and Windows receipts had incomplete schema and path-identity validation.

The current workflow runs both focused Python modules, revalidates exact downloaded finding fields and types, validates the complete Windows schema, and compares Windows identity with normalized Windows path semantics. Workflow permissions remain read-only.

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

The dedicated workflow also inventories repository findings, uploads a typed JSON artifact, downloads and revalidates it, runs the Windows Rust resolution probe, uploads its evidence, and validates the downloaded Windows receipt.

## Windows result

A Windows Server 2025 probe placed marker executables at the repository candidate and child-relative candidate locations.

Observed:

```text
relative launch with both markers    -> repository-root marker
absolute control                     -> repository-root marker
relative launch after decoy deletion -> repository-root marker
```

The tested runner resolved the relative Rust executable from the caller directory. The motivating RPFM hypothesis did not reproduce. Other Windows/Rust versions and the full Qt/NuGet build remain untested.

## Gate history

PR #222 head `06ed175d15829d7840c241a3b9d6e6b859e5e0d7` passed:

- Linux Fieldwork CI `30598820991` / 796;
- dedicated audit `30598820954` / 22.

PR #285 mechanism head `b4ce9c5fd8496072f1c5e81a56a0ee6ca2f050df` passed:

- Linux Fieldwork CI `30623361983` / 821;
- dedicated audit `30623362015` / 23;
- Linux inventory;
- Windows identity probe;
- downloaded Linux receipt;
- downloaded Windows receipt.

PR #285 documentation head `63ae0735829067a13b94e74ccf063a48073c28b9` passed:

- Linux Fieldwork CI `30624089054` / 837;
- dedicated audit `30624089038` / 24.

PR #321 transfer head `3d5e155bc005411807822c86c2e4cbd77a857e7f` passed:

- Linux Fieldwork CI `30629314675` / 895;
- dedicated audit `30629314656` / 25.

Those receipts preserve the unchanged technical blobs. This refreshed record changes the exact head and therefore requires fresh repository and dedicated gates before landing.

## Evidence boundary

The checker recognizes literal high-signal syntax. It does not execute findings, resolve variables, parse complete shell or Rust grammar, prove platform behavior, or close executable replacement races.

The Windows fixture proves only its tested executable identity. Consequential findings still require source review and, where useful, executable markers at every plausible location.

## Landing rule

1. PR #321 names its exact current head;
2. Linux Fieldwork CI passes on that head;
3. the dedicated Linux inventory, Windows probe, and both receipt jobs pass;
4. the direct diff remains the declared seven-file unit;
5. current-main drift receives review;
6. external contact remains absent.

## Authority

Internal Linux Fieldwork work only. No Debian, RPFM, or other external interaction is authorized or included.
