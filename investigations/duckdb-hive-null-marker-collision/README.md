# DuckDB Hive null-marker collision

## TL;DR

DuckDB partitioned `COPY` currently maps a literal VARCHAR value `__HIVE_DEFAULT_PARTITION__` and SQL `NULL` to the same Hive directory name. The in-memory partition keys remain distinct; the collision happens when `PartitionFileRequestBuilder::BuildDirectory()` serializes both values onto disk. The narrow candidate is to percent-encode one byte of the reserved sentinel only for a non-null partition value, leaving SQL `NULL` and ordinary partition names unchanged.

Next action: implement the writer-side escape in the owned DuckDB fork and run the existing Parquet Hive-null suite plus a regression proving both rows survive and occupy distinct directories.

## Explain like I'm five

DuckDB puts partition values into folder names. A missing value becomes the special folder name `p=__HIVE_DEFAULT_PARTITION__`. Today, a real string with exactly that text gets the same folder name. Example: input rows `('__HIVE_DEFAULT_PARTITION__', 1)` and `(NULL, 2)` -> partitioned `COPY` -> one directory -> reading the files returns only row 2 in the upstream reproduction.

## Why care

Two distinct SQL values can address the same output directory during partitioned `COPY`, so an overwrite-capable write can silently lose data. The fix can stay inside partition-value serialization and preserve the existing Hive null marker for actual SQL `NULL`.

## Current state

- State: `SCOPING`
- Exact working head: `teamleaderleo/linux-fieldwork@7dab6a8ff346117f95a5c03dd1af7bcc4f104510` plus this investigation branch
- Latest authoritative gate or artifact: source-read against `duckdb/duckdb@22226bba7f8b3fa32b9b1c0777c2caf048cb4cef`; upstream issue carries a minimal reproduction and `reproduced` label
- First incomplete step: materialize the candidate in `teamleaderleo/duckdb` and execute the regression
- Cleanup state: source-read only; no runtime state created
- Next safe action: implement the value-specific escape and run focused tests in the owned fork
- External-contact state: no upstream mutation authorized or performed by this worker

## Intent and precedent

Primary sources:

- https://github.com/duckdb/duckdb/issues/24308
- https://github.com/duckdb/duckdb/blob/22226bba7f8b3fa32b9b1c0777c2caf048cb4cef/src/execution/operator/persistent/physical_copy_to_file.cpp
- https://github.com/duckdb/duckdb/blob/22226bba7f8b3fa32b9b1c0777c2caf048cb4cef/src/common/hive_partitioning.cpp
- https://github.com/duckdb/duckdb/blob/22226bba7f8b3fa32b9b1c0777c2caf048cb4cef/test/sql/copy/parquet/parquet_hive_null.test

Observed source contracts:

1. `PartitionWriteManager` and the surrounding partitioned-copy machinery key active writes by `vector<Value>`, so SQL `NULL` and the literal sentinel remain distinct before path creation.
2. `PartitionFileRequestBuilder::BuildDirectory()` writes actual SQL `NULL` as raw `__HIVE_DEFAULT_PARTITION__`.
3. The same function writes a non-null value as `HivePartitioning::Escape(partition_value.ToString())`. URL encoding leaves the sentinel's underscores and ASCII letters unchanged, so the literal sentinel receives the same directory spelling.
4. `HivePartitioning::GetValue()` treats raw `__HIVE_DEFAULT_PARTITION__` as SQL NULL before type-specific conversion. A percent-encoded first underscore avoids the reserved raw spelling, and the later URL decode reconstructs the literal string.
5. The existing `parquet_hive_null.test` protects the SQL-NULL marker and literal VARCHAR `NULL` behavior, so a broad change to all escaping would create unnecessary compatibility risk.

Interpretation: Hive's null marker is a reserved serialization token. DuckDB currently escapes ordinary user strings without escaping that reserved token out of band.

## Question

Can DuckDB preserve both SQL `NULL` and a literal `__HIVE_DEFAULT_PARTITION__` partition value by escaping the reserved spelling only on the non-null writer path, while keeping existing null-directory naming and literal `NULL` behavior intact?

## Source

- Project: DuckDB
- Requested revision or package version: current canonical `main` at investigation start
- Resolved commit: `22226bba7f8b3fa32b9b1c0777c2caf048cb4cef`
- Candidate source commit: pending
- Local source path: owned fork `teamleaderleo/duckdb`
- Import metadata: GitHub source-read; no local import

## Environment

- Distribution and release: pending candidate execution
- Kernel and architecture: pending candidate execution
- Shell: pending candidate execution
- Privileges: ordinary test execution expected
- Container, virtual machine, or host context: pending candidate execution
- Relevant tool versions: pending candidate execution

## Baseline behavior

Upstream issue reproduction:

