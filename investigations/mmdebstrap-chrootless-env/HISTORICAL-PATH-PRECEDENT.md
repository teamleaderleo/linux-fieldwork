# Historical executable-search and environment precedent

Date: 2026-07-30

Tracking: issues #40 and #107; investigation PR #105; candidate PR #109.

## Why this is a distinct class of problem

MITRE distinguishes two related search-path weaknesses:

- **CWE-426, Untrusted Search Path**: an external party controls the search path itself;
- **CWE-427, Uncontrolled Search Path Element**: the path is fixed, but an external party can write to one of its elements.

The mmdebstrap baseline in issue #107 is primarily CWE-426-shaped: the caller supplies the leading `PATH`, and the package manager later gives that combined value to maintainer scripts. A writable caller directory can also create a CWE-427-shaped element, but path ownership alone is not the whole issue.

- CWE-426: <https://cwe.mitre.org/data/definitions/426.html>
- CWE-427: <https://cwe.mitre.org/data/definitions/427.html>

MITRE's listed mitigations match the candidate's trust boundary:

- use known system paths;
- permit path configuration through an administrator-controlled configuration file rather than an external caller;
- remove or restrict environment search controls before invoking programs;
- prefer explicit executable paths where portability permits.

This supports treating apt's configured `DPkg::Path` as an authority while rejecting the unrelated caller prefix. It does **not** support silently discarding an explicit administrator configuration.

## Secure-programming guidance

SEI CERT ENV03-C treats inherited process environments as untrusted input and recommends explicitly constructing the environment passed to external programs when the required variables are known.

- ENV03-C: <https://wiki.sei.cmu.edu/confluence/display/c/ENV03-C.%2BSanitize%2Bthe%2Benvironment%2Bwhen%2Binvoking%2Bexternal%2Bprograms>

SEI CERT ENV04-C adds that a program name without a slash should be used only when `PATH` is known to be safe. Maintainer scripts deliberately invoke standard tools by name, so the package manager's supplied `PATH` is executable policy, not harmless metadata.

- ENV04-C: <https://wiki.sei.cmu.edu/confluence/pages/viewpage.action?pageId=87152177>

The lesson for this investigation is narrower than the privileged-program guidance: chrootless mode is normally unprivileged, but deterministic command resolution still matters for package correctness, reproducibility, and accidental execution from caller-controlled directories.

## Loader and interpreter controls

The Linux dynamic loader recognizes environment variables such as `LD_LIBRARY_PATH` and `LD_PRELOAD`. Secure-execution mode strips or ignores many of them for set-user-ID, set-group-ID, and capability transitions, but ordinary unprivileged chrootless execution does not gain that automatic boundary.

- dynamic loader environment: <https://man7.org/linux/man-pages/man8/ld-linux.so.8.html>
- `secure_getenv(3)`: <https://man7.org/linux/man-pages/man3/secure_getenv.3.html>

This reinforces the existing `env -i` design for the dpkg boundary. It also explains why conditional fakeroot loader state must be a documented exception rather than a general `LD_*` allowlist.

## Sudo and schroot precedent

Sudo's `secure_path` and environment-reset model are longstanding examples of separating the caller's interactive environment from a controlled execution environment. Schroot similarly uses a minimal environment by default and filters execution/search controls even when broader preservation is requested.

- sudoers environment and `secure_path`: <https://manpages.debian.org/trixie/sudo/sudoers.5.en.html>
- schroot environment: <https://manpages.debian.org/unstable/schroot/schroot.1.en.html>
- schroot environment filter: <https://manpages.debian.org/trixie/schroot/schroot.conf.5>

Neither tool is a direct behavioral template for mmdebstrap, but both demonstrate a stable design principle: preserve only the environment required at a trust boundary and make exceptions explicit.

## Authority model for `DPkg::Path`

APT documents `DPkg::Path` as the path supplied when apt invokes dpkg. The default is `/usr/sbin:/usr/bin:/sbin:/bin`, and an explicit empty value means apt leaves inherited `PATH` unchanged.

- APT NEWS: <https://sources.debian.org/src/apt/3.0.3/debian/NEWS>
- apt.conf(5): <https://manpages.debian.org/unstable/apt/apt.conf.5.en.html>

The candidate in PR #109 adopts the following explicit model:

1. a non-empty apt-configured path is authoritative, including a custom administrator path;
2. the caller's unrelated leading path is not authoritative for maintainer scripts;
3. an explicit empty `DPkg::Path` fails closed in chrootless mode because inheriting caller `PATH` would recreate issue #107;
4. this divergence from apt's ordinary empty-value behavior must be documented and tested.

The authority control must therefore prove both sides:

- a clean caller path plus a custom apt-configured fake directory resolves the fake command as configured behavior;
- the same fake directory supplied only by caller `PATH` does not resolve under the candidate.

## Anti-patterns reinforced by historical precedent

1. **Calling every writable path element the same problem.** Distinguish control of the path from write access to a fixed element.
2. **Checking ownership and writability once, then trusting forever.** This creates race-prone policy and does not address caller control of ordering.
3. **Hard-coding a universal path while claiming to honor administrator configuration.** Use a documented authority source.
4. **Inheriting the entire environment because one subsystem needs credentials.** Apt and dpkg are separate execution boundaries.
5. **Allowing an empty authority value to silently restore an unsafe fallback.** Make the compatibility decision explicit.
6. **Treating a safe search path as a sandbox.** It only controls command lookup; host filesystem, process, IPC, and network access remain.
7. **Testing only the secure outcome.** Retain a mutation or negative control that restores the old path behavior.

## Current conclusion

The respected guidance does not prove the exact mmdebstrap fix by itself. It supports the candidate architecture, while product-level package transactions establish whether that architecture works in both apt-managed and direct dpkg paths.

No Debian or upstream contact is authorized or performed by this record.
