# LF-02 evidence names must identify exact objects

## TL;DR

The LF-02 summarizer originally accepted target-path prefix collisions and could read a classifier-selected event file outside the retained results directory. A later peer review found the same escape remained for every fixed-name input: provenance, fixture manifest, phase records, snapshots, classifier summaries, and the host fingerprint.

The current repair routes every consumed file through one containment boundary, rejects symlinks anywhere below the results root, and publishes `summary.json` atomically so an existing output symlink is replaced rather than followed.

## Explain like I'm five

A label saying “this happened inside `/tmp/target`” should not pass just because the text also starts `/tmp/target-decoy`.

A receipt inside one evidence box should not be allowed to point through a shortcut to a different box. That applies whether the filename came from JSON or was hard-coded in the summarizer.

The final summary has the same rule: if `summary.json` is a shortcut to another file, replace the shortcut with the new summary. Do not write through it.

## Why care

This investigation decides whether chrootless package scripts ran against the intended target and whether every outside-target event was reconciled. A look-alike root or substituted artifact can make the summary certify evidence from another location.

The package lifecycle can be correct while the retained receipt overstates what was proved. An unsafe output path can additionally modify an unrelated file during validation.

## Concrete failures

### Target prefix collision

```text
expected target: /tmp/target
logged target:   /tmp/target-decoy
old check:        "dpkg_root=/tmp/target" appears in the line → accepted
new check:        parsed dpkg_root value differs → rejected
```

### Dynamic artifact escape

```text
results directory: /tmp/run/results
recorded event:   ../outside.tsv
old check:         open /tmp/run/results/../outside.tsv
new check:         parent traversal is rejected before reading
```

### Fixed artifact symlink escape

```text
results/provenance.json -> ../outside-provenance.json
old check:                Path.read_text() follows the symlink
new check:                any symlink component below results is rejected
```

The same rule covers nested directory symlinks such as `results/fixtures -> ../outside-fixtures`, phase JSON, snapshots, classifier summaries, and `host-fingerprint.diff`.

### Summary output symlink

```text
results/summary.json -> ../unrelated.json
old write:            overwrite unrelated.json
new write:            create a private in-root temporary and os.replace() the symlink itself
```

The outside target remains byte-identical and no temporary survives.

## Was this intentional?

No useful policy depends on prefix matching or cross-root evidence substitution. The script log already uses space-delimited `key=value` fields, and every input is meant to belong to the retained results set.

Allowing an in-root symlink to another evidence object would also weaken identity, even if its resolved path remained below the root. The validator therefore rejects symlink components rather than merely checking the final resolved prefix.

## Repair

`summarize.py` now:

1. parses every script-log token as one non-empty `key=value` field;
2. rejects duplicate or missing `phase`, `script_version`, `dpkg_root`, and `cwd` fields;
3. compares `dpkg_root` and `cwd` with the exact resolved target string;
4. checks failing and recovery postinst records through exact parsed fields;
5. requires every evidence path to be relative, free of `..`, below the canonical results root, symlink-free below that root, and a regular file;
6. uses that same loader for provenance, fixtures, phases, snapshots, classifier summaries, classifier event TSVs, and host fingerprint;
7. requires the results and target paths to exist as directories;
8. writes `summary.json` through an in-root temporary plus `os.replace()` and removes any temporary on failure.

## Regression matrix

`tests/test_lf02_evidence_path_exactness.py` mutates otherwise-valid synthetic evidence and requires rejection under ordinary Python and real `python -O` for:

- a target-prefix decoy;
- a classifier artifact parent escape;
- a fixed JSON symlink escape;
- a nested directory symlink escape;
- a phase-record symlink escape;
- a host-fingerprint symlink escape;
- a duplicate script-log field.

A separate success control pre-creates `summary.json` as a symlink to an outside sentinel. Both Python modes must complete successfully, leave the sentinel unchanged, replace the symlink with a regular summary, and leave no hidden temporary.

## Evidence boundary

The script log remains a deliberately simple whitespace-separated format; field values containing spaces are outside the current fixture contract. The validator proves retained pathname identity at open and publication time. It does not prevent a process with mutation authority from racing a regular file after validation or replacing the configured results root itself.

## Disposition

`REPAIR` pending exact-head focused and repository execution on the current PR #178 head. The older run receipts expire when this evidence boundary changes.

## Authority

Internal Linux Fieldwork work only. No external issue, patch, message, or review is authorized or created by this repair.
