# Relative executable after child cwd changes

Tracking: issue #194 follow-on review, PR #222, and closed research issue #223.

## TL;DR

A relative executable containing `/` or `\` can change identity when a child also changes cwd. PR #72 demonstrated both consequences: a temporary proxy disappeared after `env --chdir`, and a proposed stable source path would have executed the wrong subject.

PR #222 adds a literal-pattern review scanner for Python, Rust, and shell plus focused identity controls. Independent review repaired missing `args=`/`executable=` handling, multiline Rust, GNU `env` forms, Windows absolute paths, Python `shell=True`, and environment assignments after `env --`.

Findings remain review prompts, not automatic defects. The RPFM Windows hypothesis did not reproduce on the tested runner and is retained as a negative result. No external contact occurred.

## Explain like I'm five

A child process receives two directions:

1. which program to run;
2. which room to start in.

`./tool` means “the tool in this room.” If the child moves rooms first, the same name can disappear or point to a different tool.

Literal PR #72 example:

```text
proxy lives at /tmp/autopkgtest/mmdebstrap
→ child changes cwd to /tmp/debian-chroot
→ child executes ./mmdebstrap
→ ./mmdebstrap is looked up in /tmp/debian-chroot
→ launch fails with ENOENT
```

A more dangerous version succeeds because a decoy exists in the new room. The command is green, but the claimed program never ran.

## Why care

This class can cause:

- false missing-file failures;
- execution of a source copy instead of an installed package;
- green tests against a decoy wrapper;
- platform-specific build behavior;
- identity changes across chroot, container workdir, privilege, or namespace transitions.

The central question is not merely whether a path is relative. It is which executable identity the author intended and which identity the platform actually selected.

## Intent and precedent

- GNU `env --chdir=DIR` and `env -C DIR` change directory before command execution: https://www.gnu.org/software/coreutils/manual/html_node/env-invocation.html
- Rust documents relative program resolution combined with `Command::current_dir` as platform-specific and recommends canonicalizing the program path: https://doc.rust-lang.org/std/process/struct.Command.html#method.current_dir
- Python `subprocess.Popen` permits an `executable=` override, so argv display text and executable identity can differ: https://docs.python.org/3/library/subprocess.html#subprocess.Popen
- systemd command contracts use an absolute executable or a simple PATH-searched name, not a relative path containing `/`: https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
- GNU `realpath` provides canonical resolution when stable identity is required: https://www.gnu.org/software/coreutils/manual/html_node/realpath-invocation.html

These sources support an audit rule, not a universal defect verdict. A program intentionally generated inside the child cwd can be coherent.

## Question

Can a small static checker identify high-signal literal launch sites without mistaking command text, decoy argv values, platform-absolute paths, or environment data for executable identity?

## Source

- carrier: PR #222
- scanner: `tools/relative_exec_cwd_audit.py`
- focused matrix: `tests/test_relative_exec_cwd_audit.py`
- Windows probe: `investigations/relative-exec-cwd-audit/windows_probe.rs`
- marker fixture: `investigations/relative-exec-cwd-audit/windows_marker.rs`
- workflow: `.github/workflows/relative-exec-cwd-audit.yml`
- motivating package-test carrier: PR #72

## Candidate

The scanner reports these literal forms.

### Python

Subprocess-style calls with `cwd=` and a selected executable that is a relative path containing a separator.

It distinguishes:

- positional commands;
- `args=`;
- literal `executable=` overrides;
- `executable=None`;
- dynamic executable overrides as unknown identity;
- `shell=True` command text as shell input rather than executable identity;
- a literal custom shell in `executable=` as the selected identity.

### Rust

Literal `Command::new("relative/path")` chains with `.current_dir(...)`, including multiline string arguments and a trailing comma.

### Shell

`env --chdir`, `env -C`, attached `-Cdir`, and `/usr/bin/env` forms. The parser consumes common value-taking options and valid environment assignments before and after `--` before selecting the command token.

### Cross-platform paths

POSIX absolute, Windows drive-absolute, rooted, and UNC paths are controls. Windows drive-relative paths such as `C:relative\tool.exe` remain review findings.

Output modes:

```sh
python3 tools/relative_exec_cwd_audit.py path/to/file.py path/to/build.rs
python3 tools/relative_exec_cwd_audit.py --json --fail-on-findings path/to/tree
```

## Reproduction

Focused gate:

```sh
python3 -m unittest -v tests/test_relative_exec_cwd_audit.py
```

The matrix includes:

- positive Python positional, `args=`, and literal executable-override cases;
- negative absolute, simple-name, dynamic override, and `shell=True` command-text controls;
- a positive custom-shell identity control;
- positive one-line and multiline Rust forms;
- positive GNU `env` long, short, attached-short, and absolute-path forms;
- assignments before and after `--`;
- POSIX and Windows absolute controls;
- Windows drive-relative positive control;
- CLI JSON, clean status, and fail-on-findings status.

Repository CI and the dedicated Windows workflow remain exact-head gates.

## Review findings and repairs

### First scanner head

The original implementation covered only narrow Python positional, one-line Rust, and `env --chdir` forms.

### Second pass

Independent review found:

1. Python `args=` and `executable=` identity were missing.
2. Multiline Rust `Command::new` and trailing commas were missed.
3. GNU `env -C`, `/usr/bin/env`, and value-taking options were not parsed.
4. Linux-host `os.path.isabs` misclassified Windows rooted and UNC paths.

### Third pass

A later review found two remaining identity errors:

1. with Python `shell=True`, the command string is shell input, not the executable; only a literal custom `executable=` identifies a reportable relative shell;
2. `env --` ends option parsing but does not prevent following `NAME=VALUE` environment assignments, so the scanner must skip those before selecting the program.

Both cases now have direct positive and negative controls.

### Command-position repair

A later exact-head check reproduced the earlier finding that an `env` token used
as ordinary argument text could be mistaken for an executed command. The scanner
now accepts `env` only at the executable command position after optional leading
environment assignments. Direct `printf` and `logger` argument controls remain
empty, while a leading-assignment `/usr/bin/env -C` launch remains positive.

## Windows experiment

The RPFM research candidate used:

```rust
Command::new("./../nuget.exe")
    .current_dir(renderer_path)
