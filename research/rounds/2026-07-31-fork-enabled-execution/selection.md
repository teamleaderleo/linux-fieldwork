# Fork-enabled execution round — selection record

Date: 2026-07-31  
Programme: [`ecosystem-contributions`](../../../programmes/ecosystem-contributions/STATUS.md)  
Authority: internal fork and Linux Fieldwork work only; no external contact authorized

## TL;DR

Writable forks changed the next step from issue triage to controlled execution. This round:

1. opened a libarchive fork probe for seek-dependent 7-Zip selection on non-seekable transports;
2. implemented a bounded DuckDB candidate preventing `decode(blob, 'replace')` from mutating shared input storage;
3. separated a Deno TCP connection-racing question from an accepted-connection HTTP response stall;
4. opened a DuckDB release-boundary probe for persisted secondary-index wrong results;
5. retained Deno stdin cancellation as the strongest next unstarted lifecycle candidate.

The most important judgment result is negative: the public Deno `fetch()` fixture completes the IPv6 TCP handshake, so its expected IPv4 retry is not Happy Eyeballs behavior. The most direct candidate is DuckDB input immutability. The highest-consequence new lane is DuckDB checkpoint/index persistence.

## Explain like I'm five

A public bug report can be a map, but a fork is a laboratory. We can now run the exact old behavior, make one small change, test the changed behavior, and keep the evidence without contacting the original project.

This round also found that one attractive report asked the wrong question. A door that will not open is different from an open door where nobody answers. Connection racing handles the first problem. Automatically repeating an HTTP request after the second can duplicate real actions.

## Why care

The fork set provides a renewable pipeline across foundational libraries, databases, runtimes, packaging tools, and system projects. The quality bar remains bounded ownership, a distinguishing negative control, exact source identity, compatibility review, cleanup, and one explicit next decision.

# Executed work

## 1. libarchive non-seekable 7-Zip selection

Linux Fieldwork: #230  
Fork carrier: `teamleaderleo/libarchive` PR #1  
Fork base: `280402b7f1e3a5ce89c1ba7a7d68b803771df82b`  
Exact probe head: `ceb74e8db3aa90cd8ed7d269c911ed2d4f6d7762`

Current 7-Zip format bidding recognizes the signature and returns a strong bid without first rejecting a non-seekable transport. Later 7-Zip reading has explicit seek paths. The fork probe builds exact-head `bsdtar` and compares:

- regular 7-Zip file;
- direct 7-Zip pipe;
- gzip-wrapped 7-Zip file;
- gzip-wrapped 7-Zip pipe;
- forced-raw wrapped pipe.

It retains status, stdout, stderr, and artifacts while requiring only the regular seekable control to pass. The result must decide among bidder abstention, earlier capability diagnostics, seek emulation, and intentional late failure.

State at record creation: focused workflow run `30592942923` queued; lint passed. No product change made.

## 2. DuckDB read-only decode input mutation

Linux Fieldwork: #254  
Public report: https://github.com/duckdb/duckdb/issues/24281  
Fork carrier: `teamleaderleo/duckdb` PR #9  
Fork base: `2c9e51aa33dd07e928edae66304430aeb038edd7`  
Exact candidate head: `ff2c8324f4eb9084d7eda1cdc4e8bad551c95331`

Current source obtains a writable pointer from the input `string_t`. For invalid input with `replace`, it runs `Utf8Proc::MakeValid()` on that pointer and returns the same input object. Shared dictionary storage can therefore be changed by a read-only scalar query.

The candidate:

- analyzes through a const input pointer;
- preserves the zero-copy valid-input path;
- allocates equal-sized result-owned storage only for invalid replacement;
- copies and repairs the result buffer;
- preserves `strict` and `ignore` semantics.

The native regression forces dictionary compression, stores repeated non-inline invalid BLOBs, checkpoints, runs replacement, and proves the original `hex(b)` still ends in `C0`.

Main compatibility questions are result-vector lifetime, heap references, inlined versus non-inlined strings, constant/dictionary execution, and allocation cost. State at record creation: focused workflow `30593356836` queued.

## 3. Deno fetch family-racing classification

Linux Fieldwork: #253  
Public report: https://github.com/denoland/deno/issues/36279  
Fork carrier: `teamleaderleo/deno` PR #2  
Fork base: `3ee245fe9da563cacb0b6458c4280b5a2758782c`  
Exact probe head: `e209a4846a64dad59747ac71fe84eaef21714279`

The public fixture starts an IPv6 listener that accepts TCP and then sends no HTTP bytes. RFC 8305 ends family racing when one connection succeeds, generally at TCP handshake completion. Retrying through IPv4 after that point is a separate speculative-request policy and can duplicate non-idempotent requests.

