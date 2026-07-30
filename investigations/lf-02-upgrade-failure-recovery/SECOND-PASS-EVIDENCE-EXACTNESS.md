# LF-02 evidence names and types must be exact

## TL;DR

The LF-02 summarizer originally accepted target-path prefix collisions and could read a classifier-selected event file outside the retained results directory. Later peer review found the same escape for fixed-name inputs, an unsafe summary-output symlink, and JSON booleans accepted as integers.

The current repair routes every input through one symlink-free containment boundary, publishes `summary.json` atomically, and requires exact JSON integer types for schemas, durations, exit statuses, category counts, and totals.

## Explain like I'm five

A label saying “this happened inside `/tmp/target`” should not pass just because another path starts `/tmp/target-decoy`.

A receipt inside one evidence box should not be a shortcut to a different box. The final summary should replace a shortcut instead of writing through it.

And `true` should not count as the number `1`. Python normally allows that comparison, but an evidence schema must distinguish a yes/no answer from a numeric version or count.

## Why care

This investigation decides whether chrootless package behavior is mapped behavior, unresolved, or a product candidate. A look-alike target, substituted artifact, redirected output, or wrong JSON type can make the retained summary certify evidence different from what the contract describes.

The package lifecycle itself may be correct while the receipt overstates what was proved.

## Concrete failures

### Target prefix collision

```text
expected target: /tmp/target
logged target:   /tmp/target-decoy
old check:        expected text appears as a prefix → accepted
new check:        parsed dpkg_root value differs → rejected
```

### Artifact escape

```text
results directory: /tmp/run/results
recorded event:   ../outside.tsv
old check:         open the parent file
new check:         reject traversal before reading
```

### Fixed artifact symlink

```text
results/provenance.json -> ../outside-provenance.json
old check:                Path.read_text() follows the symlink
new check:                reject any symlink component below results
```

The same rule covers nested directory symlinks, phases, snapshots, classifier summaries, classifier TSVs, and `host-fingerprint.diff`.

### Summary output symlink

```text
results/summary.json -> ../unrelated.json
old write:            overwrite unrelated.json
new write:            write an in-root temporary and replace the symlink itself
```

### Boolean numeric look-alike

```json
{"schema_version": true, "duration_ms": true, "exit_status": false}
```

Python has `True == 1`, `False == 0`, and `isinstance(True, int)`. The old checks could therefore accept booleans for numeric evidence. The repair requires `type(value) is int` before applying version, minimum, or equality rules.

## Repair

`summarize.py` now:

1. parses script-log tokens as exact non-empty `key=value` fields;
2. rejects duplicate or missing required fields;
3. compares `dpkg_root` and `cwd` with the exact resolved target;
4. requires every evidence path to be relative, free of `..`, below the canonical results root, symlink-free below that root, and a regular file;
5. applies that boundary to every consumed input;
6. requires provenance, fixture, phase, snapshot, and classifier schema versions to be the integer `1`;
7. requires integer—not boolean—durations, exit statuses, category counts, category totals, and outside-event totals;
8. requires existing results and target directories;
9. publishes `summary.json` atomically and removes any abandoned temporary.

## Regression matrix

`tests/test_lf02_evidence_path_exactness.py` requires ordinary and real `python -O` agreement for rejection of:

- target-prefix collision;
- classifier parent traversal;
- fixed-file and nested-directory symlink escapes;
- phase and host-fingerprint symlinks;
- duplicate script fields;
- boolean schema version;
- boolean duration and exit status;
- boolean category count and totals.

A success control pre-creates `summary.json` as a symlink to an outside sentinel. Both modes must leave the sentinel unchanged, replace the symlink with a regular summary, and leave no hidden temporary.

## Evidence boundary

The script log remains a whitespace-separated fixture format; values containing spaces are outside the current contract. The validator proves pathname and JSON-type identity at read and summary-publication time. It does not prevent a process with mutation authority from racing a regular file after validation or replacing the configured results root.

## Disposition

`REPAIR` pending exact-head focused, dedicated lifecycle, and repository execution on PR #178. Every older receipt expired when this evidence boundary changed.

## Authority

Internal Linux Fieldwork work only. No external issue, patch, message, or review is authorized or created by this repair.
