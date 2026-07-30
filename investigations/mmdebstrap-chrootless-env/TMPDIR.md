# Chrootless package-script target TMPDIR

## In simple words

The chrootless environment hardening candidate correctly clears arbitrary caller variables before starting dpkg. However, mmdebstrap had already replaced the caller `TMPDIR` with `<target>/tmp`. Removing that safe derived value makes ordinary package temporary-file helpers fall back to the host `/tmp`.

The bounded repair is to preserve mmdebstrap's target-derived `TMPDIR` in the dpkg allowlist. This does not restore the original caller path.

## Question

Does preserving the `TMPDIR` value established by `run_setup()` keep chrootless maintainer-script temporary files beneath the selected target for unprivileged and fakeroot runs without restoring arbitrary caller environment values?

## Existing work and duplicate search

- Related security-hardening record: issue #40 and PR #57.
- Review finding: issue #69.
- Exact diagnostic: PR #65.
- Existing TMPDIR PRs #1, #2, #4, #8, and #26 concern mmdebstrap's own temporary rootfs workspace, not package-script temporary paths.
- Repository searches found no prior package-script target-TMPDIR record.

## Source

- Project: imported Debian `mmdebstrap`
- Requested revision: `debian/1.5.7-3`
- Resolved upstream commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Candidate base: PR #57 head `32a9dec8d0e48032a7bf15b49d4dd1eb5bc0bb62`
- Local source: `upstream/mmdebstrap/mmdebstrap`
- Candidate patch: `mmdebstrap-chrootless-target-tmpdir.patch`

## Source and test map

`run_setup()`:

1. creates `<target>/tmp`;
2. sets its mode to `01777`;
3. overwrites `%ENV` so `TMPDIR=<target>/tmp`;
4. then `setup()` calls `run_essential()` and `run_install()`.

PR #57 adds `chrootless_dpkg_environment()`, shared by both direct and apt-managed chrootless dpkg execution. The helper uses `env -i` but omits `TMPDIR`, discarding the already-safe value.

The candidate adds `TMPDIR` to that shared allowlist. It does not accept a new caller path and does not change apt's environment.

## Baseline behavior

Exact review diagnostic:

- workflow run `30536099904` (repeat `30536099804`)
- PR #65
- candidate regression: success
- target-TMPDIR invariant: failure

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

- unmodified PR #57 source remains a negative control and creates its temporary directory below host `/tmp`;
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

Pending exact-head workflow execution.

## Cleanup and rerun

The runner validates its disposable runtime path before recursive deletion. Every package-created temporary directory is removed by the maintainer script. The candidate is immediately rerun into a fresh target. Final exact-head results remain pending.

## Interpretation

Source review establishes that preserving `TMPDIR` here is not equivalent to inheriting an arbitrary shell environment. `run_setup()` has already normalized it to the selected target and created the directory with Debian `/tmp` permissions.

## Evidence boundary

- The executable probe currently reaches the apt-managed local-package path.
- `run_essential()` uses the same helper, but a full essential-package transaction remains a separate dynamic control.
- The fixture uses `mktemp`; packages with custom temporary-location logic remain outside this probe.
- Chrootless maintainer scripts remain host-executing code and this repair is not a sandbox.

## Self-review

- Candidate source delta: one allowlist entry.
- Negative control is retained and asserted.
- Caller `TMPDIR` differs from the target-derived value.
- Cleanup and fresh rerun are asserted.
- Fakeroot is included when available.
- No real credential, external socket, package repository, or upstream contact is used.

## Peer review

Pending exact-head review of the stacked candidate pull request.

## Reusable notes

Related note: `notes/packaging/chrootless-maintainer-script-tmpdir.md`.

## Next step

Run the exact-head workflow, update this record with run IDs, and fold the one-line repair plus regression into PR #57 after review.

## Authority

No upstream issue, email, merge request, patch submission, comment, review, or other interaction is authorized or performed.
