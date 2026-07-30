# Keep chrootless package temporaries below the target

## In simple words

Clearing `TMPDIR` is not neutral when a package maintainer script runs without a chroot. Standard temporary-file tools then use the host `/tmp`.

If the package manager has already created a safe `<target>/tmp`, pass that derived path explicitly through any scrubbed environment. Do not restore an arbitrary caller-provided temporary path.

## What I learned

There are three different temporary-directory boundaries in a chrootless package build:

1. the caller's original `TMPDIR`;
2. mmdebstrap's own temporary rootfs/workspace selection;
3. the environment used by dpkg and package maintainer scripts.

They must not be conflated.

In the imported mmdebstrap flow, `run_setup()` creates `<target>/tmp`, sets mode `01777`, and replaces `%ENV{TMPDIR}` with that target-contained path before package installation. A later `env -i` wrapper that omits `TMPDIR` discards the safe normalization and causes tools such as `mktemp` to fall back to host `/tmp`.

The safe rule is:

- reject or normalize the caller's path first;
- derive a target-contained path;
- preserve only that derived value across the scrubbed dpkg boundary;
- assert the actual created path, not only the variable list.

Environment sanitization tests should include a filesystem consequence. Proving that a credential variable is absent does not prove that ordinary defaults remain contained.

## Source and provenance

- Project: imported Debian `mmdebstrap`
- Source revision: `debian/1.5.7-3`, resolved commit `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Owning code: `run_setup()` and `chrootless_dpkg_environment()` in `upstream/mmdebstrap/mmdebstrap`
- Merged hardening commit: `09e2c5ef74683723cca9cf70c1162dec0328750d`
- Investigation: `investigations/mmdebstrap-chrootless-env/TMPDIR.md`
- Issue: #69
- Original hardening: PR #57
- Repair candidate: PR #73

## Example

A package-script probe can record both the environment and the created path:

```sh
created="$(mktemp -d -t package-probe.XXXXXX)"
printf 'TMPDIR=%s\n' "${TMPDIR-<unset>}"
printf 'created=%s\n' "$created"
rmdir "$created"
```

Bad scrubbed result:

```text
TMPDIR=<unset>
created=/tmp/package-probe....
```

Target-contained result:

```text
TMPDIR=/tmp/build-target/tmp
created=/tmp/build-target/tmp/package-probe....
```

The second `/tmp` is part of the target path on the host, not the host's top-level `/tmp` namespace.

## Validation

The PR #65 diagnostic ran the credential/socket mitigation successfully and then deliberately failed a target-containment assertion. The package script observed `TMPDIR=<unset>` and created below host `/tmp`.

PR #73's retained candidate regression applies a one-line allowlist patch to a temporary source copy, requires merged main to reproduce host `/tmp`, and requires the candidate to use `<target>/tmp`, mode `1777`, with cleanup, fresh rerun, and fakeroot coverage.

Executed candidate head `43005ead9bd5967470a2095fd2c55914744e524e` passed:

- target-TMPDIR run `30536852201`, job `90852098465`;
- Linux Fieldwork CI run `30536852205`;
- chrootless environment security run `30536852182`.

Artifact `8757007293` has digest `sha256:c1246052455824d008d04a61b77fb2acc0b7c6a7baa0da301f56c7cb7729594b`.

## Environment and assumptions

- Linux host path semantics.
- dpkg `--force-script-chrootless` exports `DPKG_ROOT` but does not rewrite absolute paths used by scripts.
- `mktemp` follows `TMPDIR` and otherwise defaults to `/tmp`.
- mmdebstrap has already created and normalized `<target>/tmp` before dpkg starts.

## Limits

This lesson does not make chrootless maintainer scripts untrusted-safe. They can still access host resources permitted to the caller. It only prevents an environment-hardening wrapper from accidentally moving ordinary temporary files into the host default namespace.

Other temporary variables (`TMP`, `TEMP`), package-specific cache directories, language runtimes, and direct essential-package transactions require separate controls where relevant.

## Related work

- Related issue: #69
- Related hardening: PR #57
- Related repair: PR #73
- Related diagnostic: PR #65
- Related workspace TMPDIR work: PRs #1, #2, #4, #8, and #26
