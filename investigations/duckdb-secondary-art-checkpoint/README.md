# DuckDB same-process checkpoint wrong-result boundary

## TL;DR

A controlled release matrix reproduced a persisted wrong result when DuckDB 1.5.4 checkpoints a pending WAL through a second independently loaded engine in the same process. The same fixture is clean on 1.3.2.

The first probe proved the release boundary but did not yet prove the secondary ART execution path: the fresh `EXPLAIN` text reported a sequential scan even while the filtered count was wrong. The active repair adds no-index and primary-key controls, actual stored values, optimizer-disabled queries, `EXPLAIN ANALYZE`, and a higher-cardinality row before source-level conclusions.

## Explain like I'm five

Two copies of DuckDB open one database inside one process. One copy has new rows in a pending log. The second copy files that log. In the affected release, the saved database still says it has two rows, but asking for the row whose value is `1` returns zero.

That is a real wrong answer. We still need to prove whether the bad answer comes specifically from the secondary index or from another saved structure.

## Why care

This is persisted silent data correctness, not a loud crash. A later fresh client can return a false negative while broad row counts remain plausible. Any correction can affect checkpointing, WAL replay, locking, index persistence, embedding, and database-format behavior, so the evidence must identify the exact owner before changing source.

## Source and authority

- Project: DuckDB
- Controlled fork: `teamleaderleo/duckdb`
- Probe PR: `teamleaderleo/duckdb#10`
- Initial exact probe head: `362ac467dbb8d10e8f962cee1289237cedcd3722`
- Strengthened probe head: `e4543e7d2e6aa12f6d4e75ec2266ac9030e59fc5`
- Linux Fieldwork issue: #256
- Public report: https://github.com/duckdb/duckdb/issues/23788
- External contact: unauthorized and not made

The controlled fork changes evidence scripts and workflows only. No DuckDB product source is changed by this investigation yet.

## Mechanism under test

The fixture loads two matching DuckDB implementations into one process:

1. the Python package opens a file, creates a table and secondary index, inserts committed rows, and leaves the writer connection open with a pending WAL;
2. a separately loaded official `libduckdb.so` opens the same path read-write and triggers checkpoint/WAL replay;
3. the probe queries through the second engine;
4. the process calls `os._exit()` so Python/C++ destructor cleanup cannot let the first writer heal the file from its own in-memory state;
5. a fresh read-only Python client opens the persisted file and repeats the queries.

The use of `os._exit()` is deliberate evidence preservation. Ordinary cleanup occurs only after the artifact has been retained by the disposable hosted job.

## Initial hosted matrix

Workflow run: `30593662278`  
Conclusion: success  
Environment: Ubuntu 24.04.4, Python 3.12.13, matching official Python wheels and C libraries

### DuckDB 1.3.2 clean control

Observed probe record:

```json
{
  "corrupt": false,
  "full_count": 2,
  "indexed_count": 1,
  "python_duckdb_version": "1.3.2",
  "wal_present_before_checkpoint": true
}
```

Fresh read-only client:

```text
full count: 2
filtered count a=1: 1
```

Artifact:

- name: `secondary-art-1.3.2`
- ID: `8780312912`
- ZIP SHA-256: `66530b0115b758dad5d4163abbcc1bcc17d1e7e522348f73808b589991f33cc1`

### DuckDB 1.5.4 affected control

Observed probe record:

```json
{
  "corrupt": true,
  "full_count": 2,
  "indexed_count": 0,
  "python_duckdb_version": "1.5.4",
  "wal_present_before_checkpoint": true
}
```

Fresh read-only client:

```text
full count: 2
filtered count a=1: 0
```

Artifact:

- name: `secondary-art-1.5.4`
- ID: `8780334532`
- ZIP SHA-256: `bcd82fd045569b4e7b9a1f0baf762f2fd8e12acdc087fd2561055cebc6e11fe6`

## Evidence mismatch found during self-review

The initial fresh-client `EXPLAIN SELECT count(*) FROM t WHERE a = 1` text said `Sequential Scan` for both releases. That creates two possibilities:

- runtime execution still chooses an index path that plain `EXPLAIN` does not expose;
- another persisted structure or value path is wrong, and the secondary index is only a trigger rather than the executing lookup owner.

The initial test therefore supports this narrow claim:

> DuckDB 1.5.4, unlike 1.3.2, persists a filtered wrong result after the second-engine pending-WAL checkpoint fixture.

It does not yet independently support this stronger claim:

> The fresh query executed through a corrupt secondary ART index.

## Strengthened probe

The active fork head adds:

- secondary-index, primary-key, and no-index controls;
- actual `SELECT a FROM t ORDER BY a` values;
- optimizer-enabled and `PRAGMA disable_optimizer` filtered counts;
- `EXPLAIN ANALYZE` for both optimizer states;
- a 10,000-row secondary-index observation to encourage an authoritative selective index plan;
- aligned opaque C-result storage instead of a byte-aligned buffer;
- artifact upload before expected-result classification.

The exact strengthened head requires its own hosted receipt. No result is claimed from it until that workflow finishes.

## Questions the next result must answer

1. Is the wrong result present only when a secondary index exists?
2. Does a primary-key ART remain clean?
3. Do the physical row values remain `1, 2, ...`?
4. Does disabling the optimizer restore the filtered result?
5. Does `EXPLAIN ANALYZE` show an index scan at either cardinality?
6. Does current DuckDB source still reproduce when the Python and C engines share one exact source identity?

## Compatibility and blast radius

Potential repair directions have different costs:

- reject a second independent same-process engine open for one path;
- make locking or database-instance registration distinguish engine images rather than only PIDs;
- coordinate checkpoint ownership across instances;
- rebuild or validate secondary indexes from authoritative table/WAL state;
- repair one ART serialization transition.

Each can affect plugin embedding, language runtimes, process-global registries, startup time, read-only clients, crash recovery, and database compatibility. Source changes wait for the strengthened mechanism evidence.

## Cleanup and evidence limits

Hosted runners are disposable. Deliberately unclean process exit exists only to preserve the wrong database state before upload. The artifacts contain generated two-row databases and JSON/text results; no private data is involved.

The first run covers official Linux x86-64 release artifacts for 1.3.2 and 1.5.4. It does not establish the first bad commit, current-main status, other architectures, or supported-policy status for independently loaded engines.

## Current disposition

**REPAIR THE PROBE, THEN CONTINUE.** The release-boundary wrong result is retained. Mechanism attribution and any candidate correction remain on hold pending the strengthened exact-head run and current-source execution.