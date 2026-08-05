# runc cgroups JSON omission boundary

Tracks Linux Fieldwork issue #450.

## Question

What changed in JSON output when runc moved from `github.com/opencontainers/cgroups v0.0.6` to v0.0.8, and are the old and new representations semantically round-trip compatible?

The dependency changed config and stats tags from `omitempty` to `omitzero`. This harness compares exact pinned generations rather than relying only on general tag semantics.

## Samples

The shared serializer emits:

- an empty `cgroups.Cgroup`;
- a cgroup with a non-nil all-zero `Resources`;
- a cgroup with non-nil empty `HugetlbLimit` and `Unified` collections;
- a non-zero resource control;
- an empty `cgroups.Stats`.

It records both encoded JSON and collection shape (`nil` versus non-nil empty) for the config samples.

## Matrix

The hosted workflow produces four reports:

1. v0.0.6 native construction;
2. v0.0.8 native construction;
3. v0.0.6 decoding and re-encoding the v0.0.8 report;
4. v0.0.8 decoding and re-encoding the v0.0.6 report.

A Python classifier retains per-sample byte/JSON differences and nilness changes. It does not label any difference a defect automatically.

## Interpretation

- A missing field that decodes to the same effective cgroup behavior may be internal state text churn.
- Loss of non-nil empty collection identity is observable Go semantics, but still needs a real runc call-site owner before promotion.
- Failure to decode or preservation of a stale non-zero value would be a stronger compatibility defect.
- `runc events --stats` is a negative control because runc converts dependency stats into runc-owned output structs before JSON encoding.

## Authority

Internal Linux Fieldwork only. No upstream contact is authorized or made.
