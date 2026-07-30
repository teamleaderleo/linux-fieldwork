# LF-02 evidence names must identify exact objects

## Explain it like I am five

A label saying “this happened inside `/tmp/target`” should not pass merely because the text also appears at the start of `/tmp/target-decoy`.

Likewise, an evidence receipt stored inside one results directory should not be allowed to say “the supporting event file is somewhere above me” and have the validator silently read it.

The earlier summarizer used substring checks for maintainer-script `dpkg_root` and `cwd` fields, and joined a classifier-provided artifact filename without first requiring that it stay inside the results directory.

## Why should anyone care?

This investigation is deciding whether chrootless package scripts ran against the intended target and whether every outside-target event has been reconciled. A look-alike pathname can make the summary certify the wrong execution root. An escaping artifact reference can substitute unrelated event rows for the evidence produced by the phase being summarized.

The package lifecycle itself can be correct while the receipt overstates what was proved.

## Concrete failures

### Prefix collision

```text
expected target: /tmp/target
logged target:   /tmp/target-decoy
old check:        "dpkg_root=/tmp/target" appears in the line → accepted
new check:        parsed dpkg_root value differs → rejected
```

### Artifact escape

```text
results directory: /tmp/run/results
recorded event:   ../outside.tsv
old check:         open /tmp/run/results/../outside.tsv
new check:         parent traversal is rejected before reading
```

## Was this intentional?

No useful policy depends on prefix matching here. The script log is already emitted as space-delimited `key=value` fields, and the artifact field is meant to name a file belonging to the retained results set. The old behavior was a compact validation shortcut.

## Repair

`summary.py` now:

1. parses every script-log token as one non-empty `key=value` field;
2. rejects duplicate or missing `phase`, `script_version`, `dpkg_root`, and `cwd` fields;
3. compares `dpkg_root` and `cwd` with the exact resolved target string;
4. checks the failing and recovery postinst records through exact parsed fields;
5. requires classifier event paths to be relative, free of `..`, resolved below the results root, and regular files before reading.

`tests/test_lf02_evidence_path_exactness.py` mutates otherwise-valid synthetic evidence and requires rejection under ordinary Python and real `python -O` for:

- a target-prefix decoy;
- a classifier artifact parent escape;
- a duplicate script-log field.

## Local focused gate

The parsing and containment helpers passed three focused tests under ordinary and optimized Python, and the repaired summarizer passed Python compilation before publication. Repository exact-head execution remains the authoritative integrated gate.

## Evidence boundary

The script log remains a deliberately simple whitespace-separated format; field values containing spaces are outside the current fixture contract. The validator proves exact retained names, not resistance to a process that can alter files concurrently during validation.

## Authority

Internal Linux Fieldwork work only. No external issue, patch, message, or review is authorized or created by this repair.
