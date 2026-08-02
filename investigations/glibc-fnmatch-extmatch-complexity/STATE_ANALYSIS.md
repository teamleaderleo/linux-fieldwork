# State analysis

## Reduced grammar

This model deliberately covers only the first investigation family:

```text
pattern: repeated choice of `a` or `aa`, followed by `b`
input:   `a` repeated n times, followed by `c`
```

It is not a replacement for glibc `fnmatch`. It omits locale, pathname boundaries, period handling, character classes, negative extglobs, nested grammar, allocation failure, and wide-character behavior.

## Naive paths versus unique states

The retained [`model_states.py`](model_states.py) evaluates the reduced grammar two ways:

1. naive recursion, which recomputes a suffix whenever another `a`/`aa` decomposition reaches it;
2. memoized recursion, which evaluates each input position once.

Selected output:

| `n` | Naive recursive calls | Unique suffix states | Recompute ratio |
| ---: | ---: | ---: | ---: |
| 14 | 1,596 | 15 | 106× |
| 20 | 28,656 | 21 | 1,365× |
| 24 | 196,417 | 25 | 7,857× |
| 28 | 1,346,268 | 29 | 46,423× |
| 30 | 3,524,577 | 31 | 113,696× |
| 32 | 9,227,464 | 33 | 279,620× |
| 34 | 24,157,816 | 35 | 690,223× |

The naive call counts follow the Fibonacci recurrence because each state branches to the next one- and two-byte suffixes. Unique state count remains `n + 1` in this reduced family.

## Relation to measured glibc time

For lengths 14 through 34, a log-log fit of measured glibc seconds against reduced-model naive calls produced:

```text
log(measured seconds) = 1.00381241 * log(naive calls) - 16.46807188
R^2 = 0.99998883
```

The slope is approximately one, meaning measured runtime is nearly proportional to the model's recursive path count across the tested range.

This does not prove glibc executes exactly one source-level recursive call for each reduced-model call. It does show that the timing family tracks the repeated-decomposition model far more closely than a linear or polynomial unique-state model.

## Locale context

The original timing probe did not call `setlocale`, so standard C process startup kept it in the `C` locale. The separate locale-aware probe calls `setlocale(LC_ALL, "")` and was run with `LC_ALL=C` and `LC_ALL=C.utf8`.

| Locale | `n=20` | `n=24` | `n=28` | `n=30` |
| --- | ---: | ---: | ---: | ---: |
| `C` | 0.002106 s | 0.014826 s | 0.100395 s | 0.260631 s |
| `C.utf8` | 0.004142 s | 0.033147 s | 0.192819 s | 0.502820 s |

`C.utf8` roughly doubled the constant cost for this ASCII family but retained the same rapid growth. The locale path affects cost; it does not remove the ambiguity mechanism.

## Design implications

A straightforward cache keyed only by input position is insufficient for full glibc semantics. A safe state identity may need to include:

- current pattern or subpattern identity;
- current string position and end boundary;
- flags after local `FNM_PERIOD` adjustment;
- `no_leading_period` state;
- narrow versus wide-character execution;
- any continuation state represented through the `ends` mechanism.

Negative extglobs may require richer state because success depends on the absence of alternative matches over candidate spans. Allocation failure is also observable: the current extension parser can return internal error values, so a compiled or cached representation needs an explicit failure contract.

The next algorithm review should therefore start by enumerating full matcher state, not by inserting an ad hoc cache into the recursive function.
