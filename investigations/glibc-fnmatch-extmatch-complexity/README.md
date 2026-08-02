# glibc `fnmatch` extended-match rejection complexity

## TL;DR

Debian glibc 2.41 takes rapidly increasing CPU time to reject `a^n c` against the nine-byte GNU extended pattern `*(a|aa)b`. The measured family grows about 1.62× per added `a`: 34 characters take roughly 1.8 seconds, 36 take 4.8 seconds, and 38 exceed a seven-second timeout. Matching input and unambiguous extended-pattern controls remain in the microsecond range.

The next work is source-generation confirmation on canonical current glibc, call/state instrumentation, and a bounded algorithm review. No external report should be prepared until the exact current project head, prior-art search, and an acceptable semantic-preserving mitigation are clearer.

## Explain like I'm five

The matcher can consume either one `a` or two `a` characters each time. When the final character is wrong, it keeps retrying almost every possible grouping before admitting failure.

Literal example:

```text
pattern promises: groups of `a` or `aa`, then `b`
input supplies:   aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaac
result:           no match, after seconds of retries
```

## Why care

`fnmatch` is a foundational libc API, and `FNM_EXTMATCH` has production callers. A compact pattern can turn a short rejected string into seconds of CPU work. The practical consequence depends on which caller controls the pattern and candidate string, how often matching runs, and what resource limits exist.

## Current state

