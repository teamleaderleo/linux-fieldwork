# mmdebstrap chrootless environment security mitigation

Tracking: #40

## Confirmed baseline

PR #22 demonstrated that a chrootless package maintainer script receives caller-provided credential variables and session socket paths. The purpose-built script connected to the inherited fake `SSH_AUTH_SOCK` and sent a canary message. A blank-environment control removed the credentials and socket access.

This investigation treats the exposure as a chrootless-mode hardening defect, not as a claim that ordinary Debian package installation is sandboxed or that package scripts are untrusted by default.

## Source boundary

- imported source: `upstream/mmdebstrap/mmdebstrap`
- source revision: Debian `mmdebstrap` 1.5.7-3 plus reviewed local fixes already merged to `main`
- affected path: chrootless `apt-get`/`dpkg` execution, which currently inherits `%ENV`
- no upstream contact authorized

## Threat model

Chrootless mode deliberately runs package maintainer scripts without `chroot(1)`. Clearing environment variables does not make those scripts safe to treat as untrusted code.

A same-user script may still be able to:

- inspect ancestor or peer process environments through `/proc` where permissions allow;
- derive and read the caller home directory;
- discover sockets below runtime directories;
- execute host programs and access host paths permitted to the invoking user.

Therefore, environment filtering is only defense-in-depth against accidental direct inheritance. The primary mitigation must prevent users from unknowingly launching chrootless mode from a credential-rich session and must preserve the existing warning that a disposable containment boundary is required.

## Candidate designs

### A. Fail-closed launch check

Before chrootless package execution, inspect environment variable names for high-risk credentials and session endpoints. Refuse by default, listing names only and never values. Permit an explicit skip for users who have reviewed the risk.

Candidate exact names:

- `SSH_AUTH_SOCK`;
- `GPG_AGENT_INFO`;
- `DBUS_SESSION_BUS_ADDRESS`;
- `XDG_RUNTIME_DIR`;
- `KUBECONFIG`;
- `DOCKER_CONFIG`.

Candidate name patterns cover token, secret, password, credential, and private-key variables. The matrix must measure false positives before retaining a pattern.

Advantages:

- does not pretend to sandbox package scripts;
- prevents common accidental launches from desktop, CI, cloud, and agent-rich sessions;
- low impact on apt networking and authentication internals.

Risks:

- variable-name matching is incomplete;
- broad patterns may reject benign variables;
- users can bypass the check explicitly.

### B. Dpkg-only environment wrapper

Keep apt's environment intact for repository authentication and proxy access. Configure chrootless apt to execute dpkg through a temporary wrapper that constructs a minimal environment before dpkg starts package maintainer scripts.

Candidate preserved classes:

- `PATH`;
- locale variables set by mmdebstrap;
- `DEBIAN_FRONTEND` and `DEBCONF_*` noninteractive controls;
- `SOURCE_DATE_EPOCH` and `TZ` where needed for reproducibility;
- fakeroot's `FAKEROOTKEY`, preload, and daemon state when fakeroot is active.

Variables created by dpkg for maintainer scripts, including `DPKG_ROOT` and `DPKG_ADMINDIR`, remain available because dpkg supplies them after the wrapper starts it.

Advantages:

- blocks arbitrary caller variables from direct inheritance by maintainer scripts;
- does not strip proxy or repository credentials from apt itself;
- limits compatibility risk to dpkg and maintainer-script behavior.

Risks:

- still not a sandbox because `/proc`, home paths, and host filesystem access remain;
- maintainer scripts or helpers may rely on additional ambient variables;
- a wrapper path and cleanup lifecycle must be handled safely.

### C. Documentation and safe invocation

Document that chrootless mode is not a package-script sandbox. Recommend an unprivileged disposable container or chroot and a scrubbed launch environment. Do not recommend bypassing the root safety check on a normal host.

## Test matrix

1. Reproduce the original inherited environment with fake values only.
2. Require the launch check to reject a credential-rich environment and report variable names only.
3. Require the explicit skip to bypass only the launch refusal while the dpkg environment remains sanitized.
4. Apply the dpkg-wrapper candidate to a temporary copy of the imported source.
5. Require the package script not to receive:
   - `AWS_SECRET_ACCESS_KEY`;
   - `GITHUB_TOKEN`;
   - `SSH_AUTH_SOCK`;
   - `DBUS_SESSION_BUS_ADDRESS`;
   - an arbitrary `LF_SECRET_CANARY` variable.
6. Require no direct connection to the fake agent socket.
7. Record the filtered environment using names and redacted values only.
8. Verify required behavior for:
   - `PATH`;
   - `LC_ALL`/locale;
   - `DEBIAN_FRONTEND`;
   - relevant `DEBCONF_*` variables;
   - `SOURCE_DATE_EPOCH`;
   - `TZ`.
9. Verify the maintainer script still receives valid `DPKG_ROOT` and `DPKG_ADMINDIR` from dpkg.
10. Verify apt still sees proxy and repository-auth variables because filtering occurs only at the dpkg boundary.
11. Compare normalized target state with the unsanitized control.
12. Verify ordinary non-chrootless execution is unchanged.
13. Add `/proc` and host-file controls that demonstrate the remaining non-sandbox boundary.
14. Verify a fakeroot chrootless run preserves fakeroot state without restoring unrelated variables.
15. Verify cleanup and a second clean run.

## Decision rule

Retain the fail-closed launch check if it catches the demonstrated high-risk environment without unacceptable false positives. Retain the dpkg-only wrapper only if representative package and reproducibility tests pass and the documentation clearly states that it is defense-in-depth rather than isolation.

## Immediate safe-use guidance

Until a candidate is proven:

```sh
env -i \
  HOME=/nonexistent \
  PATH=/usr/sbin:/usr/bin:/sbin:/bin \
  LC_ALL=C.UTF-8 \
  DEBIAN_FRONTEND=noninteractive \
  mmdebstrap --mode=chrootless ...
```

Add only the proxy or reproducibility variables the invocation actually needs. Run as an unprivileged user inside a disposable container or chroot. Do not bypass the root chrootless safety check on a normal host.
