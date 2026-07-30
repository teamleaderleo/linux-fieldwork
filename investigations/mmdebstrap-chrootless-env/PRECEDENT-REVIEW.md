# Chrootless maintainer-script environment precedent review

Date: 2026-07-30

Tracking: issue #40. Related reviews and repairs: PRs #57, #65, #73, and #74; issue #69.

## Scope

This review compares the merged Linux Fieldwork chrootless environment hardening with:

- Debian maintainer-script and dpkg contracts;
- existing mmdebstrap source and regression tests;
- schroot, sudo, bubblewrap, Nix, GNU `env`, POSIX locale, and FHS temporary-directory precedent;
- peer review findings already recorded on PRs #57, #73, and #74.

This is an internal research record. It does not authorize or perform upstream contact.

## Peer-review disposition

The first merged hardening in PR #57 correctly established a fail-closed credential-name check and a clean dpkg boundary, but exact-head peer review found that clearing `TMPDIR` caused package helpers to fall back to host `/tmp`. Issue #69 retained the reproduction.

PR #74 is the canonical correction. Its helper derives `<target>/tmp` from the selected root, rejects a final-component symlink or non-directory, creates the directory when absent, enforces mode `01777`, and supplies it through both chrootless dpkg call sites. The mutation control proves that removing the assignment restores host `/tmp` fallback. The review accepted the exact head after apt-managed, rerun, fakeroot, cleanup, style, and explicit-TMPDIR checks passed.

The discarded PR #73 only allowlisted the already-mutated environment value. Although its tested result was sound, PR #74 has the stronger contract because the helper receives the target root and derives the path itself.

## Current source boundary

`chrootless_dpkg_environment($root)` currently constructs an `env -i` argument list containing:

- target-derived `TMPDIR=<target>/tmp`;
- inherited `PATH`;
- `DEBIAN_FRONTEND`, `DEBCONF_NONINTERACTIVE_SEEN`, `LC_ALL`, `LANGUAGE`, and `LANG`;
- `TZ`, `SOURCE_DATE_EPOCH`, and `QEMU_LD_PREFIX` when defined;
- conditional fakeroot loader and daemon state.

The same helper is used by direct `run_essential()` dpkg and apt-managed `run_install()` dpkg.

Before option parsing, mmdebstrap itself overwrites the debconf and locale values with:

```text
DEBIAN_FRONTEND=noninteractive
DEBCONF_NONINTERACTIVE_SEEN=true
LC_ALL=C.UTF-8
LANGUAGE=C.UTF-8
LANG=C.UTF-8
```

Later, mmdebstrap appends apt's configured `DPkg::Path` to the caller's existing `PATH`; it does not replace the caller prefix.

## Established precedent

### Debian and dpkg

Debian Policy says maintainer scripts should invoke ordinary system tools through `PATH`, should not reset `PATH`, and may rely on the package management system having checked important tools. This makes the package manager's supplied path part of the execution contract rather than incidental shell state.

- Debian Policy, maintainer scripts: <https://www.debian.org/doc/debian-policy/ch-maintainerscripts.html>
- Debian Policy, environment defaults: <https://www.debian.org/doc/debian-policy/ch-opersys.html#environment-variables>
- dpkg `--force-script-chrootless`, `DPKG_ROOT`, and `DPKG_ADMINDIR`: <https://manpages.debian.org/testing/dpkg/dpkg.1.en.html>
- dpkg root-support/bootstrap specification: <https://wiki.debian.org/Teams/Dpkg/Spec/InstallBootstrap>

Dpkg explicitly warns that `--force-script-chrootless` can damage the host. `DPKG_ROOT` is a path-prefix contract for cooperating maintainer scripts, not transparent path virtualization.

### Clean-environment tools

GNU `env -i` starts from an empty environment and then applies explicit assignments. An unset variable is not equivalent to an empty assignment, which is why the original `TMPDIR` omission had a filesystem consequence.

- GNU Coreutils `env`: <https://www.gnu.org/s/coreutils/manual/html_node/env-invocation.html>

Schroot uses a minimal environment by default and treats whole-environment preservation as opt-in. Even when preservation is enabled, its default filter removes execution and search controls including `BASH_ENV`, `ENV`, `IFS`, `LD_*`, `NLSPATH`, resolver controls, and terminal-information paths.

- schroot environment contract: <https://manpages.debian.org/unstable/schroot/schroot.1.en.html>
- schroot filter configuration: <https://manpages.debian.org/trixie/schroot/schroot.conf.5>

Sudo's `env_reset`, `env_keep`, and `env_delete` model likewise separates a small accepted environment from explicit exceptions.

- sudoers environment policy: <https://manpages.debian.org/trixie/sudo/sudoers.5.en.html>

### Isolation is a separate layer

Bubblewrap documents that it is a mechanism for constructing a sandbox and that protection depends on the complete policy supplied by its caller. It supports `--clearenv`, but environment clearing alone is not its isolation model.

