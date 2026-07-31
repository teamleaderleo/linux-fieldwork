# LF-02 maintainer-script argument evidence repair

State: `producer and schema repaired — fresh gates required`

## Run 25: original evidence failure

- PR #178 head: `a3f7b0d09ec03cad457f09c2c466c759fcf94f54`
- dedicated workflow: `30588652679` / 25
- lifecycle job: `91025835702`
- retained artifact: `8778845717`
- digest: `sha256:a973001e9b3bd3ae93937f7385d7cbb9bb9c242b80acbb188ff640908353668a`
- artifact files: 313

The guarded lifecycle executed and retained phase, snapshot, classifier, provenance, and host-fingerprint evidence. Summary validation then stopped with:

```text
evidence validation failed: script log token is not key=value: '2.0'
```

The generated scripts had written raw `$*` into a whitespace-delimited record:

```text
phase=preinst script_version=2.0 args=upgrade 1.0 2.0 dpkg_root=... cwd=...
```

The bare tokens were ambiguous and could not be recovered into exact argument boundaries. This was an evidence-producer failure, not a lifecycle result. Run 25 published no valid disposition.

## Selected encoding

The producer now writes the complete argument vector in one token:

```sh
args_hex=$(printf '%s\000' "$@" | od -An -tx1 | tr -d ' \n')
```

The format is:

- NUL-delimited, preserving argument boundaries including empty arguments;
- hexadecimal, preventing spaces, tabs, newlines, or Unicode bytes from becoming record delimiters;
- `-` for an empty argument vector.

The record uses `args_hex=...` instead of raw `args=...`.

## Run 26: review exposed an unrelated fixture regression

First repair head: `912ca6bfaee301ba72ec98f0fbb652b41c093764`.

- Linux Fieldwork CI `30638297844` / 984: focused tests passed; the older stacked base still failed its generic shell/help inventory.
- dedicated lifecycle `30638297780` / 26: failed before package execution.

The encoding tests passed, but complete lifecycle execution found that the same patch had accidentally changed:

```python
path.parent.mkdir(parents=True, exist_ok=True)
```

to:

```python
path.parent.mkdir(parents=True)
```

The second file written below the same `DEBIAN` directory therefore raised `FileExistsError`. This failure was introduced by the carrier and was unrelated to the argument encoding.

The branch restores `exist_ok=True` and adds a regression that writes two files below one existing parent.

## Production schema repair

Review found another evidence gap beyond the red lifecycle: the unit test could decode `args_hex`, but the production summarizer did not require that field or validate its encoding. A future producer could omit or corrupt argument evidence while still producing a summary.

The current generation therefore:

- adds `args_hex` to the required script-log fields;
- accepts `-` as the explicit empty-vector sentinel;
- otherwise requires valid hexadecimal;
- requires the decoded byte sequence to be nonempty and end in NUL;
- retains the legacy whitespace shape as a rejecting control.

The test matrix now covers:

- multiple ordinary arguments;
- an empty argument within a nonempty vector;
- spaces, tabs, newlines, and Unicode;
- an empty vector;
- missing `args_hex`;
- malformed hexadecimal;
- a vector without a trailing NUL;
- repeatable writes below an existing fixture parent;
- generated source using `$@` with NUL-delimited hexadecimal rather than raw `$*`.

## Current identity

- branch: `repair/178-script-log-tsv`;
- current reviewed head after source and schema repairs: `1b2e807faea1b8d4cd2bbe98404ccde16197cdea`;
- changed surface: fixture producer, production summarizer, focused regression, and this record;
- product source: unchanged;
- external contact: none and unauthorized.

## Decision boundary

A green unit test proves the producer/parser contract. It does not establish the package lifecycle result.

A valid lifecycle disposition requires the dedicated workflow to:

1. build all fixture packages;
2. execute the guarded upgrade/failure/recovery matrix;
3. retain complete script logs with recoverable argument vectors;
4. publish a schema-valid summary;
5. classify the resulting lifecycle, host effects, and unresolved events.

## Next transition

Run repository CI and the dedicated LF-02 lifecycle on the unchanged current head. Classify any next failure by the first failing phase; do not infer a lifecycle result from producer-only success.

Internal Linux Fieldwork work only. No external contact.
