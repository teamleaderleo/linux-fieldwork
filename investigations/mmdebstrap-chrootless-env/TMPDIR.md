# Chrootless package-script target TMPDIR

## In simple words

The merged chrootless environment hardening clears arbitrary caller variables before starting dpkg. However, mmdebstrap had already replaced the caller `TMPDIR` with `<target>/tmp`. Removing that safe derived value makes ordinary package temporary-file helpers fall back to the host `/tmp`.

The bounded repair is to preserve mmdebstrap's target-derived `TMPDIR` in the dpkg allowlist. This does not restore the original caller path.

## Question

Does preserving the `TMPDIR` value established by `run_setup()` keep chrootless maintainer-script temporary files beneath the selected target for unprivileged and fakeroot runs without restoring arbitrary caller environment values?

## Existing work and duplicate search

- Related security-hardening record: issue #40 and merged PR #57.
- Review finding: issue #69.
- Exact diagnostic: PR #65.
- Superseded stacked candidate: PR #70.
- Existing TMPDIR PRs #1, #2, #4, #8, and #26 concern mmdebstrap's own temporary rootfs workspace, not package-script temporary paths.
- Repository searches found no prior package-script target-TMPDIR record.

## Source

- Project: imported Debian `mmdebstrap`
- Requested revision: `debian/1.5.7-3`
- Resolved upstream commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Merged environment-hardening commit: `09e2c5ef74683723cca9cf70c1162dec0328750d`
- Merged PR #57 head: `5ebb8095288c7b3c11a4d23e2a329d6424f6a96e`
- Local source: `upstream/mmdebstrap/mmdebstrap`
- Candidate patch: `mmdebstrap-chrootless-target-tmpdir.patch`
- Candidate branch: `fix/mmdebstrap-chrootless-target-tmpdir-main`

## Source and test map

`run_setup()`:

1. creates `<target>/tmp`;
2. sets its mode to `01777`;
3. overwrites `%ENV` so `TMPDIR=<target>/tmp`;
4. then `setup()` calls `run_essential()` and `run_install()`.

PR #57 added `chrootless_dpkg_environment()`, shared by both direct and apt-managed chrootless dpkg execution. The helper uses `env -i` but omits `TMPDIR`, discarding the already-safe value.

The candidate adds `TMPDIR` to that shared allowlist. It does not accept a new caller path and does not change apt's environment.

## Baseline behavior

Exact review diagnostic:

- workflow run `30536099904` (repeat `30536099804`)
- job `90849239211`
- PR #65
- candidate credential/socket regression: success
- target-TMPDIR invariant: failure
- artifact `8756657860`
- digest `sha256:31fcfe69a249bfe9d237238fa33d1e965c29f403bded3201fa8d6401527e849a`

Observed package-script result:

```text
script_tmpdir=<unset>
created=/tmp/lf-chrootless-tmp.BZQPka
outside_target_temp=yes
```

The fixture removed the temporary directory before exiting.

## Hypothesis or candidate

Add `TMPDIR` to the names preserved by `chrootless_dpkg_environment()`.

Expected outcomes:

- merged main without the repair remains a negative control and creates its temporary directory below host `/tmp`;
- the candidate package script receives exactly `<target>/tmp`, not the caller path;
- `mktemp` creates below `<target>/tmp`;
- target `/tmp` is mode `1777`;
- the temporary directory is removed;
- a fresh rerun converges;
- fakeroot preserves the same target-derived invariant;
- both direct and apt-managed dpkg paths use the shared helper.

## Reproduction

```sh
bash investigations/mmdebstrap-chrootless-env/run-target-tmpdir-regression.sh
```

The runner copies the imported source, applies the one-line candidate patch, builds a dependency-free local package, executes the negative control and candidate cases, and retains compact summaries.

## Assertions and negative control

The negative control requires:

```text
TMPDIR=<unset>
created=/tmp/...
```

The candidate requires:

```text
TMPDIR=<target>/tmp
created=<target>/tmp/...
target_tmp_mode=1777
```

It also requires the created directory not to survive, then repeats the candidate in a fresh target and under fakeroot when available.

## Results

The first stacked candidate run `30536534715` passed against the PR #57 stack. A replacement branch was created directly from current `main` after PR #57 merged; exact-head replacement validation is pending.

## Cleanup and rerun

The runner validates its disposable runtime path before recursive deletion. Every package-created temporary directory is removed by the maintainer script. The candidate is immediately rerun into a fresh target. Final exact-head replacement results remain pending.

## Interpretation

Source review and the first candidate run establish that preserving `TMPDIR` here is not equivalent to inheriting an arbitrary shell environment. `run_setup()` has already normalized it to the selected target and created the directory with Debian `/tmp` permissions.

## Evidence boundary

- The executable probe currently reaches the apt-managed local-package path.
- `run_essential()` uses the same helper, but a full essential-package transaction remains a separate dynamic control.
- The fixture uses `mktemp`; packages with custom temporary-location logic remain outside this probe.
- Chrootless maintainer scripts remain host-executing code and this repair is not a sandbox.

## Self-review

- Candidate source delta: one allowlist entry.
- Negative control is retained and asserted against merged main.
- Caller `TMPDIR` differs from the target-derived value.
- Cleanup and fresh rerun are asserted.
- Fakeroot is included when available.
- No real credential, external socket, package repository, or upstream contact is used.

## Peer review

Pending exact-head review of the replacement pull request based on current `main`.

## Reusable notes

Related note: `notes/packaging/chrootless-maintainer-script-tmpdir.md`.

## Next step

Run the replacement exact-head workflow, record the run IDs and artifact digest, and request review before merging the one-line repair into `main`.

## Authority

No upstream issue, email, merge request, patch submission, comment, review, or other interaction is authorized or performed.
