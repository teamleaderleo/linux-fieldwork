# Results — glibc `fnmatch` extended-match complexity

## Observed timing family

Runtime: Debian glibc `2.41-12+deb13u2`, x86-64, ordinary disposable container, C locale.

Pattern:

```text
*(a|aa)b
```

Rejecting strings contain `n` copies of `a` followed by `c`. Matching controls contain the same prefix followed by `b`.

| `n` | Rejecting, seconds per call | Matching, seconds per call |
| ---: | ---: | ---: |
| 14 | 0.000115 | 0.000004 |
| 20 | 0.002118 | 0.000006 |
| 24 | 0.014314 | 0.000007 |
| 28 | 0.101649 | 0.000026 |
| 30 | 0.260793 | 0.000027 |
| 32 | 0.692438 | 0.000023 |
| 34 | 1.795662 | 0.000025 |

Boundary run:

```text
n=34: 1.876586996 seconds, completed
n=36: 4.813378942 seconds, completed
n=38: exceeded a 7-second process timeout
```

The related `+(a|aa)b` rejecting family also grew rapidly:

```text
n=28: 0.106895203 seconds
n=30: 0.246770404 seconds
n=32: 0.662719943 seconds
```

## Growth fit

```text
log(seconds) = 0.48306665 * n - 15.827298
growth per added character = 1.62103795
estimated growth per two characters = 2.62776402
R^2 = 0.99998878
```

The measured factor is close to Fibonacci growth, expected when the matcher repeatedly chooses between consuming one or two indistinguishable `a` bytes and exhausts decompositions before rejecting the final `c`.

## Losing controls

At `n=34`:

| Case | Result | Seconds per call |
| --- | ---: | ---: |
| `*(a|aa)b`, suffix `c`, `FNM_EXTMATCH` | no match | 1.795662 |
| `*(a|aa)b`, suffix `b`, `FNM_EXTMATCH` | match | 0.000025 |
| `*(a)b`, suffix `c`, `FNM_EXTMATCH` | no match | 0.000027 |
| `*(a|b)b`, suffix `c`, `FNM_EXTMATCH` | no match | 0.000031 |
| literal `*(a|aa)b`, suffix `c`, flags `0` | no match | 0.000002 |

The sharp growth requires extended matching, overlapping alternatives, and rejection after the ambiguous prefix. Prefix-disjoint alternatives stay fast despite executing the extension parser.

## Repeated-state model

The reduced model in [`model_states.py`](model_states.py) implements only the first family's one-or-two-byte decomposition. It is not a replacement for glibc.

| `n` | Naive recursive calls | Unique suffix states | Recompute ratio |
| ---: | ---: | ---: | ---: |
| 20 | 28,656 | 21 | 1,365× |
| 24 | 196,417 | 25 | 7,857× |
| 28 | 1,346,268 | 29 | 46,423× |
| 30 | 3,524,577 | 31 | 113,696× |
| 32 | 9,227,464 | 33 | 279,620× |
| 34 | 24,157,816 | 35 | 690,223× |

Measured glibc time tracks reduced-model recursive paths closely:

```text
log(measured seconds) = 1.00381241 * log(naive calls) - 16.46807188
R^2 = 0.99998883
```

This strongly supports repeated equivalent suffix work. It does not prove an exact source-level call count or a complete formal bound for the full grammar.

## Locale matrix

The base benchmark does not call `setlocale`, so it runs in the C locale. A separate probe calls `setlocale(LC_ALL, "")`.

| Locale | `n=20` | `n=24` | `n=28` | `n=30` |
| --- | ---: | ---: | ---: | ---: |
| `C` | 0.002106 s | 0.014826 s | 0.100395 s | 0.260631 s |
| `C.utf8` | 0.004142 s | 0.033147 s | 0.192819 s | 0.502820 s |

`C.utf8` roughly doubles constant cost for the ASCII family but retains the same growth shape.

## Source mechanism

The 2.41 `posix/fnmatch_loop.c` implements `*()` and `+()` by:

1. parsing alternatives into a dynamic list;
2. trying each split `rs` from the current string position through the end;
3. matching an alternative against the prefix;
4. matching the continuation;
5. after continuation failure, recursively invoking the complete extended pattern at `rs`.

For alternatives `a` and `aa`, different decompositions reach equivalent suffix positions. No memoization or state deduplication is visible in this path.

Exact source receipts:

- `glibc-2.41@74f59e9271cbb4071671e5a474e7d4f1622b186f`;
- 2.41 `fnmatch_loop.c` blob `9ec5e0edc656a774b3d1ab43c86755fe0c236672`;
- 2.42 `fnmatch_loop.c` blob `83f8861653673058e0ba80368d7b54629661aee6`, retaining the same recursive branch;
- archived mirror master blob `713caff58f3ff5845bac3583ec9ef8bf3f3fa737`, also retaining it.

Official project status identifies glibc 2.43 as current stable and `release/2.43/master` as its stable branch. The published 2.42→2.43 release file inventory does not list `posix/fnmatch_loop.c` as changed. This supports an inference that 2.43 retained the 2.42 mechanism, but a direct 2.43 checkout/build is still required for execution and exact blob identity.

## Existing tests

`posix/tst-fnmatch.input` contains broad result-oriented `FNM_EXTMATCH` coverage, including nested and overlapping patterns. No reviewed input asserts a complexity bound or creates a growing rejecting family equivalent to `*(a|aa)b` plus `a^n c`.

## Downstream context sample

PipeWire's context loop selection calls `fnmatch(pattern, candidate, FNM_EXTMATCH)` for loop names and classes.

This establishes a production consumer. It does **not** establish untrusted pattern control, acceptance in a default configuration, or a PipeWire vulnerability. Pattern and candidate authority remain a separate investigation question.

## Overlap search

Searches covered Sourceware Bugzilla, libc-alpha archives, glibc commits, general web results, and the historical glibc/gnulib synchronization. No exact equivalent complexity report or active patch appeared in returned results. This is bounded search evidence, not proof of absence.

## Artifact identities

```text
runtime libc SHA-256:
adeedbc69ac402b762a3bd94759441e0546c33972cb2c0f5bc6869a2d32efed6

locally compiled primary probe SHA-256:
a28ab2308dc2ca791f16a804b1b7d4314a8f8a07e4d705af210b4e34e41d6565

primary CSV SHA-256:
fa5aa5ab97076fb32334f2dc16a0ad91fd758d69a6f4345f158e3d6227ebc9bc
```

## Interpretation class

- **Demonstrated:** Debian glibc 2.41 exhibits rapid combinatorial rejection-time growth for a nine-byte ambiguous extended pattern.
- **Demonstrated:** the timing family tracks a Fibonacci reduced-model path count, while unique suffix positions remain linear.
- **Source-supported:** 2.41 and 2.42 use the recursive split-and-retry mechanism that explains equivalent suffix recomputation.
- **Release-diff inference:** glibc 2.43 retained that source file from 2.42.
- **Plausible consequence:** CPU amplification where a caller permits low-trust influence over an ambiguous pattern or candidate.
- **Not demonstrated:** remote exploitability, a default affected service, memory corruption, current stable execution, cross-libc behavior, or an acceptable upstream algorithmic replacement.
