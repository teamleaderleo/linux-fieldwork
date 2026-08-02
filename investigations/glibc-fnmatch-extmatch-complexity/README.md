# glibc `fnmatch` extended-match rejection complexity

## TL;DR

Debian glibc 2.41 takes rapidly increasing CPU time to reject `a^n c` against the nine-byte GNU extended pattern `*(a|aa)b`. The measured family grows about 1.62× per added `a`: 34 characters take roughly 1.8 seconds, 36 take 4.8 seconds, and 38 exceed a seven-second timeout. Matching input, prefix-disjoint alternatives, unambiguous extended matching, and the same punctuation without `FNM_EXTMATCH` remain in the microsecond range.

A reduced state model sharpens the mechanism. At `n=34`, naive one-or-two-byte decomposition explores 24,157,816 recursive paths while only 35 suffix positions exist. Measured glibc time is nearly proportional to the reduced model's path count (`R² = 0.99998883`).

The next work is a current canonical `release/2.43/master` checkout or official tarball build, complete matcher-state design analysis, and one downstream authority map. No upstream contact is authorized.

## Explain like I'm five

The matcher can consume either one `a` or two `a` characters each time. When the final character is wrong, it keeps retrying almost every possible grouping before admitting failure.

```text
pattern promises: groups of `a` or `aa`, then `b`
input supplies:   aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaac
result:           no match, after seconds of retries
```

## Why care

`fnmatch` is a foundational libc API, and `FNM_EXTMATCH` has production callers. A compact ambiguous pattern can turn a short rejected string into seconds of CPU work. Practical severity depends on who controls the pattern and candidate string, matching frequency, and caller resource limits.

## Current state

