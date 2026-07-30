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

## Candidate designs

### A. Denylist

Remove high-risk credential and session variables immediately around chrootless apt/dpkg execution.

Advantages:

- narrow compatibility impact;
- easy to explain and test.

Risks:

- incomplete by construction;
- secret variable names are open-ended;
- future credential helpers and sockets can bypass the list.

### B. Allowlist

Construct a minimal environment for chrootless apt/dpkg execution and preserve only demonstrated requirements.

Candidate preserved classes:

- `PATH`;
- locale variables needed for deterministic parsing;
- `DEBIAN_FRONTEND` and related noninteractive controls;
- proxy variables required for repository access;
- `SOURCE_DATE_EPOCH` where reproducibility depends on it;
- mmdebstrap internal variables required by the execution path.

Variables created by dpkg for maintainer scripts, including `DPKG_ROOT` and `DPKG_ADMINDIR`, must remain available because dpkg supplies them after mmdebstrap starts the subprocess.

Advantages:

- blocks arbitrary caller secrets and unanticipated socket variables;
- has a defensible security boundary.

Risks:

- compatibility regressions if apt, authentication helpers, proxies, or user workflows rely on ambient variables;
- exact preservation rules require evidence, not guesses.

## Test matrix

1. Reproduce the original inherited environment with fake values only.
2. Apply each candidate to a temporary copy of the imported source.
3. Require the package script not to receive:
   - `AWS_SECRET_ACCESS_KEY`;
   - `GITHUB_TOKEN`;
   - `SSH_AUTH_SOCK`;
   - `DBUS_SESSION_BUS_ADDRESS`;
   - an arbitrary `LF_SECRET_CANARY` variable.
4. Require no connection to the fake agent socket.
5. Record the complete sanitized environment using names and redacted values only.
6. Verify required behavior for:
   - `PATH`;
   - `LC_ALL`/locale;
   - `DEBIAN_FRONTEND`;
   - `SOURCE_DATE_EPOCH`;
   - HTTP and HTTPS proxy variables;
   - apt authentication helpers, if applicable.
7. Verify the maintainer script still receives valid `DPKG_ROOT` and `DPKG_ADMINDIR` from dpkg.
8. Compare normalized target state with the unsanitized control.
9. Verify ordinary non-chrootless execution is unchanged.
10. Verify cleanup and a second clean run.

## Decision rule

Prefer an allowlist only if the representative package and network-access matrix passes without hidden dependencies. Otherwise retain a narrow denylist as an immediately reviewable hardening candidate while documenting the residual risk.

## Immediate safe-use guidance

Until a candidate is proven:

```sh
env -i \
  HOME="$HOME" \
  PATH=/usr/sbin:/usr/bin:/sbin:/bin \
  LC_ALL=C.UTF-8 \
  DEBIAN_FRONTEND=noninteractive \
  mmdebstrap --mode=chrootless ...
```

Add only the proxy or reproducibility variables the invocation actually needs. Run as an unprivileged user inside a disposable container or chroot. Do not bypass the root chrootless safety check on a normal host.
