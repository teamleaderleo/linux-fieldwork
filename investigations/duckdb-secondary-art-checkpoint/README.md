# DuckDB same-process checkpoint wrong-result boundary

## TL;DR

A controlled release matrix reproduced a persisted secondary-index wrong result when DuckDB 1.5.4 checkpoints a pending WAL through a second independently loaded engine in the same process. The same fixture is clean on 1.3.2. DuckDB 1.5.4 primary-key and no-index controls are also clean.

The strengthened result resolves the first probe's attribution doubt:

```text
1.5.4 secondary ART + optimizer enabled: index scan returns 0
same persisted file + optimizer disabled: sequential scan returns 1
full scan: all rows and values remain present
```

The defect is therefore specific to the persisted secondary ART path in this fixture, rather than general loss of table rows or a broadly wrong comparison result.

## Explain like I'm five

Two copies of DuckDB open one database inside one process. One copy has new rows waiting in a log. The second copy files that work.

In DuckDB 1.5.4, the books remain on the shelf, but the saved secondary index says the books are missing. A normal lookup trusts the bad index and returns zero. Telling DuckDB to ignore the index finds the rows again.

DuckDB 1.3.2 files the same work correctly. A primary-key index and a table with no index also remain correct on 1.5.4.

## Why care

This is persisted silent data correctness, not a loud crash. A later fresh process can return false negatives for real rows while broad counts and ordered table reads look healthy.

A correction can affect checkpointing, WAL replay, secondary-index serialization, same-process embedding, database locking, and on-disk compatibility. The exact failing owner is now narrow enough for source work, but the blast radius still requires strong independent review.

## Source and authority

- Project: DuckDB
- Controlled fork: `teamleaderleo/duckdb`
- Evidence PR: `teamleaderleo/duckdb#10`
- Initial probe head: `362ac467dbb8d10e8f962cee1289237cedcd3722`
- Strengthened exact head: `e4543e7d2e6aa12f6d4e75ec2266ac9030e59fc5`
- Linux Fieldwork issue: #256
- Public report: https://github.com/duckdb/duckdb/issues/23788
- External contact: unauthorized and not made

The controlled fork changes evidence scripts and workflows only. No DuckDB product source is changed by this investigation.

## Mechanism under test

The fixture loads two matching DuckDB implementations into one process:

1. the Python package opens a file, creates a table and selected index form, inserts committed rows, and leaves the writer connection open with a pending WAL;
2. a separately loaded official `libduckdb.so` opens the same path read-write and triggers checkpoint/WAL replay;
3. the probe queries through the second engine;
4. the process calls `os._exit()` so Python/C++ destructor cleanup cannot let the first writer heal the file from its own in-memory state;
5. a fresh read-only Python client opens the persisted file and repeats the queries, records values, and captures optimizer-enabled and optimizer-disabled `EXPLAIN ANALYZE` plans.

The use of `os._exit()` is deliberate evidence preservation inside a disposable hosted job.

## Strengthened hosted matrix

Workflow run: `30596939235`  
Exact head: `e4543e7d2e6aa12f6d4e75ec2266ac9030e59fc5`  
Conclusion: success, five of five jobs  
Environment: Ubuntu 24.04.4, Python 3.12.13, matching official Python wheels and C libraries

| Case | Optimizer enabled | Optimizer disabled | Full rows | Plan/result interpretation |
|---|---:|---:|---:|---|
| 1.3.2, secondary ART, 2 rows | 1 | 1 | 2 | clean release control; index scan finds row |
| 1.5.4, secondary ART, 2 rows | 0 | 1 | 2 | bad index scan; sequential scan finds row |
| 1.5.4, secondary ART, 10,000 rows | 0 | 1 | 10,000 | bad index scan persists at higher cardinality |
| 1.5.4, primary key, 2 rows | 1 | 1 | 2 | clean neighboring ART control |
| 1.5.4, no index, 2 rows | 1 | 1 | 2 | clean table/WAL control |

### 1.5.4 secondary ART, two rows

The checkpointing process recorded:

```json
{
  "filtered_count": 0,
  "full_count": 2,
  "index_kind": "secondary",
  "row_count": 2,
  "wal_present_before_checkpoint": true,
  "wrong_result": true
}
```

The fresh read-only client then observed:

- physical ordered values: `[1, 2]`;
- optimizer-enabled `a = 1`: `0`;
- optimizer-enabled `a = 2`: `0`;
- plan: `Type: Index Scan`, `0 rows`;
- optimizer-disabled `a = 1`: `1`;
- plan: `Type: Sequential Scan`, `1 row`.

This is the key attribution result: the rows survive and the sequential scan reads them correctly; the persisted secondary index supplies false negatives.

### 1.5.4 secondary ART, 10,000 rows

The higher-cardinality control observed:

- full count: `10,000`;
- first values: `1` through `10`;
- optimizer-enabled `a = 1`: `0` through an index scan;
- optimizer-enabled `a = 10000`: `0`;
- optimizer-disabled `a = 1`: `1` through a sequential scan.

