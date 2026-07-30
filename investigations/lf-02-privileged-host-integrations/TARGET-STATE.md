# LF-02 target-state comparison contract

## In simple words

The original summary proved that two selected package-facing components were equal across the default and control runs:

- the normalized maintainer-script log;
- the normalized `update-alternatives` database entry.

It did not compare those booleans with the full target tree manifest. The full trees differ, so those component equalities must not be described as whole-target equality.

This note records the correction for issue #100.

## Source boundary

- Investigation: PR #22
- D-Bus classifier stack: PR #99
- Target-state comparison branch: `fix/lf-02-target-state-comparison`
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

## Retained observed distinction

The earlier expanded evidence showed the default tree differed from the two controls. The controls contained:

```text
etc/apt/apt.conf.d/99mmdebstrap
```

where the default target did not.

The no-inhibit and isolated trees were otherwise equal in that retained comparison. The exact current matrix will be regenerated and recorded by the stacked workflow.

## Interpretation rule

Use the narrowest field that answers the question:

- package-script behavior: `maintainer_script_log_equal`;
- alternatives registration: `alternatives_database_equal`;
- whole captured filesystem manifest: `full_tree_manifest_equal`.

Do not say "target state is identical" unless the full-tree field is true and the manifest captures every relevant metadata dimension needed by the claim.

Even a full tree manifest has limits: this runner records relative path, type, mode, size, and link target. It does not currently hash every regular file, record ownership, xattrs, ACLs, timestamps, device numbers, or file contents.

## Regression

The focused unit test creates:

- equal normalized maintainer-script logs;
- equal alternatives entries;
- a default tree without `99mmdebstrap`;
- two equal control trees with that file.

It requires the component booleans to remain true while the full-tree boolean is false and the pairwise difference count is nonzero.

## Report correction

`RESULT.md` now says the normalized maintainer-script and alternatives observations remained equal. It explicitly avoids the previous broad sentence "Target package state remained identical."

## Next step

Run the exact-head privileged matrix, record the schema-3 tree comparison and pairwise counts, and classify the `99mmdebstrap` difference as expected or unexpected from source behavior.

## Authority

Internal Linux Fieldwork evidence-quality correction only. No upstream contact.