- State: `EXECUTING`
- Branch: `investigation/glibc-fnmatch-extmatch-complexity`
- Base: `main@6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Exact predecessor before this refresh: `4868f4905a2b3cc9c56efe5cc5f9765553b38d37`
- Latest authoritative runtime artifact: [`results/fnmatch-matrix.csv`](results/fnmatch-matrix.csv), SHA-256 `fa5aa5ab97076fb32334f2dc16a0ad91fd758d69a6f4345f158e3d6227ebc9bc`
- Mechanism artifact: [`results/reduced-state-model.csv`](results/reduced-state-model.csv)
- Locale artifact: [`results/locale-matrix.csv`](results/locale-matrix.csv)
- First incomplete step: materialize official glibc 2.43 source and run the same probe against a built `release/2.43/master` or 2.43 release tree
- Cleanup state: temporary binaries and timing state removed; no process remains running
- Next safe action: enumerate the full matcher state needed by any semantic-preserving deduplication design
- External-contact state: unauthorized; none made

## Intent and precedent

GNU documents `FNM_EXTMATCH` as ksh-style extended matching. The glibc test data contains extensive semantic examples, including nested and overlapping patterns, so support for this grammar is intentional.

The investigated question is algorithmic cost, not whether extended matching should exist. Any mitigation must preserve grammar, locale behavior, pathname and period boundaries, narrow and wide execution, allocation failure behavior, and established results.

## Question

Does glibc's `FNM_EXTMATCH` implementation perform repeated equivalent work on ambiguous rejecting patterns, producing combinatorial or exponential time growth under a small input family?

## Source

- Project: GNU C Library
- Executed distribution build: Debian glibc `2.41-12+deb13u2`
- Exact upstream release read: `glibc-2.41@74f59e9271cbb4071671e5a474e7d4f1622b186f`
- 2.41 `posix/fnmatch_loop.c` blob: `9ec5e0edc656a774b3d1ab43c86755fe0c236672`
- 2.42 `posix/fnmatch_loop.c` blob: `83f8861653673058e0ba80368d7b54629661aee6`
- 2.42 source retains the same `*()`/`+()` recursive split-and-retry branch
- Official current stable release: glibc 2.43, released 2026-01-23
- Official stable branch: `release/2.43/master`
- Release-diff inference: the 2.42→2.43 file inventory does not list `posix/fnmatch_loop.c` as changed, supporting the same 2.42 mechanism in 2.43; direct 2.43 source identity remains pending
- Relevant test driver blob: `06343cbae5b34b58793deacc2c293e06b644df86`
- Relevant test-data blob: `796683afedf9d8554c3d81a246f88a865fddbb9e`
- Read-only GitHub mirror master blob: `713caff58f3ff5845bac3583ec9ef8bf3f3fa737`, supporting only because the mirror is archived
- Target map: [`targets/glibc/map.md`](../../targets/glibc/map.md)

## Environment

- Kernel and architecture: Linux `6.12.13`, x86-64
- CPU: AMD EPYC 9V74
- Compiler: GCC `14.2.0`
- Shell: Bash `5.2.37`
- Privileges: ordinary disposable-container user
- Base benchmark locale: `C`; the probe does not call `setlocale`, so standard process startup retains the C locale
- Separate locale-aware matrix: explicit `LC_ALL=C` and `LC_ALL=C.utf8` after `setlocale(LC_ALL, "")`
- Process timeout: GNU `timeout`, seven or twelve seconds depending on the probe
- Runtime libc SHA-256: `adeedbc69ac402b762a3bd94759441e0546c33972cb2c0f5bc6869a2d32efed6`

## Baseline behavior

```sh
./bench_fnmatch '*(a|aa)b' 34 c 32 1
```

```text
*(a|aa)b,34,c,32,1,1,1.795662035,1.795662035
```

The result is `FNM_NOMATCH`. The same input ending in `b` matches in approximately 25 microseconds.

## Hypothesis and mechanism

The `*()` and `+()` branch:

1. parses alternatives;
2. tries every candidate split;
3. tests an alternative on the prefix;
4. tests the continuation;
5. after continuation failure, recursively restarts the whole extended pattern at the suffix.

Overlapping alternatives `a` and `aa` reach the same suffix positions through many decompositions. The reduced model evaluates 24,157,816 naive paths at `n=34`, compared with 35 unique suffix positions. See [`STATE_ANALYSIS.md`](STATE_ANALYSIS.md).

A semantic-preserving implementation may use state deduplication or a compiled automaton, but a cache keyed only by string position is not sufficient for full glibc semantics.

## Reproduction

The GitHub contents API does not retain executable mode for these scripts, so run explicitly through the shell:

```sh
sh ./run-matrix.sh
python3 ./model_states.py
```

Boundary examples:

```sh
timeout 7s ./bench_fnmatch '*(a|aa)b' 36 c 32 1
timeout 7s ./bench_fnmatch '*(a|aa)b' 38 c 32 1
timeout 7s ./bench_fnmatch '+(a|aa)b' 32 c 32 1
```

## Results

- Full timing and source receipt: [`RESULTS.md`](RESULTS.md)
- Repeated-state analysis and locale matrix: [`STATE_ANALYSIS.md`](STATE_ANALYSIS.md)
- Primary CSV: [`results/fnmatch-matrix.csv`](results/fnmatch-matrix.csv)
- State counts: [`results/reduced-state-model.csv`](results/reduced-state-model.csv)
- Locale timings: [`results/locale-matrix.csv`](results/locale-matrix.csv)

Key fits:

```text
measured growth per added character: 1.62103795
log(time) against input length R²: 0.99998878
log(time) against reduced-model path count R²: 0.99998883
```

## Interpretation

The evidence demonstrates a deterministic algorithmic-complexity boundary in Debian glibc 2.41. The behavior requires overlapping extended alternatives and later rejection; it is not ordinary linear wildcard scanning.

The reduced model and source explain the measured family as repeated equivalent suffix work. They do not prove a formal worst-case bound for every glibc pattern or define a safe complete implementation change.

`C.utf8` roughly doubles the constant cost for this ASCII family while retaining the rapid growth shape. Locale affects cost but does not eliminate the mechanism.

## Evidence boundary

Not yet established:

- execution against a built current glibc 2.43 stable tree or development master;
- a second architecture or non-Debian glibc build;
- full glibc project-native tests;
- allocation and stack-depth counts;
- full `FNM_PATHNAME`, `FNM_PERIOD`, wide-character, and negative-extglob complexity matrices;
- a semantic-preserving candidate patch;
- concrete remote or privilege-boundary reachability in a downstream consumer.

A PipeWire source sample confirms production use of `FNM_EXTMATCH` for loop selection. It does not establish attacker-controlled patterns or a PipeWire vulnerability.

## Next step

1. Build and execute the probe against official glibc 2.43 source.
2. Enumerate full matcher state: subpattern identity, continuation, string position/end, flags, period state, narrow/wide mode, and `ends` continuation state.
3. Map one downstream caller's pattern and candidate authority.
4. Decide whether the result calls for a glibc performance regression/design report, consumer-side input bound, or retained warning.

## Authority

No upstream issue, mailing-list message, patch submission, comment, review, email, or other external interaction is authorized or created. All work remains local or inside Linux Fieldwork.