Current Deno fetch source resolves and permission-checks addresses, then constructs hyper-util `HttpConnector`. Hyper-util documents a default 300 ms Happy Eyeballs timer for connection establishment.

The fork probe therefore separates:

- IPv6 SYN packets dropped while IPv4 responds — connection-racing case;
- IPv6 TCP accepted while HTTP remains silent — response-stall control.

State at record creation: focused workflow `30593513414` queued. The original internal issue was corrected to `REPAIR / RESCOPE`; no Deno defect is claimed from the accepted-socket fixture.

## 4. DuckDB persisted secondary ART wrong results

Linux Fieldwork: #256  
Public report: https://github.com/duckdb/duckdb/issues/23788  
Fork carrier: `teamleaderleo/duckdb` PR #10  
Fork probe head: `362ac467dbb8d10e8f962cee1289237cedcd3722`

The report isolates a same-process, independently loaded engine configuration where a second engine checkpoints a pending WAL. In affected releases, table data remains present while a secondary index later returns zero rows for an existing value. The bad index persists into fresh clients.

The release-boundary matrix runs matching Python and shared-library engines:

- 1.3.2 expected clean: indexed count `1`;
- 1.5.4 expected affected: indexed count `0`, full count `2`.

The probe bypasses original-writer cleanup to prevent its correct in-memory state from healing the file, then inspects the retained database from a fresh client. Current-head behavior remains a separate required step.

This work requires stronger review because candidate directions can affect WAL recovery, persistent format, file locking, embedded multi-engine use, and startup/index validation. State at record creation: focused workflow `30593662278` queued.

# Source-review result: why the Deno report changed category

Happy Eyeballs races unresolved or pending connection attempts. Once TCP succeeds, the selected application protocol can still stall. Automatically retrying an HTTP operation after successful connection establishment creates new questions:

- Was any request body sent?
- Is the method idempotent?
- Can both servers process the same request?
- Which response wins?
- How are losing sockets and pooled connections cleaned?
- Does a proxy own the connection instead of the origin client?

The correct fork test uses a dropped SYN for connection racing and an accepted silent server as a no-replay control. This is a retained example of why an executable reproduction can still encode an incorrect expected contract.

# Strong next candidate

## Deno stdin cancellation leaves a read operation alive

Public report: https://github.com/denoland/deno/issues/30652  
Environment: current Linux CI  
Current public state: open bug, runtime and streams labels, no assignee, comments, or visible fix carrier

The minimal report starts a stdin read, cancels the reader, observes both cancellation and `read()` resolve, finishes JavaScript, and then hangs until another input byte arrives. `--strace-ops` reportedly shows the underlying `op_read` remains pending.

Why it is attractive:

- tiny TTY and pipe controls;
- clear lifecycle owner;
- cancellation, operation completion, process exit, and rerun are directly observable;
- likely bounded to stdin resource/readable-stream cancellation wiring;
- no privileged environment.

Required first probe:

1. run affected release and current fork head under pipe and pseudo-terminal input;
2. retain operation trace, process status, descriptors, and timing;
3. distinguish reader cancellation, resource close, lock release, and pending native op cancellation;
4. test cancel before read, during read, after data, EOF, repeated cancel, and immediate rerun;
5. find whether the resource owner can cancel only its own pending read without closing inherited stdin globally.

Main downside risk: closing or globally cancelling stdin may break another reader or caller-owned descriptor. The repair needs operation ownership rather than a blunt process exit.

# Additional retained candidates

- DuckDB Arrow union type-ID mapping: current report says parsed non-identity mappings are ignored, producing either an out-of-range error or silently wrong union member assignment. It has a sharp interoperability fixture but needs an overlap refresh before promotion.
- uv BusyBox `realpath --` shebang noise: a small Alpine portability issue with a clean container matrix, but lower consequence than current database and lifecycle work.
- DuckDB large `string_agg` allocation overflow: potentially serious but requires multi-gigabyte memory and current overlap/security handling before local execution.

# Stops and boundaries

- DuckDB Iceberg duplicated-column prefetch accounting already names public fix PR #24187; retain it as planning/accounting precedent rather than duplicate implementation.
- Deno accepted-TCP/no-response is not, by itself, RFC 8305 noncompliance.
- Fork pull requests are internal laboratories. They are not upstream submissions, approvals, or authority to contact maintainers.
- Queued Actions results are not claimed as passed. Later exact-run receipts supersede this snapshot.

# Execution order

1. classify and repair any harness failure in libarchive PR #1;
2. validate DuckDB candidate PR #9, then expand vector-shape controls only where evidence demands;
3. validate DuckDB release-boundary PR #10 and add current-head execution;
4. validate Deno classification PR #2 and retire or rescope #253 accordingly;
5. open the stdin-cancellation investigation and probe if no active fix appears;
6. continue fork scanning with the same overlap and consequence filters.
