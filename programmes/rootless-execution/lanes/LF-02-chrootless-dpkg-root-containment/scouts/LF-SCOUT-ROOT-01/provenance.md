# LF-02 evidence provenance and portable views

## In simple words

The original hosted artifact recorded `git branch --show-current`. GitHub Actions checks out pull requests with a detached `HEAD`, so the retained branch field was empty even though the workflow knew the pull-request head and base refs.

The same artifact kept useful raw commands and traces, but their absolute runner paths made ordinary cross-run comparisons noisy. This record defines separate raw and normalized evidence layers instead of discarding either one.

Tracking: issue #110 and PR #115.

## Source boundary

- Scout investigation: issue #11 / PR #21
- Reviewed scout head: `f5c6b835bcc3283fc934718942c587593cb713af`
- Correction branch: `fix/lf-02-evidence-provenance`
- Validated implementation head: `33285c9e572792a238f4b1a1dfa1339699cc562f`
- Runner: `artifacts/run-probe.sh`
- Provenance helper: `artifacts/write-provenance.py`
- Regression: `tests/test_lf02_evidence_provenance.py`

## Original defect

The runner wrote:

```sh
repository_head="$(git rev-parse HEAD)"
repository_branch="$(git branch --show-current)"
```

The head SHA remained useful, but `repository_branch=` was empty in the detached Actions checkout. The artifact did not retain the corresponding `GITHUB_REF`, `GITHUB_HEAD_REF`, `GITHUB_BASE_REF`, run ID, or run attempt in a machine-readable record.

Command files also contained exact checkout and runner-temporary paths such as:

```text
/home/runner/work/linux-fieldwork/linux-fieldwork
/home/runner/work/_temp/lf-02-dpkg-root-containment
```

Those paths are valuable in raw traces but are not stable comparison keys.

## Corrected provenance schema

`provenance.json` schema version 1 records:

### Repository state

- checked-out `git rev-parse HEAD`;
- symbolic branch when one exists;
- explicit `detached_head` boolean;
- an `effective_ref` selected in this order:
  1. pull-request `GITHUB_HEAD_REF`;
  2. `GITHUB_REF_NAME`;
  3. full `GITHUB_REF`;
  4. local symbolic branch.

An absent branch is represented as JSON `null`, not an ambiguous empty string.

### GitHub Actions state

When present:

- repository slug;
- event name;
- workflow and workflow ref;
- run ID, run number, and run attempt;
- job name;
- `GITHUB_SHA`;
- ref, ref name, and ref type;
- head and base refs.

Local execution keeps the same schema with `active: false` and unavailable Actions fields set to `null`.

### Path views

The provenance record names the raw:

- repository root;
- runtime root;
- result directory.

It also declares stable tokens:

```text
<repo-root>
<runtime>
<result-dir>
```

## Raw versus normalized artifacts

Each traced command now has two views:

- `<phase>.command.raw`: exact argv rendering with original absolute paths;
- `<phase>.command`: portable view with declared path tokens.

Raw syscall traces remain unchanged. The correction does not erase execution context needed for diagnosis.

`summary.json` schema version 2 embeds the complete provenance object and maps every command name to both views.

## Regression contract

Focused tests require:

1. an Actions-style detached pull-request checkout retains head ref, base ref, merge ref, checked-out SHA, run ID, and attempt;
2. `repository_branch` is explicitly `<unset>` in the text view rather than empty;
3. local branch execution records `github_actions=false` and uses the symbolic branch as the effective ref;
4. empty Actions variables become JSON `null`;
5. normalized views replace repository, runtime, and result roots while raw views preserve them.

The hosted workflow additionally downloads the final artifact and asserts the provenance against its own run ID and attempt.

## Hosted validation

Run `30544282909` passed:

- containment job `90876375124`;
- provenance receipt job `90876464096`.

Artifact `8760014817` has digest `sha256:7e8c48ca83981b0247ee37031350957af6ed7fffceb7e30526aab8c65aae6aaa`.

The artifact receipt printed and asserted:

```text
summary_schema_version=2
provenance_schema_version=1
checked_out_head=6a09fed4649a7e6e69f466b1dadf5020886b2c6d
detached_head=true
effective_ref=fix/lf-02-evidence-provenance
github_sha=6a09fed4649a7e6e69f466b1dadf5020886b2c6d
github_ref=refs/pull/115/merge
github_head_ref=fix/lf-02-evidence-provenance
github_base_ref=scout/lf-scout-root-01/lf-02-dpkg-root-containment
github_run=30544282909 attempt=1
```

The workflow artifact metadata separately names branch head `33285c9e572792a238f4b1a1dfa1339699cc562f`. The checked-out SHA is the pull-request merge commit. Retaining both values makes that distinction explicit instead of calling either one "the branch."

All six traced phases had paired command views:

- direct install;
- direct reinstall;
- direct purge;
- direct install after purge;
- first mmdebstrap run;
- second mmdebstrap run.

The receipt required every normalized view to omit the declared repository and runtime roots and required every raw view to preserve at least one of them.

## Evidence limits

- `GITHUB_SHA` can name the pull-request merge commit while workflow artifact metadata names the head branch SHA. Both are retained rather than assumed equal.
- Repository paths remain in raw traces by design.
- The normalized command view currently replaces only the three declared roots. Other host-specific paths remain visible if they are semantically part of the command.
- This contract describes evidence provenance; it does not claim reproducible execution across runner images or package versions.

## Decision

**Retain the correction.** It removes the ambiguous empty branch field, preserves exact Actions identity, and adds portable command views without weakening the raw evidence layer.

## Authority

Internal Linux Fieldwork evidence-quality work only. No upstream contact.
