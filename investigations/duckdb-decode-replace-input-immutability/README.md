# DuckDB `decode(..., 'replace')` input immutability

## TL;DR

DuckDB's two-argument BLOB decoder analyzes and repairs invalid UTF-8 through a writable pointer to its input. When the input is shared dictionary storage, a read-only query can change bytes observed by later queries.

A controlled-fork candidate now analyzes through a const pointer and allocates result-owned storage only when invalid input requests replacement. The first hosted run failed before compilation because the focused workflow omitted DuckDB's selected `mold` linker. The workflow was repaired; a fresh exact-head build and native regression remain the current gate.

## Explain like I'm five

Several rows can share one stored copy of a value. The old read-only function writes question marks onto that shared value while making its answer. The candidate copies the value into the answer first and repairs the copy, leaving the stored value alone.

## Why care

A successful `SELECT` must not silently change later query results. Shared-buffer mutation can poison analytical output, caches, repeated tests, and application decisions while leaving no update record and returning success.

## Source and authority

- Project: DuckDB
- Controlled fork: `teamleaderleo/duckdb`
- Fork PR: `teamleaderleo/duckdb#9`
- Initial candidate head: `ff2c8324f4eb9084d7eda1cdc4e8bad551c95331`
- Current workflow-repair head: `6bd105b3a05d1a881d62897a90f98024957bd98d`
- Linux Fieldwork issue: #254
- Public report: https://github.com/duckdb/duckdb/issues/24281
- External contact: unauthorized and not made

## Exact source defect

`extension/core_functions/scalar/blob/encode.cpp` currently enters the binary decoder with:

```cpp
auto input_data = input.GetDataWriteable();
auto input_length = input.GetSize();
```

For invalid input and `DecodeErrorBehavior::REPLACE`, it then does:

```cpp
Utf8Proc::MakeValid(input_data, input_length);
return input;
```

The same `string_t` can refer to dictionary backing storage shared by several rows and later expressions. A writable pointer does not establish exclusive ownership.

## Candidate

The controlled-fork diff changes only the transformed replacement path:

```cpp
auto input_data = input.GetData();
...
auto target = StringVector::EmptyString(result, input_length);
auto output = target.GetDataWriteable();
memcpy(output, input_data, input_length);
Utf8Proc::MakeValid(output, input_length);
target.Finalize();
return target;
```

Properties:

- already-valid input retains the existing no-op return path;
- invalid `replace` input writes only into result-owned memory;
- output length and replacement behavior stay unchanged;
- `strict` and `ignore` branches remain structurally unchanged;
- the existing result heap reference to the input remains, which is required for no-op results and harmless for result-owned branches.

## Native regression

`test/sql/function/blob/decode_replace_immutability.test`:

1. forces dictionary compression;
2. creates three repeated non-inline BLOB values ending in invalid byte `C0`;
3. checkpoints and restarts;
4. verifies one dictionary-compressed BLOB segment exists;
5. records original hex ending in `C0`;
6. runs `decode(b, 'replace')` and expects a trailing question mark;
7. queries original BLOB hex again and requires the trailing byte to remain `C0`;
8. retains an already-valid non-inline no-op control.

The test is intentionally native sqllogictest coverage rather than a Python-only reproduction so it exercises the executor and storage vector path directly.

## First hosted run and failure owner

Focused workflow run: `30593356836`  
Job: `91040230410`  
Conclusion: failure before candidate compilation

The build configured successfully, selected `-fuse-ld=mold`, reached the first link, and failed with:

```text
collect2: fatal error: cannot find 'ld'
```

The workflow installed `ninja-build` but not `mold`. No product or regression result is claimed from that run.

Repair commit `6bd105b3a05d1a881d62897a90f98024957bd98d` installs both packages before `GEN=ninja make debug`. A fresh exact-head run is required.

## Self-review questions

Before promotion, the exact candidate should prove:

- dictionary, flat, constant, and sliced/vectorized input immutability where the executor can produce them;
- inline and non-inline invalid strings;
- valid, `strict`, `replace`, and `ignore` behavior;
- NULL and repeated-value handling;
- result lifetime after input chunks are released;
- no broad loss of dictionary-expression optimization for valid data;
- native blob tests and formatting/build gates.

The current regression proves the reported dictionary/non-inline case and one valid control. Additional vector-shape tests may be added after the first exact candidate run establishes the basic mechanism.

## Compatibility and negative ramifications

Copying every input would be safe but unnecessarily change the valid no-op path. Disabling dictionary optimization for the function could hide this instance while leaving the mutating implementation unsafe for other shared vector forms. A broad executor change could affect many scalar functions.

The focused candidate allocates only when transformation is required. The main compatibility risks are allocation cost for large invalid BLOBs, string heap references, inlining, result ownership, and exact UTF-8 replacement behavior.

## Cleanup and evidence limits

Hosted builds use disposable runners. The failed run retained no database or process state. No external service or private data is involved.

The candidate has not yet received a successful exact-head compile/test receipt. The public report and source review establish a credible defect direction; the hosted candidate result remains pending.

## Current disposition

**REPAIR COMPLETE; EXACT-HEAD GATE PENDING.** Continue from workflow head `6bd105b3a05d1a881d62897a90f98024957bd98d`, classify the first semantic result, then broaden vector-shape coverage if the candidate passes.