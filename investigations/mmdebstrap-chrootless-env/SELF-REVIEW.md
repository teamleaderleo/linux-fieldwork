# Self-review: chrootless maintainer-script environment hardening

Reviewed source head: `6fb12c73233de1d5483b4399af5881d137e724d4`

Tracking: issue #40, draft PR #57.

## Security objective

Reduce the chance that `mmdebstrap --mode=chrootless` is started from a credential-rich shell and directly hands unrelated credentials or host-session endpoints to package maintainer scripts.

This change is defense in depth. It does not make chrootless package scripts safe to treat as untrusted code and does not create a filesystem, process, network, or IPC sandbox.

## Complete source-path review

The imported source has two chrootless dpkg execution paths that use `--force-script-chrootless`:

1. `run_essential()` invokes dpkg directly because apt would not run the `base-passwd` preinst early enough.
2. `run_install()` invokes apt, which then launches dpkg.

Both paths are covered:

- the direct path executes `env -i`, the explicit preserved environment, and then dpkg;
- the apt path keeps apt's caller environment but changes `Dir::Bin::dpkg` to `env`, passes the explicit environment as dpkg options, and then executes dpkg;
- the option order leaves apt's generated dpkg status-fd and package arguments after the dpkg executable, as before.

No root, unshare, or fakechroot execution path is changed.

## Fail-closed launch review

The new startup check runs only in chrootless mode. It is separate from the existing root/chrootless check, so `--skip=check/chrootless` does not silently disable the credential check.

The detector:

- matches common agent, session-bus, Kerberos, container-registry, cloud-credential, package-manager configuration, askpass, and credential-file variables;
- matches bounded name components such as token, secret, password, credential, private key, API key, access key, auth, JWT, and keytab;
- detects proxy and package-index URLs only when their URL authority embeds user information;
- returns a sorted unique list of variable names;
- never includes environment values in the error.

The explicit override is `--skip=check/chrootless/environment`. It bypasses only the launch refusal. The dpkg environment remains sanitized.

## Dpkg environment review

The default dpkg environment preserves only:

- `PATH`;
- mmdebstrap's noninteractive debconf controls;
- locale variables;
- `TZ` and `SOURCE_DATE_EPOCH`;
- `QEMU_LD_PREFIX` for foreign-architecture execution.

When and only when `FAKEROOTKEY` is active, it also preserves fakeroot's IPC and preload state: `FAKEROOTKEY`, `FAKED_MODE`, `FAKEROOT_FD_BASE`, `LD_PRELOAD`, and `LD_LIBRARY_PATH`.

`DPKG_ROOT` and `DPKG_ADMINDIR` are not copied from the caller. Dpkg creates them for maintainer scripts after the sanitized process starts.

`HOME`, agent sockets, session-bus addresses, cloud variables, registry authentication, arbitrary caller variables, and proxy variables are not passed directly to dpkg or maintainer scripts.

## Apt compatibility and residual risk

Apt retains its existing environment so that proxying, repository authentication, and apt helpers continue to work. This is a deliberate compatibility boundary, not isolation.

Consequences:

- default fail-closed launch behavior is the primary protection against credential-rich invocations;
- after an explicit override, apt or another ancestor process may still contain caller credentials;
- depending on host `/proc` policy and filesystem permissions, a same-user maintainer script may still inspect processes, derive home paths, read host files, or discover sockets;
- a malicious script can still execute host programs and issue host syscalls available to the invoking user.

The documentation states these limits and continues to require an unprivileged disposable container or chroot for meaningful containment.

## Regression review

The dedicated matrix uses fake values and purpose-built sockets only. It requires:

- direct chrootless dpkg to reproduce the original ambient credential and socket exposure;
- default mmdebstrap launch to reject credential, JWT, registry-auth, access-key, agent-socket, and credential-bearing proxy variables;
- the rejection to list names while redacting every supplied value;
- the explicit override to leave apt's non-credentialed proxy and fake token environment intact;
- the dpkg-maintainer-script boundary to remove direct credentials and socket paths;
- the fake agent socket to receive no connection;
- `PATH`, debconf controls, locale, `TZ`, `SOURCE_DATE_EPOCH`, `DPKG_ROOT`, and `DPKG_ADMINDIR` to remain correct;
- a supported fakeroot launch to preserve fakeroot state without restoring unrelated variables;
- a scrubbed launch and a second fresh run to succeed;
- current Debian sid perltidy output to match the committed source exactly.

The unrelated TMPDIR runtime and deep-review harnesses now launch chrootless mode from explicit clean environments instead of inheriting GitHub runner credentials.

## Review findings corrected before this record

1. The first formatter helper ran outside `upstream/mmdebstrap` and ignored its `.perltidyrc`; this was corrected before the source commit.
2. The first allowlist omitted fakeroot state and would have broken a supported chrootless mode; conditional fakeroot preservation and a live fakeroot regression were added.
3. Perl::Critic rejected `return sort ...`; the detector now builds a unique set, sorts it into an array, and returns the array.
4. Existing TMPDIR CI initially failed at the new credential check because it inherited GitHub runner tokens; those tests now use clean environments rather than bypassing the security check.

## Known limits

- Variable-name and URL-userinfo detection cannot identify every possible secret representation.
- Broad security-oriented name matching can reject benign variables; the override is explicit and documented.
- The full upstream source matrix and authenticated private-repository matrix have not been run.
- No claim is made that the override is safe for untrusted packages.
- No Debian or upstream contact has been made or authorized.

## Decision

The implementation is suitable for local retention once the final exact-head security, repository, TMPDIR runtime, and TMPDIR deep-review workflows pass. It should remain a draft and must not be represented as an upstream Debian fix until those checks are green and an upstream submission is separately authorized.
