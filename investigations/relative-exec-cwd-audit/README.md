# Relative executable after child cwd changes

Tracking: issue #194 follow-on review, PR #222, and issue #223. Worker: Helper B.

## Explain like I'm five

A child process has two separate inputs:

1. the program to execute;
2. the directory where the child begins running.

A path such as `./tool` only has meaning relative to a directory. When the launcher also changes the child's directory, the program may be resolved from the new directory, the caller's directory, or a platform-specific boundary.

Literal example from PR #72:

```text
proxy lives at /tmp/autopkgtest/mmdebstrap
→ child changes cwd to /tmp/debian-chroot
→ child executes ./mmdebstrap
→ kernel looks in /tmp/debian-chroot
→ launch fails with ENOENT
```

The review question is:

> Did the author mean “this executable inside the child directory,” or did the author select an executable somewhere else and then change the child directory?

## Why care

Linux Fieldwork hit this class directly in PR #72. A temporary proxy existed in the autopkgtest work directory, while one case changed directory before executing `./mmdebstrap`. The test failed before reaching package behavior.

A later repair pointed at `$SRC/mmdebstrap`, which survived the directory change but selected the imported source script instead of the installed-package proxy. The path became stable while the subject under test changed.

This class can produce:

- false missing-file failures;
- execution of the wrong source, wrapper, or generated binary;
- platform-specific results;
- test success against a decoy while the intended installed binary remains untested;
- command substitution after a chroot, pivot, container workdir, or privilege transition.

## Intent and precedent

- GNU `env --chdir=DIR` and `env -C DIR` change directory before command execution: https://www.gnu.org/software/coreutils/manual/html_node/env-invocation.html
- Rust says a relative program path combined with `Command::current_dir` has platform-specific and unstable behavior and recommends canonicalizing the program path first: https://doc.rust-lang.org/std/process/struct.Command.html#method.current_dir
- Python `subprocess.Popen` permits an `executable=` override, so argv display text and executable identity can differ: https://docs.python.org/3/library/subprocess.html#subprocess.Popen
- systemd accepts an absolute executable path or a simple filename searched in a fixed system path; relative paths containing `/` are excluded from that contract: https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
- GNU `realpath` provides canonical absolute path resolution when stable identity is required: https://www.gnu.org/software/coreutils/manual/html_node/realpath-invocation.html

These sources support an audit rule, not a universal defect verdict. A program deliberately built inside the child cwd can be a coherent relative launch.

## Audit tool

`tools/relative_exec_cwd_audit.py` reports three explicit pattern families:

- Python subprocess-style calls with `cwd=` and a literal relative selected executable containing `/` or `\`; `args=` and `executable=` are distinguished so a decoy argv name is not mistaken for executable identity;
- Rust `Command::new("relative/path")` chains with `.current_dir(...)`, including multiline string literals and the ordinary trailing comma;
- shell `env --chdir`, `env -C`, and absolute-path `.../env` launches, while consuming common value-taking options before the command.

POSIX and Windows absolute paths are evaluated with their own path rules. Drive-absolute, rooted Windows, and UNC paths are controls; drive-relative spellings such as `C:tools\runner.exe` remain findings.

The tool reports review prompts. It exposes text, JSON, and `--fail-on-findings` modes:

```sh
python3 tools/relative_exec_cwd_audit.py path/to/file.py path/to/build.rs
python3 tools/relative_exec_cwd_audit.py --json --fail-on-findings path/to/tree
```

## Second-pass review repair

Independent review found four blind spots in the first scanner head:

1. Python calls using `args=` were invisible, and `executable=` could select a different program than argv[0].
2. Rust matching ran line-by-line, so `Command::new(` with its literal on the next line was missed; a trailing comma also prevented a match.
3. GNU `env -C`, `/usr/bin/env`, and a preceding value-taking option such as `-u NAME` were missed.
4. The Linux runner's `os.path.isabs` treated Windows rooted and UNC paths as relative.

The repaired focused matrix uses distinct executable/decoy names and covers:

- Python positional `args`, keyword `args=`, literal `executable=`, absolute override, and dynamic override;
- single-line and multiline Rust builders;
- long, short, attached-short, and absolute-path GNU `env` forms;
- POSIX absolute, Windows drive-absolute, rooted, UNC, and drive-relative paths;
- text, JSON, clean-status, and fail-on-findings CLI behavior.

Local focused result before publication:

```text
python3 -m unittest tests.test_relative_exec_cwd_audit -v
Ran 15 tests
OK
```

Both scanner and test module also passed `python3 -m py_compile`. Exact-head repository and focused workflow receipts remain required after publication.

## Decision method

For every finding, answer four questions:

1. Where is the executable created or selected?
2. Which directory interprets its relative path on each supported platform?
3. Can a different file occupy the same spelling after the cwd change?
4. Which executable identity does the test or product claim to exercise?

A strong regression plants distinct markers at each plausible location and proves which one executes.

## RPFM research candidate

Repository: `Frodo45127/rpfm`

File: `rpfm_ui/build.rs`

Source observed on commit `cd255a4405f5cc052df3a5809b3aced5717496f5`:

```rust
Command::new("./../nuget.exe")
    .arg("restore")
    .arg("./QtRenderingWidget_RPFM.sln")
    .current_dir(renderer_path)
    .output()
```

The error message tells users to place `nuget.exe` in the repository root. `renderer_path` points below `3rdparty/src/qt_rendering_widget`. Rust documents the combined relative-program/current-dir boundary as platform-specific, so issue #223 proposed an absolute repository-root path as a hypothesis.

Searches for RPFM issues and pull requests containing `nuget current_dir` returned no result. No external contact occurred.

## Windows experiment

PR #222 ran a tracked Rust probe on GitHub's Windows Server 2025 runner image.

The fixture created two real marker executables:

```text
repository candidate:      <repo>/nuget.exe
child-relative candidate:  <repo>/3rdparty/src/nuget.exe
```

It launched:

```rust
Command::new("./../nuget.exe").current_dir(renderer)
```

from `<repo>/rpfm_ui`, then repeated the launch after deleting the child-relative candidate. An absolute repository-path launch served as the control.

Run `30584306362`, Windows artifact `relative-exec-cwd-windows-30584306362-1`, digest:

```text
sha256:9be2f5cd3e4bf7f293ade3f8b2e4fb11591f41f59c2c045a2f7b64749d275d7c
```

Observed identities:

```text
relative launch with both markers      → <repo>/nuget.exe
absolute control                       → <repo>/nuget.exe
relative launch after child deletion   → <repo>/nuget.exe
```

### Demonstrated behavior

On the tested Windows Server 2025 / Rust runner, the relative program resolved from the caller directory, not the child's `current_dir`. The repository-root marker ran in all three cases.

### Interpretation

The hypothesized current Windows failure did not reproduce. The RPFM code still relies on a Rust-documented platform-specific boundary, but its Windows-only build path behaved as intended on this runner.

### Design choice

Keep the checker finding as a portability and identity review prompt. Do not call the RPFM line a demonstrated defect. Close internal issue #223 with the negative result and preserve the absolute-path idea as optional cleanup, not a required repair.

### Open question

Other Windows versions, Rust versions, and toolchain launch layers remain untested. The result supports the current RPFM path on the tested environment; it does not convert Rust's API contract into a cross-platform guarantee.

## Alternatives considered

### Ban every relative executable with `cwd`

Too broad. A relative executable intentionally built inside the child cwd is coherent. The audit should force an identity decision and a regression.

### Require absolute paths everywhere

Strong for generated wrappers and selected local executables. Simple command names such as `make`, `git`, or `verilator` can still use an explicit PATH contract. The key risk is a relative path containing `/` whose intended base is unclear.

### Resolve after changing directory

This deliberately selects from the child cwd. It is correct when the executable belongs there. For a proxy or repository-root tool, resolve before launch.

### Trust successful execution

A decoy can make a command succeed while testing the wrong file. Identity controls still add value even when the launch succeeds.

## Related areas to explore

- test runners that combine generated wrappers with per-test cwd values;
- build systems launching repository tools from nested build directories;
- chroot, pivot-root, container `WORKDIR`, and namespace launchers;
- privilege wrappers selected through caller PATH before environment sanitization;
- temporary binaries deleted or replaced between resolution and execution;
- Windows drive-relative paths and platform differences in child executable search;
- commands assembled as strings and split after cwd changes.

## Evidence boundary

The checker recognizes literal high-signal patterns. It does not resolve variables, macros, helper functions, shell split strings, Rust builder variables, raw-string literals, symlink races, or executable replacement between review and launch. Python matching is intentionally subprocess-style by call name and can still produce review prompts for unrelated methods with the same name. Findings need human classification.

The Windows probe tested a reduced directory tree and marker executables, not RPFM's full Qt/NuGet build.

## Disposition

`REPAIR` pending exact-head focused and repository CI after the second-pass scanner repair.

The intended final decision is whether the checker, focused tests, repository inventory workflow, and Windows identity probe are reusable enough to merge as internal review tooling. The RPFM hypothesis remains a retained negative result.

## Authority

Internal Linux Fieldwork work only. No external contact is included or authorized.