```sql
CREATE TABLE t AS
SELECT * FROM (VALUES ('__HIVE_DEFAULT_PARTITION__', 1), (NULL, 2)) v(p, id);

COPY t TO '/private/tmp/duckdb_partition_hive_default_collision_min'
(FORMAT PARQUET, PARTITION_BY (p), OVERWRITE);

SELECT count(*) AS rows_read, min(id), max(id)
FROM read_parquet('/private/tmp/duckdb_partition_hive_default_collision_min/**/*.parquet',
                  hive_partitioning=true);
```

Reported result: one row survives, with `id = 2`.

Source-level path discriminator:

```text
SQL NULL                         -> p=__HIVE_DEFAULT_PARTITION__
literal __HIVE_DEFAULT_PARTITION__ -> p=__HIVE_DEFAULT_PARTITION__
```

The collision occurs after partition identity has already been established correctly.

## Hypothesis or candidate

Keep `HivePartitioning::Escape()` generic because it is also used for partition keys. Add a value-specific writer helper near `PartitionFileRequestBuilder::BuildDirectory()`:

```cpp
static string EscapeHivePartitionValue(const Value &value) {
    auto escaped = HivePartitioning::Escape(value.ToString());
    if (escaped == "__HIVE_DEFAULT_PARTITION__")
        escaped.replace(0, 1, "%5F");
    return escaped;
}
```

Then use that helper only in the `partition_value.IsNull() == false` branch.

Expected serialization:

```text
SQL NULL                         -> p=__HIVE_DEFAULT_PARTITION__
literal __HIVE_DEFAULT_PARTITION__ -> p=%5F_HIVE_DEFAULT_PARTITION__
```

Reader behavior for the literal path becomes: raw value is outside the reserved-token check -> URL decode -> exact literal `__HIVE_DEFAULT_PARTITION__`.

The candidate deliberately preserves:

- raw `__HIVE_DEFAULT_PARTITION__` for SQL `NULL`;
- existing ordinary URL encoding;
- literal VARCHAR `NULL` directory spelling and round-trip behavior;
- partition-key escaping;
- in-memory partition identity and file-rotation behavior.

## Reproduction

Focused candidate test should extend `test/sql/copy/parquet/parquet_hive_null.test` with:

```sql
CREATE TABLE hive_default_collision AS
SELECT * FROM (VALUES ('__HIVE_DEFAULT_PARTITION__', 1), (NULL, 2)) v(p, id);

COPY hive_default_collision TO '{TEST_DIR}/hive-default-collision'
(FORMAT PARQUET, PARTITION_BY (p), OVERWRITE);

SELECT (p IS NULL)::INTEGER, COALESCE((p='__HIVE_DEFAULT_PARTITION__')::INTEGER, -1), id
FROM parquet_scan('{TEST_DIR}/hive-default-collision/**/*.parquet', hive_partitioning=1)
ORDER BY id;

SELECT count(*)
FROM glob('{TEST_DIR}/hive-default-collision/p=__HIVE_DEFAULT_PARTITION__/*.parquet');

SELECT count(*)
FROM glob('{TEST_DIR}/hive-default-collision/p=%5F_HIVE_DEFAULT_PARTITION__/*.parquet');
```

Expected rows:

```text
0  1  1
1 -1  2
```

Expected path counts: `1`, `1`.

Also rerun the complete existing `parquet_hive_null.test` to protect the adjacent `NULL` and SQL-null contracts.

## Results

Source-read result only at this checkpoint. The candidate and regression have not yet executed.

Open-PR overlap refresh at this checkpoint found no open canonical DuckDB PR matching issue `24308` or `HIVE_DEFAULT_PARTITION`.

## Interpretation

The smallest sufficient owner is writer-side Hive partition-value serialization. Reworking partition identity, overwrite policy, or general URL escaping would operate outside the demonstrated failure boundary.

A rejection-only fix could prevent data loss, but a reversible percent escape preserves the literal value and keeps partitioned COPY useful for arbitrary strings. That is the stronger candidate.

## Evidence boundary

- The upstream reproduction was read, not independently executed by this worker yet.
- The percent-escape candidate is source-derived and awaits compile/test execution.
- No claim is made yet about Spark/Hive interoperability for the escaped literal sentinel. The resulting path is ordinary percent-encoded Hive-style text and DuckDB's reader reverses it, but external-engine behavior needs a separate compatibility probe if required for upstream review.
- No broad change to legacy raw `NULL` handling is proposed in this lane.

## Next step

1. Create a current-head work branch in `teamleaderleo/duckdb`.
2. Change only `physical_copy_to_file.cpp` plus the existing Hive-null regression file.
3. Prove baseline failure and candidate success on the two-row collision.
4. Run the full `parquet_hive_null.test` and diff the created directory names.
5. Review external-engine compatibility as a separate discriminator if DuckDB maintainers treat Hive path interoperability as part of this writer contract.
6. Rebuild/squash a clean source candidate before any human upstream submission.

## Authority

Canonical `duckdb/duckdb` remains read-only to this worker. No upstream issue comment, pull request, review, reaction, branch, or other mutation has been made.