- bubblewrap security model: <https://github.com/containers/bubblewrap/blob/main/README.md>

Nix sandboxing isolates filesystem, process, IPC, and network resources in addition to controlling the build environment. This is useful precedent for keeping the mmdebstrap documentation explicit: environment scrubbing is defense in depth, not a sandbox.

- Nix sandbox configuration: <https://releases.nixos.org/nix/nix-2.31.3/manual/command-ref/conf-file.html#conf-sandbox>

### Locale and debconf

POSIX locale precedence is `LC_ALL`, then category-specific `LC_*`, then `LANG`. The current helper preserves mmdebstrap's forced `LC_ALL=C.UTF-8`, so omitted category-specific caller variables do not affect the resulting locale while `LC_ALL` remains set. Claims should therefore say that mmdebstrap's fixed C.UTF-8 locale is preserved, not that arbitrary caller locale configuration is preserved.

- POSIX environment variables: <https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap08.html>

Debconf documents `DEBIAN_FRONTEND`, `DEBIAN_PRIORITY`, database overrides, and `DEBCONF_NONINTERACTIVE_SEEN`. Current mmdebstrap intentionally forces the noninteractive frontend and seen behavior. The evidence supports preserving those two mmdebstrap-owned controls; it does not support a general promise to preserve all caller `DEBCONF_*` settings.

- debconf environment: <https://manpages.debian.org/unstable/debconf-doc/debconf.7.en.html>

## Existing mmdebstrap wisdom that should be reused

The imported `tests/chrootless` test already compares root and chrootless output for several package sets and snapshots the host tree before and after. It is the strongest existing basis for normalized target-state equality and host-mutation detection.

The imported `tests/chrootless-fakeroot` test already compares ordinary and fakeroot chrootless output for multiple package sets. New compatibility work should compose with these tests instead of inventing a weaker parallel equivalence claim.

The prior TMPDIR implementation review established another reusable rule: enforce a path contract at the actual operation instead of adding an early check-then-use probe.

## Anti-patterns to avoid

1. **Calling a clean environment a sandbox.** Same-user scripts may still inspect `/proc`, read accessible host files, discover sockets, execute host tools, and issue host syscalls.
2. **Unsetting a variable without testing its default.** `TMPDIR` demonstrated that omission can select host `/tmp`.
3. **Broad compatibility prose backed by a narrow allowlist.** Name the exact variables and whether values are caller-owned or mmdebstrap-owned.
4. **Preserving an entire environment to keep one feature working.** Keep apt authentication compatibility separate from the dpkg/maintainer-script environment.
5. **Name-only secret matching as a complete policy.** Secret names are useful for warning, but execution/search variables and credentials embedded in files or process state remain separate concerns.
6. **Caller-prefixed executable search paths without a test.** Maintainer scripts are expected to use `PATH`; therefore path ordering is executable behavior.
7. **Check-then-use filesystem validation.** Derive and validate at the operation boundary, and state remaining concurrent-modification limits.
8. **Recursive cleanup without canonical containment checks.** PR #74 corrected the retained harness by resolving and bounding disposable paths before deletion.
9. **A green harness that never reaches the product path.** Keep mutation controls, exact source assertions, and product-execution receipts separate.
10. **Claiming equality after comparing only selected logs.** Use the existing root-versus-chrootless archive comparison or narrow the claim.

## New focused question: maintainer-script PATH precedence

The current clean dpkg environment preserves `PATH`, but mmdebstrap constructs that value by appending apt's `DPkg::Path` to the caller's existing path. A caller-controlled directory therefore remains before the package-manager path.

This matters because Debian Policy explicitly expects maintainer scripts to resolve ordinary tools through `PATH`. The unresolved question is not whether a maintainer script is sandboxed; it is whether chrootless installation should execute tools from caller-writable path entries before the package manager's known tool path.

A dedicated probe on this branch uses a harmless command in a disposable caller path. It records whether an apt-managed chrootless maintainer script resolves that command from the caller directory and compares the result with a clean-path control. No production change is included.

## Further investigation queue

1. Run the PATH-precedence probe and retain exact evidence.
2. If reproduced, open a focused compatibility/hardening issue rather than expanding issue #40 with an unbounded fix.
3. Test a candidate where maintainer scripts receive a canonical package-manager path while apt retains the caller environment needed for repository access.
4. Execute a real essential-package chrootless transaction to cover direct `run_essential()` dynamically.
5. Run the imported root-versus-chrootless archive comparison against the candidate.
6. Add detector allow/deny examples for benign near-matches, mixed case, and URL userinfo.
7. Retain explicit `/proc` and host-file controls so the residual non-sandbox boundary stays visible.
8. Define override wording precisely: skipping the launch refusal does not restore the former maintainer-script environment.

## Authority

All work remains internal to `teamleaderleo/linux-fieldwork`. No Debian bug, email, merge request, upstream comment, or external review is authorized or performed by this record.
