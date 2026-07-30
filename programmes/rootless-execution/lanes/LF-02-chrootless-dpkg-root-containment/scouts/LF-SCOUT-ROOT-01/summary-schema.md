# LF-02 generated evidence summary schema

## In simple words

The original runner generated a JSON object by parsing human-oriented text files. Fixture metadata was a list of formatted lines, classifier categories kept bracketed display names, and the cleaner committed hosted receipt had to reshape the data manually.

This record defines a typed generated summary so the workflow artifact and later compact receipts use the same contract.

Tracking: issue #121.

## Source boundary

- Scout investigation: issue #11 / PR #21
- Provenance prerequisite: issue #110 / PR #115
- Summary correction branch: `fix/lf-02-generated-summary-schema`
- Classifier: `artifacts/classify-strace.py`
- Summary builder: `artifacts/summarize-probe.py`
- Runner: `artifacts/run-probe.sh`
- Regression: `tests/test_lf02_summary_schema.py`

## Original generated shape

The runner embedded the last two lines of `fixture.txt`:

```json
"fixture": [
  "<sha256>  /absolute/path/package.deb",
  "size=1018 mode=644 uid=..."
]
```

It also parsed text keys unchanged:

```json
"category[required host read]": 1003
```

The committed hosted summary later renamed those keys and reconstructed fixture fields manually. That created two summary contracts for one run.

## Schema version 3

PR #115 introduced summary schema version 2 for provenance and raw/normalized command views. This correction advances the generated summary to version 3.

### Fixture

The fixture is a typed object:

```json
{
  "package": "lf-fieldwork-probe",
  "version": "1.0",
  "architecture": "all",
  "archive_name": "lf-fieldwork-probe_1.0_all.deb",
  "size_bytes": 1018,
  "sha256": "..."
}
```

Package identity comes from `dpkg-deb -f`; size and digest come from the built archive.

### Tools

The summary records version and raw version text for:

- dpkg;
- apt;
- update-alternatives;
- strace;
- Perl;
- the imported mmdebstrap source.

`environment.txt` remains the broader human-readable execution record.

### Phases

Each traced phase is an object containing:

- exit status;
- UTC start and finish strings;
- observed wall-clock duration in milliseconds;
- retained command, stdout, stderr, status, and trace artifact names.

Duration is descriptive evidence. It is required to be non-negative but is not compared across runs or used as a pass/fail invariant.

### Classifications

The classifier emits both its existing text summary and a versioned JSON summary. Stable category identifiers are:

```text
required_host_read
harmless_runtime_interaction
unexpected_mutation
service_action
unresolved
```

Every structured classification records a category total and requires it to equal `outside_access_events`. Unknown, missing, or mismatched categories fail summary construction instead of silently producing a partial decision.

### Comparisons

Rerun comparisons are grouped under:

```json
"comparisons": {
  "host_fingerprint_unchanged": true,
  "mmdebstrap_rerun": {
    "maintainer_script_equal": true,
    "alternatives_state_equal": true,
    "artifacts": {}
  }
}
```

### Decision inputs

Raw evidence counts are separated from the derived decision:

```json
"decision_inputs": {
  "service_actions": 24,
  "unexpected_mutations": 0,
  "unresolved": 0,
  "promotion_signal": true,
  "rule": "promote when any service action or unexpected mutation is observed"
}
```

The final `decision` must agree with `promotion_signal`.

## Pass gate

Summary construction succeeds only when:

- all phase records exist and agree with their status files;
- every classification uses schema 1 and the exact category set;
- category totals equal outside-event totals;
- all phase exit statuses are zero;
- host fingerprint comparison is empty;
- both declared rerun comparisons are empty.

Service actions can still produce a successful probe with decision `promote`; they are findings, not harness failures.

## Migration

- Original generated artifact: unversioned / informal shape.
- PR #115: schema version 2, adding provenance and command views while retaining old classifier/fixture shapes.
- This correction: schema version 3, typed fixture, tools, phases, classifications, comparisons, and decision inputs.

Consumers should branch on `schema_version` rather than infer shape from field names.

## Regression contract

Focused tests cover:

- typed fixture and tool records;
- phase duration and artifact mapping;
- stable category identifiers;
- category-total equality;
- rejection of missing categories;
- rejection of impossible negative time ordering;
- explicit decision inputs and final decision.

The hosted artifact receipt rechecks the complete generated summary after downloading it from the exact workflow run.

## Evidence limits

- Timing is host-load dependent and not a reproducibility invariant.
- Tool version strings identify the executed environment but do not by themselves capture every package build dependency.
- Trace counts can vary while logical category invariants remain true.
- The summary references raw traces by glob rather than enumerating hundreds of per-process files.

## Validation

Exact correction head before this documentation-only receipt commit: `efe62caefa0a3f6a270b2d3dfad55e0beeb04097`.

Dedicated workflow run `30545542057` passed:

- containment job `90880625223`;
- downloaded-artifact receipt job `90880923046`.

Artifact `8760553863`, digest `sha256:31e908fa9939114671be5fdce0252a7e094eb2b736b3913666874e97223ab23e`.

The receipt asserted summary schema version 3, provenance schema version 1, exact run identity, typed fixture and tool fields, all six successful phase objects, non-negative observed durations, exact classification category totals, comparison booleans, explicit decision inputs, and paired raw/normalized command views.

Repository-wide `Linux Fieldwork CI` passed Python compilation and all unit tests, including the focused summary-schema regression, then failed in the inherited shell-help step because the old stacked base references an absent repository script. The lane-specific execution and exact artifact receipt are green.

## Authority

Internal Linux Fieldwork evidence-quality work only. No upstream contact.
