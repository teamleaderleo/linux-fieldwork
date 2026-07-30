# mmdebstrap Debian sid autopkgtest reduction

Tracking: PR #72, issues #53, #54, #119, #153, and PR #171.

## Explain it simply

The package test runs hundreds of small cases. Linux Fieldwork temporarily places a tiny `mmdebstrap` proxy in the autopkgtest work directory. That proxy forwards each real invocation to the installed `/usr/bin/mmdebstrap` package while letting the reduction bypass source-format checks that belong to a newer source revision.

One test deliberately changes its working directory before it launches `mmdebstrap`. A command spelled `./mmdebstrap` then points inside the new directory. The proxy stays in the old autopkgtest work directory, so the command disappears from the test's point of view.

Run `30578966104` exposed exactly that failure at `(125/284) cwd-directory-not-accessible-by-unshared-user`:

```text
env: './mmdebstrap': No such file or directory
```

The run had already completed 77 cases and skipped `root-without-cap-sys-admin` out of the hook-heavy phase. The later authoritative hook-free phase never ran because the broad phase uses `--exitfirst`.

## Why we care

A harness failure can impersonate a product failure. Here it also blocked the exact Packet B case we meant to observe.

The tempting repair, `CMD="$SRC/mmdebstrap ..."`, reaches a stable path but executes the imported source script. That silently changes the subject under test. The experiment exists to exercise the installed Debian package through the proxy, so that repair would produce a convincing answer to a different question.

## Chosen repair

Use:

```text
$AUTOPKGTEST_TMP/mmdebstrap
```

The testsuite creates the proxy in `$AUTOPKGTEST_TMP` after changing into that directory. The absolute expanded path survives later working-directory changes. The proxy still executes `/usr/bin/mmdebstrap`, so the installed package remains the behavioral subject.

The regression creates two possible executables:

- a source-tree decoy that exits `97`;
- the intended proxy under the autopkgtest temporary directory.

It then changes directory and requires the intended proxy to receive the hook arguments. This proves both path stability and subject identity.

## Alternatives considered

### `./mmdebstrap`

Small and readable, but its meaning changes with the working directory. Run `30578966104` demonstrated the failure.

### `$SRC/mmdebstrap`

Stable across `chdir`, but `$SRC` names the imported source checkout. This bypasses the installed-package proxy and invalidates the reduction question.

### Bare `mmdebstrap`

This is the clean final package-test contract. It also restores the original source-preflight checks against the installed script. The broad reduction currently keeps a temporary proxy because the packaged script and imported source revision differ at those checks. Final reusable tooling should remove the proxy and prove the installed package through the original path.

### Copy the proxy into every possible working directory

This spreads test-only state across cases and misses future directory changes. One canonical executable path is easier to inspect and harder to misuse.

### Rewrite the individual cwd test

That hides a useful stress case. The test correctly asks whether the command remains executable after the cwd becomes inaccessible. The harness should supply a cwd-independent program path.

## Historical precedent

The rule appears in several mature process APIs:

- GNU `env --chdir=DIR` changes directory before invoking the command: https://www.gnu.org/software/coreutils/manual/html_node/env-invocation.html
- Rust documents relative program paths used with `Command::current_dir` as platform-specific and recommends canonicalizing the program path first: https://doc.rust-lang.org/std/process/struct.Command.html#method.current_dir
- systemd accepts either an absolute executable path or a simple name searched in a fixed system path; a relative path containing `/` is rejected: https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
- GNU `realpath` exists to turn path references into canonical absolute names when the caller needs stable identity: https://www.gnu.org/software/coreutils/manual/html_node/realpath-invocation.html

The shared lesson is straightforward: decide which program will run before changing directories, then carry a stable executable identity into the child launch.

## Packet B interpretation

The Packet B patch did what its focused tests claim:

- parser acceptance works;
- the capability case leaves the hook-heavy phase;
- ordinary statuses remain hard in the dedicated phase;
- timeout `124` remains neutral `77`.

The sid artifact did not execute the dedicated phase. It therefore neither validates nor refutes the runtime behavior of `root-without-cap-sys-admin` under the new schedule.

A further experiment-design question remains: the dedicated authoritative case sits after a broad `--exitfirst` matrix. Unrelated earlier failures can starve it. Two coherent designs are available:

1. preserve upstream phase order and keep rerunning after each earlier blocker is repaired;
2. in this reduction carrier only, defer the broad phase's ordinary failure, execute the focused authoritative phase, then restore the deferred status.

The second design gives the focused question priority while preserving the broad failure. It should remain an investigation-only carrier and never weaken the package's final failure result.

## Related defect class to audit

Search for child launches that combine any of these:

- `cwd=`, `current_dir`, `chdir`, `env --chdir`, `cd`, or a chroot/pivot operation;
- a relative executable containing `/`, especially `./tool`;
- a test proxy, wrapper, generated script, or temporary executable;
- a source-tree path that can be confused with an installed binary;
- a command string expanded after the directory change.

Useful negative controls plant different exit codes at the source path, installed path, and temporary proxy path. The test should prove which one actually executes.

## Current disposition

PR #72 remains an investigation carrier. The current exact head is recorded in the PR. The corrected proxy-path regression must pass, followed by a fresh disposable sid run. Packet B can advance once the dedicated hook-free phase itself executes and its exact status is retained.

## Authority

Internal Linux Fieldwork work only. No external contact is included or authorized.