The defect is not a two-row plan artifact.

### 1.3.2 release control

The same independent-engine checkpoint fixture observed:

- full count: `2`;
- optimizer-enabled `a = 1`: `1`;
- plan: index scan returning one row;
- optimizer-disabled `a = 1`: `1`;
- ordered values: `[1, 2]`.

This retains a clean historical control with the same operation shape.

### 1.5.4 neighboring controls

The primary-key and no-index jobs both retained all rows and returned `1` for `a = 1`. The matrix therefore distinguishes the secondary `CREATE INDEX` path from a primary-key ART and from table/WAL persistence without an index.

## Retained artifacts

All artifacts belong to workflow run `30596939235` and exact head `e4543e7d2e6aa12f6d4e75ec2266ac9030e59fc5`.

| Artifact | ID | ZIP SHA-256 |
|---|---:|---|
| `secondary-art-v1.3.2-secondary-2` | `8781398037` | `77c353722f62619fc8dd81425aa89abdd6528a78efb2c4c0b740a838c8f136c7` |
| `secondary-art-v1.5.4-secondary-2` | `8781401229` | `bcc04b01cd1e13bcddaf27c27b0846a579f62c8dc187033f55d3c267d2f09890` |
| `secondary-art-v1.5.4-secondary-10000` | `8781402082` | `827df72d4ba7b0af50e27fe257ad47c1731c29ff928c70da912df32681b876a3` |
| `secondary-art-v1.5.4-primary-2` | `8781400777` | `2a0cd8afa85c42c47b5c74a620af532a0770f6858cb3b2c9b09ebf7fc18d6f35` |
| `secondary-art-v1.5.4-none-2` | `8781404609` | `582a01001a147fa06cc3a57b21237dc4ceb893479420c343919708e481d848bc` |

Each archive includes the generated database, probe JSON/status, and fresh-client inspection record. The 1.5.4 secondary artifacts preserve the wrong index state before writer cleanup can heal it.

## Why the first interpretation changed

The initial two-row `EXPLAIN` snapshot appeared to say `Sequential Scan`, so the first retained record correctly narrowed its claim and withheld ART attribution.

The strengthened fixture added `EXPLAIN ANALYZE`, optimizer-disabled comparison, actual row values, index-kind controls, and higher cardinality. Those discriminators now show:

```text
secondary ART present + normal planning -> wrong index scan
same file + optimizer disabled -> correct sequential scan
primary key or no index -> correct result
```

This is a useful example of why a surprising plan/result mismatch should cause probe repair rather than prose confidence.

## Candidate ownership directions

The next source pass should distinguish these repair families:

1. **Secondary ART checkpoint/serialization correction** — identify the 1.4-era change that writes or restores the wrong index state.
2. **Checkpoint ownership coordination** — prevent a second independent engine from checkpointing state it cannot serialize consistently.
3. **Safe rejection of unsupported same-process duplicate opens** — fail before mutation when the configuration is outside the supported contract.
4. **Validation/rebuild on open** — detect a persisted index/table mismatch and rebuild or reject it.

The matrix now favors direction 1 as the first source investigation because table/WAL state is intact and neighboring index forms remain correct. Directions 2 and 3 still matter because the trigger uses two independent engine images in one process.

## Rejected shortcuts

- Disabling optimizer/index scans hides the corrupted persisted index and removes expected query behavior.
- Rebuilding every secondary index on every open can impose broad startup cost and mask the writer defect.
- Calling the configuration unsupported is insufficient while current code permits the second open and writes a bad persistent result; safe rejection must occur before checkpoint mutation.
- Testing only `count(*)` is insufficient; the strengthened fixture retains actual values and both plan families.
- Letting the first writer close normally can heal the file and erase the evidence.

## Remaining edge ledger

Proved:

- 1.3.2 clean versus 1.5.4 affected release boundary;
- secondary index trigger;
- primary-key and no-index clean controls;
- two-row and 10,000-row affected cases;
- rows remain present and sequential scans remain correct;
- persisted wrong index result in a fresh process;
- exact generated artifacts retained.

Still open:

- first bad commit and exact source owner;
- current-main behavior built from one exact source identity for both engine images;
- integer versus text and multi-column indexes;
- unique indexes and multiple secondary indexes;
- deletes, updates, transactions, and checkpoint timing variants;
- cross-platform/architecture behavior;
- separate process versus two independent libraries in one process;
- supported-policy status of duplicate embedded engines;
- crash recovery and WAL replay after abnormal exit;
- safe repair and database-format compatibility.

## Human decision

Treat the release result as a confirmed high-consequence secondary ART checkpoint defect in the characterized same-process embedding shape. Approve a source-level investigation that first maps the 1.4-era regression and current-main status before selecting a correction.

Any production candidate requires independent exact-diff review and retained before/after database artifacts.

## Current disposition

**CONFIRMED — BEGIN SOURCE OWNERSHIP AND CURRENT-MAIN WORK.**

The evidence carrier is complete for the release-boundary claim. No external contact is authorized or made.