```

A Windows Server 2025 probe placed marker executables at both plausible resolution points and retained artifact `relative-exec-cwd-windows-30584306362-1`, digest:

```text
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

The hypothesized current Windows failure did not reproduce. The code still depends on a Rust-documented platform-specific boundary, so the scanner retains it as a portability and identity prompt rather than a demonstrated defect.

### Design choice

Issue #223 was closed with the negative result. An absolute path remains optional cleanup, not a required repair.

### Open question

Other Windows and Rust versions, toolchain wrappers, and the full Qt/NuGet build remain untested.

## Decision method

For each finding, answer:

1. Where is the executable created or selected?
2. Which directory interprets its path on each supported platform?
3. Can a different file occupy the spelling after cwd changes?
4. Which executable identity does the test or product claim to exercise?

A strong regression plants distinct exit codes or output markers at every plausible location and proves which one runs.

## Alternatives considered

### Ban all relative programs with cwd

Rejected as too broad. A child-cwd-local generated executable can be intentional.

### Require absolute paths everywhere

Useful for selected local tools and wrappers, but simple names can intentionally use a controlled PATH contract.

### Trust successful execution

Rejected. A decoy can make a command succeed while the intended program remains untested.

### Resolve after changing directory

Correct only when the executable intentionally belongs to the child cwd. Repository-root tools and temporary proxies should be resolved or installed before launch.

## Results

The scanner now models selected executable identity rather than merely argv text. The changes are scanner-correctness repairs, not new product defect claims.

The RPFM experiment remains a retained negative result. PR #72 remains the demonstrated real failure that motivates the checker.

## Interpretation

**Demonstrated behavior:** PR #72 proves relative executable loss after cwd change.

**Retained negative result:** the tested RPFM Windows path selected the intended repository-root executable.

**Design choice:** merge only a review aid with explicit false-positive boundaries; never treat scanner output as automatic vulnerability or defect classification.

**Open question:** dynamic builders, Rust variables/macros, split shell strings, additional process APIs, and replacement races need separate tooling or manual review.

## Evidence boundary

The checker recognizes literal high-signal syntax. It does not execute targets, resolve variables, prove supported-platform behavior, or close check/execute races. Python matching remains call-name-based and may surface unrelated methods named like subprocess APIs. Findings require source reading and, where material, an executable identity probe.

The Windows probe used a reduced marker tree, not RPFM's full build.

## Next step

The reviewer is deciding whether the six-file audit aid is useful and honest enough to merge locally after:

- focused exact-head tests;
- repository CI;
- Windows workflow;
- complete six-file diff review;
- confirmation that findings remain prompts rather than automatic failures.

## Authority

Internal Linux Fieldwork work only. No Debian, RPFM, or other external issue, pull request, comment, email, or message is authorized or included.
