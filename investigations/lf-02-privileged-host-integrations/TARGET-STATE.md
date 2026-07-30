# LF-02 target-state comparison contract

## In simple words

The original summary proved that two selected package-facing components were equal across the default and control runs:

- the normalized maintainer-script log;
- the normalized `update-alternatives` database entry.

It did not compare those booleans with the full target tree manifest. The full trees differ, so those component equalities must not be described as whole-target equality.

This note records the correction and exact hosted matrix for issue #100.

## Source boundary

- Investigation: PR #22
- D-Bus classifier stack: PR #99
- Target-state comparison PR: #104
- Validated comparison head: `868087a696b955914bed7dac0ca33302f56bf3f2`
- Summary implementation: `summarize_results.py`
- Tree inputs: `<case>-tree.tsv`
- Regression: `tests/test_lf02_privileged_summary.py`

## Original fields

The compatibility fields remain:

```json
{
  "target_script_state_equal": true,
  "target_alternatives_state_equal": true
}
```

Their exact meanings are:

- `target_script_state_equal`: the normalized fixture maintainer-script logs are byte-equal;
- `target_alternatives_state_equal`: the normalized fixture alternatives database entries are byte-equal.

Neither field covers every file or metadata entry in the target.

## Corrected schema

Schema version 3 adds:

```json
{
  "target_tree_state_equal": false,
  "target_state_comparison": {
    "maintainer_script_log_equal": true,
    "alternatives_database_equal": true,
    "full_tree_manifest_equal": false,
    "tree_pairwise": {}
  }
}
```

Each pairwise tree entry records:

- left and right case names;
- an equality boolean;
- the number of added/removed manifest lines;
- the retained unified-diff artifact name.

The summarizer writes all three pairwise diff files into the result directory.

## Exact hosted results

Exact-head run `30543204388` passed:

- privileged matrix job `90872718011`;
- compact contract job `90872847423`;
- focused tree-diff job `90872847506`.

Artifact `8759572657` has digest `sha256:e542ba9eaac47697daccdc633342e3b717cea7e99b25200a29abf5b4afeaed86`.

The schema-3 summary reported:

```text
target_state: script_equal=true alternatives_equal=true tree_equal=false
default_vs_no_inhibit: equal=false difference_lines=3
default_vs_isolated: equal=false difference_lines=3
no_inhibit_vs_isolated: equal=false difference_lines=2
```

### Default versus either control

Both controls add:

```text
etc/apt/apt.conf.d/99mmdebstrap  file  mode=644  size=61
```

This is expected control-specific state. The runner supplies two `--aptopt` values only for the no-inhibit and isolated cases. The imported project's `tests/aptopt` contract confirms that supplied apt options are persisted in `etc/apt/apt.conf.d/99mmdebstrap`.

The other pairwise change is the raw size of:

```text
var/lib/lf-fieldwork-probe/script.log
```

Observed sizes were:

- default: 457 bytes;
- no-inhibit: 469 bytes;
- isolated: 461 bytes.

The fixture log records the absolute `DPKG_ROOT`, so changing the case label changes the raw byte length. The separately normalized logs replace the target path and are byte-equal. This is an expected path-length artifact, not a behavioral divergence.

### No-inhibit versus isolated

The only captured tree-manifest difference is the raw `script.log` size, 469 versus 461 bytes. Both contain `99mmdebstrap`, and their normalized script logs and alternatives entries are equal.

## Interpretation rule

Use the narrowest field that answers the question:

- package-script behavior: `maintainer_script_log_equal`;
- alternatives registration: `alternatives_database_equal`;
- raw captured filesystem manifest: `full_tree_manifest_equal`.

Do not say "target state is identical" unless the full-tree field is true and the manifest captures every relevant metadata dimension needed by the claim.

A false raw-tree result does not by itself mean the package behaved differently. Inspect the retained pairwise diffs and classify expected control files, target-path-dependent fixture bytes, and unexplained differences separately.

Even a full tree manifest has limits: this runner records relative path, type, mode, size, and link target. It does not currently hash every regular file, record ownership, xattrs, ACLs, timestamps, device numbers, or file contents.

## Regression

The focused unit test creates:

- equal normalized maintainer-script logs;
- equal alternatives entries;
- a default tree without `99mmdebstrap`;
- two control trees with that file.

It requires the component booleans to remain true while the full-tree boolean is false and the pairwise difference count is nonzero.

The hosted workflow additionally downloads the retained artifact, asserts all structured fields, checks every named diff exists, and prints the complete tree differences in a dedicated short job.

## Report correction

`RESULT.md` now says the normalized maintainer-script and alternatives observations remained equal. It explicitly avoids the previous broad sentence "Target package state remained identical."

## Remaining improvement

A future manifest can add content hashes and a normalized comparison view while retaining the raw tree. That should be a separate schema revision because normalizing target-dependent content requires an explicit field-by-field contract.

## Authority

Internal Linux Fieldwork evidence-quality correction only. No upstream contact.
