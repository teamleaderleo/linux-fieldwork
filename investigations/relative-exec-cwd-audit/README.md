# Relative executable after child cwd changes

Tracking: issue #194 follow-on review. Worker: Helper B.

## Explain it simply

A child process has two separate inputs:

1. the program to execute;
2. the directory where the child begins running.

A path such as `./tool` only has meaning relative to a directory. When the launcher also changes the child's directory, the program may be resolved from the new directory, the caller's directory, or a platform-specific boundary. A command that worked in one environment can disappear or execute a different file elsewhere.

The safest review question is:

> Did the author mean “this executable inside the child directory,” or did the author find an executable somewhere else and then change the child directory?

## Why we care

Linux Fieldwork hit this class directly in PR #72. A temporary proxy existed in the autopkgtest work directory, while one case changed directory before executing `./mmdebstrap`. The test failed with `ENOENT` before reaching the package behavior.

A later repair pointed at `$SRC/mmdebstrap`, which survived the directory change but selected the imported source script instead of the installed-package proxy. The path became stable while the subject under test changed.

This class can cause:

- false missing-file failures;
- silent execution of the wrong source, wrapper, or generated binary;
- platform-specific behavior;
- test success against a decoy while the intended installed binary remains untested;
- command substitution after a chroot, pivot, container workdir, or privilege transition.

## Audit tool

`tools/relative_exec_cwd_audit.py` reports three explicit patterns:

- Python child launch calls with `cwd=` and a relative argv[0] containing `/`;
- Rust `Command::new("relative/path")` chains with `.current_dir(...)`;
- shell `env --chdir ... relative/path` launches.

The tool reports review prompts. Some findings are intentional, such as executing `./obj_dir/simv` that was deliberately built below the child cwd. Reviewers should classify identity and intent instead of mechanically replacing every path.

Examples:

```sh
python3 tools/relative_exec_cwd_audit.py path/to/file.py path/to/build.rs
python3 tools/relative_exec_cwd_audit.py --json --fail-on-findings path/to/tree
```

## Decision method

For every finding, answer four questions:

1. Where is the executable created or selected?
2. Which directory is used to interpret its relative path on each supported platform?
3. Can a different file occupy the same spelling after the cwd change?
4. Which executable identity does the test or product claim to exercise?

A strong regression plants distinct exit codes or output markers at each plausible location and proves which one executes.

## Historical precedent

- GNU `env --chdir=DIR` changes directory before command execution: https://www.gnu.org/software/coreutils/manual/html_node/env-invocation.html
- Rust says a relative program path combined with `Command::current_dir` has platform-specific and unstable behavior and recommends canonicalizing the program path first: https://doc.rust-lang.org/std/process/struct.Command.html#method.current_dir
- systemd accepts an absolute executable path or a simple filename searched in a fixed system path; relative paths containing `/` are excluded from that contract: https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
- GNU `realpath` provides canonical absolute path resolution when stable identity is required: https://www.gnu.org/software/coreutils/manual/html_node/realpath-invocation.html

## External candidate found

Repository: `Frodo45127/rpfm`

File: `rpfm_ui/build.rs`

Observed code on commit `cd255a4405f5cc052df3a5809b3aced5717496f5`:

```rust
Command::new("./../nuget.exe")
    .arg("restore")
    .arg("./QtRenderingWidget_RPFM.sln")
    .current_dir(renderer_path)
    .output()
```

The error message instructs users to place `nuget.exe` in the repository root, while `renderer_path` points below `3rdparty/src/qt_rendering_widget`. The executable path and child cwd therefore rely on Rust's documented ambiguous boundary. The likely repair is to resolve the repository-root `nuget.exe` to an absolute `PathBuf` before setting the child cwd.

Searches for open issues and pull requests containing `nuget current_dir` returned no match. This is an internal research candidate only. No issue, pull request, comment, or message was sent.

## Alternatives considered

### Ban every relative executable with `cwd`

Too broad. A relative executable intentionally built inside the child cwd is coherent. The audit should force an identity decision and a regression.

### Require absolute paths everywhere

Strong for generated wrappers and selected local executables. Simple command names such as `make`, `git`, or `verilator` can still use an explicit PATH contract. The key is to avoid a relative path containing `/` whose base is ambiguous.

### Resolve after changing directory

This deliberately selects from the child cwd. It is correct only when the executable belongs there. For a proxy or repository-root tool, resolve before launch.

### Trust successful execution

A decoy at the child path can make the command succeed while testing the wrong file. Identity controls are required.

## Related areas to explore

- test runners that combine generated wrappers with per-test cwd values;
- build systems launching repository tools from nested build directories;
- chroot, pivot-root, container `WORKDIR`, and namespace launchers;
- privilege wrappers whose executable is selected through caller PATH before environment sanitization;
- temporary binaries deleted or replaced between resolution and execution;
- Windows drive-relative paths and platform differences in child executable search;
- commands assembled as strings and split after cwd changes.

## Disposition

`MERGE LOCALLY`

The checker and focused tests are internal review tooling. The external RPFM candidate remains research-only until a deliberate external-contact decision exists.

## Authority

Internal Linux Fieldwork work only. No external contact is included or authorized.
