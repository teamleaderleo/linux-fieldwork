# Results — glibc `fnmatch` extended-match complexity

## Observed timing family

Runtime: Debian glibc `2.41-12+deb13u2`, x86-64, ordinary disposable container.

Pattern:

```text
*(a|aa)b
```

Rejecting candidate strings contain `n` copies of `a` followed by `c`. Matching controls contain the same prefix followed by `b`.

| `n` | Rejecting, seconds per call | Matching, seconds per call |
| ---: | ---: | ---: |
| 14 | 0.000115 | 0.000004 |
| 20 | 0.002118 | 0.000006 |
| 24 | 0.014314 | 0.000007 |
| 28 | 0.101649 | 0.000026 |
| 30 | 0.260793 | 0.000027 |
| 32 | 0.692438 | 0.000023 |
| 34 | 1.795662 | 0.000025 |

A separate boundary run observed:

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

A least-squares fit of `log(seconds)` against `n` for the primary rejecting matrix from 14 through 34 produced:

```text
log(seconds) = 0.48306665 * n - 15.827298
growth per added character = 1.62103795
estimated growth per two characters = 2.62776402
R^2 = 0.99998878
```

The measured factor is close to Fibonacci-style growth, which is expected when the matcher repeatedly chooses between consuming one or two indistinguishable `a` bytes and must exhaust the decompositions before rejecting the final `c`.

## Losing controls

The sharp growth depends on all three conditions: extended matching enabled, overlapping alternatives, and rejection after the ambiguous prefix.

At `n=34`:

| Case | Result | Seconds per call |
| --- | ---: | ---: |
| `*(a|aa)b`, rejecting suffix `c`, `FNM_EXTMATCH` | no match | 1.795662 |
| `*(a|aa)b`, matching suffix `b`, `FNM_EXTMATCH` | match | 0.000025 |
| `*(a)b`, rejecting suffix `c`, `FNM_EXTMATCH` | no match | 0.000027 |
| `*(a|b)b`, rejecting suffix `c`, `FNM_EXTMATCH` | no match | 0.000031 |
| literal `*(a|aa)b`, rejecting suffix `c`, flags `0` | no match | 0.000002 |

The unambiguous alternatives remain fast even though they execute the extended-match parser. The matching case returns before exhausting the decomposition tree. The flags-0 control treats the extglob punctuation literally.

## Source mechanism

Upstream tag `glibc-2.41` resolves to commit `74f59e9271cbb4071671e5a474e7d4f1622b186f`. `posix/fnmatch_loop.c` blob `9ec5e0edc656a774b3d1ab43c86755fe0c236672` implements `*()` and `+()` by:

1. parsing alternatives into a dynamic list;
2. trying every candidate split `rs` from the current string position through the end;
3. matching one alternative against the prefix;
4. matching the rest of the pattern;
5. after a failed rest, recursively invoking the complete extended pattern at `rs`.

For overlapping alternatives `a` and `aa`, the recursive step recomputes equivalent suffix states reached through different decompositions. No memoization or state deduplication is visible in this path.

The retrieved GitHub-mirror `master` blob `713caff58f3ff5845bac3583ec9ef8bf3f3fa737` retains the same recursive branch. The mirror is archived, so this is supporting source evidence rather than a claim about the current canonical Sourceware head.

## Existing tests

`posix/tst-fnmatch.input` contains broad semantic coverage for `FNM_EXTMATCH`, including nested and overlapping patterns, but the reviewed data is result-oriented. No input in the inspected suite asserts a complexity bound or creates a growing rejecting family equivalent to `*(a|aa)b` plus `a^n c`.

## Downstream context sample

A bounded source search found real callers enabling `FNM_EXTMATCH`. PipeWire's context loop selection calls `fnmatch(pattern, candidate, FNM_EXTMATCH)` for loop names and classes.

This establishes that the GNU extension has production consumers. It does **not** establish that an untrusted PipeWire client controls the relevant pattern, that the measured pattern is accepted in a default configuration, or that PipeWire is vulnerable. Those are separate authority and integration questions.

## Overlap search

Searches used:

```text
site:sourceware.org/bugzilla glibc fnmatch FNM_EXTMATCH exponential backtracking
site:inbox.sourceware.org/libc-alpha fnmatch extmatch exponential
glibc fnmatch EXT match exponential complexity CVE
GNU libc fnmatch *(a|aa) exponential
```

No exact equivalent report or active patch was found in the returned results. This is a bounded search result, not proof that no prior report exists.

## Artifact identities

```text
runtime libc SHA-256:
adeedbc69ac402b762a3bd94759441e0546c33972cb2c0f5bc6869a2d32efed6

locally compiled probe SHA-256:
a28ab2308dc2ca791f16a804b1b7d4314a8f8a07e4d705af210b4e34e41d6565

raw CSV SHA-256:
fa5aa5ab97076fb32334f2dc16a0ad91fd758d69a6f4345f158e3d6227ebc9bc
```

## Interpretation class

- **Demonstrated:** installed Debian glibc 2.41 exhibits rapid combinatorial rejection-time growth for a 9-byte ambiguous extended pattern.
- **Source-supported:** the glibc 2.41 recursive split-and-retry mechanism explains repeated equivalent suffix work.
- **Plausible consequence:** a long-running caller can suffer CPU amplification when an attacker or low-trust configuration can influence the candidate string or ambiguous extended pattern.
- **Not demonstrated:** remote exploitability, a default affected service, memory corruption, cross-libc behavior, current canonical Sourceware-head behavior, or an acceptable upstream algorithmic replacement.
