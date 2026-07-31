# Fork-enabled execution — live results supplement

Updated: 2026-07-31  
Authority: internal fork and Linux Fieldwork work only

This file supersedes head and run-state fields in the dated `selection.md` when they differ.

## libarchive transport-selection probe

- Linux Fieldwork issue: #230
- fork PR: `teamleaderleo/libarchive#1`
- exact head: `ceb74e8db3aa90cd8ed7d269c911ed2d4f6d7762`
- focused run: `30592942923`
- latest observed state: queued
- completed adjacent gate: fork lint success
- claim boundary: no transport-matrix result claimed yet

## DuckDB decode input-immutability candidate

- Linux Fieldwork issue: #254
- fork PR: `teamleaderleo/duckdb#9`
- current exact head: `b3b149029c3471e59ac0f4959632b24aab5cd3c4`
- focused run: `30593988082`
- latest observed state: queued
- candidate change: const input analysis plus result-owned copy only for invalid `replace`
- self-review repair: moved the regression into `decode_replace_immutability.test`; persistent database, checkpoint, restart, explicit Dictionary storage guard, unchanged stored-byte assertion, valid non-inline control
- claim boundary: source and complete diff reviewed; execution still pending

## Deno connection-racing classification

- Linux Fieldwork issue: #253
- fork PR: `teamleaderleo/deno#2`
- exact head: `e209a4846a64dad59747ac71fe84eaef21714279`
- focused run: `30593513414`
- latest observed state: queued
- source-review result: accepted IPv6 TCP with silent HTTP is a response-stall case, not an RFC 8305 connection-establishment failure
- retained controls: IPv6 SYN drop with healthy IPv4; accepted IPv6 TCP with no HTTP bytes
- disposition: `REPAIR / RESCOPE`; no confirmed product defect from the public fixture

## DuckDB secondary ART checkpoint probe

- Linux Fieldwork issue: #256
- fork PR: `teamleaderleo/duckdb#10`
- exact head: `362ac467dbb8d10e8f962cee1289237cedcd3722`
- focused run: `30593662278`
- latest observed state: queued
- matrix: matching 1.3.2 engines expected clean; matching 1.5.4 engines expected persisted index false negative
- claim boundary: public result not yet independently reproduced by this repository

## Deno stdin cancellation

- Linux Fieldwork issue: #258
- public issue: Deno 30652
- state: ready for fork probe
- overlap result: no assignee, comments, or visible fix carrier at the recorded check
- first execution: release and current-head pipe/PTY matrix with op trace, process exit timing, descriptor/resource ownership, cancellation/data race, signals, cleanup, and rerun

## Current decisions

1. Do not merge or publish any fork product change based only on queued CI.
2. Repair harness failures before interpreting product behavior.
3. Keep DuckDB PR #9 as the first product candidate for exact review.
4. Treat DuckDB #256 as higher consequence and require independent review after reproduction.
5. Treat Deno #253 as a standards-driven classification exercise unless the connect-level control fails.
6. Start Deno #258 after one final public overlap refresh.

No external contact was made or authorized.