- State: `EXECUTING`
- Branch: `investigation/glibc-fnmatch-extmatch-complexity`
- Base: `main@6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Exact predecessor before this README: `f86267da214332b2a786f65806dade086d9a6d04`
- Latest authoritative artifact: [`results/fnmatch-matrix.csv`](results/fnmatch-matrix.csv), SHA-256 `fa5aa5ab97076fb32334f2dc16a0ad91fd758d69a6f4345f158e3d6227ebc9bc`
- First incomplete step: instrument or model distinct recursive states to separate repeated-state recomputation from unavoidable semantic branching
- Cleanup state: temporary binaries and timing state are disposable; no process remains running
- Next safe action: compare a memoized reduced model and inspect canonical current Sourceware history for equivalent work
- External-contact state: unauthorized; none made

## Intent and precedent

GNU documents `FNM_EXTMATCH` as ksh-style extended matching. The glibc 2.41 test data contains extensive semantic examples, including nested and overlapping patterns, so support for this grammar is intentional.

The investigated question is algorithmic cost, not whether extended matching should exist. Any mitigation must preserve the documented grammar, flags, locale behavior, pathname/period boundaries, and established test results.

## Question

Does glibc's `FNM_EXTMATCH` implementation perform repeated equivalent work on ambiguous rejecting patterns, producing combinatorial or exponential time growth under a small input family?

## Source

- Project: GNU C Library
- Upstream revision: `glibc-2.41`
- Resolved tag commit: `74f59e9271cbb4071671e5a474e7d4f1622b186f`
- Relevant source: `posix/fnmatch_loop.c`
- Relevant source blob: `9ec5e0edc656a774b3d1ab43c86755fe0c236672`
- Relevant test driver blob: `06343cbae5b34b58793deacc2c293e06b644df86`
- Relevant test-data blob: `796683afedf9d8554c3d81a246f88a865fddbb9e`
- Current mirror support: archived GitHub mirror master blob `713caff58f3ff5845bac3583ec9ef8bf3f3fa737` retains the same recursive branch
- Local source path: none; exact files were retrieved through the repository connector because direct Git DNS resolution failed
- Target map: [`targets/glibc/map.md`](../../targets/glibc/map.md)

## Environment

- Distribution/library: Debian glibc `2.41-12+deb13u2`
- Kernel and architecture: Linux `6.12.13`, x86-64
- CPU: AMD EPYC 9V74
- Compiler: GCC `14.2.0`
- Shell: Bash `5.2.37`
- Privileges: ordinary container user
- Container context: disposable execution container; no network-dependent step required
- Locale variables: unset during the timing matrix, so the process inherited the container default locale behavior
- Process timeout: GNU `timeout`, seven or twelve seconds depending on the probe
- Runtime libc SHA-256: `adeedbc69ac402b762a3bd94759441e0546c33972cb2c0f5bc6869a2d32efed6`

## Baseline behavior

Compile the retained probe and run:

```sh
./bench_fnmatch '*(a|aa)b' 34 c 32 1
```

Observed:

```text
*(a|aa)b,34,c,32,1,1,1.795662035,1.795662035
```

The final `1` is `FNM_NOMATCH`. The same input ending in `b` matches in approximately 25 microseconds.

## Hypothesis

The `*()` and `+()` implementation recursively revisits the same `(pattern position, string position)` suffix state through multiple decompositions of the ambiguous prefix. A semantic-preserving implementation with state deduplication or a compiled automaton should avoid recomputing those states, but locale-sensitive and negative-extglob semantics may make a naive memoization patch invalid.

### Accepted for the current investigation

- demonstrate and characterize the runtime family;
- map the exact recursive source path;
- identify real callers without claiming their exploitability;
- build reduced models or instrumentation to distinguish repeated-state work;
- review current upstream and prior art;
- prepare a regression shape and design questions.

### Deliberately deferred

- calling the behavior a vulnerability;
- claiming a remotely reachable default service;
- publishing an upstream issue or patch;
- replacing glibc's complete matcher with a reduced grammar model;
- broad claims about musl, BSD libcs, Bash's independent matcher, or every glibc release.

## Reproduction

```sh
./run-matrix.sh
```

The script compiles `bench_fnmatch.c`, runs the primary family and four controls, writes CSV output, and removes the temporary executable through a trap.

Boundary commands:

```sh
timeout 7s ./bench_fnmatch '*(a|aa)b' 36 c 32 1
timeout 7s ./bench_fnmatch '*(a|aa)b' 38 c 32 1
timeout 7s ./bench_fnmatch '+(a|aa)b' 32 c 32 1
```

## Results

See [`RESULTS.md`](RESULTS.md) for the full matrix, growth fit, source mechanism, control interpretation, downstream context sample, overlap search, and artifact identities.

Key result:

```text
estimated growth per added character: 1.62103795
estimated growth per two characters: 2.62776402
log-time fit R^2: 0.99998878
```

## Interpretation

The current evidence establishes a deterministic algorithmic-complexity boundary in the installed glibc build. It is not ordinary linear wildcard scanning: the behavior requires overlapping extended alternatives and a later rejection, and its timing follows a near-perfect exponential fit over the measured range.

The source supports a repeated-state explanation because each successful prefix split can recursively restart the complete extended pattern at a suffix already reached by another decomposition. The work has not yet counted those states directly or proved a formal worst-case bound for the full implementation.

## Evidence boundary

Not yet executed or established:

- current canonical Sourceware master build;
- a second architecture or distribution build;
- full glibc test-suite execution;
- allocation and stack-depth counts;
- locale matrix beyond the container's inherited default;
- `FNM_PATHNAME`, `FNM_PERIOD`, wide-character, and negative-extglob complexity families;
- a semantic-preserving candidate patch;
- concrete remote or privilege-boundary reachability in a downstream consumer.

The GitHub mirror is archived. Its master source is supporting evidence only and must not be described as the canonical current upstream head.

## Next step

1. Implement a reduced matcher for the `*(a|aa)b` grammar that records unique suffix states and compare recursive-call count with memoized-state count.
2. Inspect current Sourceware Git and Bugzilla history through available non-Git retrieval paths.
3. Expand the bounded matrix to C and C.UTF-8, `*()` versus `+()`, and one negative-extglob family.
4. Map one downstream caller's pattern and candidate authority before discussing practical severity.
5. Decide whether the next artifact is a glibc regression/design report, a downstream mitigation note, or a retained complexity warning.

## Authority

No upstream issue, mailing-list message, patch submission, comment, review, email, or other external interaction is authorized or created. All work is local or inside Linux Fieldwork.
