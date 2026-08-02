# Handoff — glibc `fnmatch` extended-match complexity

Date: 2026-08-02  
Worker: GPT-5.6 Thinking  
State: `EXECUTING`  
External contact authorized: `false`

## Exact Linux Fieldwork state

- Repository: `teamleaderleo/linux-fieldwork`
- Branch: `investigation/glibc-fnmatch-extmatch-complexity`
- Base: `main@6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Exact predecessor before this handoff: `2b066fc685ef199b8c985decbde22f8c4cc0bc59`
- Current head: the commit adding this file; resolve with the branch ref
- Investigation: `investigations/glibc-fnmatch-extmatch-complexity/`
- Programme lane: `programmes/ecosystem-contributions/lanes/LF-39-foundational-library-boundary-corpus/`
- Target map: `targets/glibc/map.md`

## Direction change retained

Fresh bounded work no longer waits for the P0 contribution backlog or hosted CI. The branch updates LF-39 and the ecosystem-contributions status so source review, local/container execution, code review, hypotheses, and new investigations proceed whenever they have a discriminator, cleanup boundary, durable record, and stop rule.

## Finding

Debian glibc 2.41 exhibits rapid rejection-time growth for:

```text
pattern: *(a|aa)b
input:   a^n c
flags:   FNM_EXTMATCH
```

Measured per-call times include:

```text
n=28  0.101649 seconds
n=30  0.260793 seconds
n=32  0.692438 seconds
n=34  1.795662 seconds
n=36  4.813379 seconds
n=38  exceeded 7-second timeout
```

Matching input, prefix-disjoint alternatives, unambiguous extended matching, and flags-0 controls remain in the microsecond range.

## Mechanism evidence

The glibc 2.41 and 2.42 `*()`/`+()` implementation tries candidate splits and recursively restarts the complete extended pattern after continuation failure. Alternatives `a` and `aa` reach the same suffix positions through many decompositions.

Reduced model at `n=34`:

```text
naive recursive paths: 24,157,816
unique suffix states:  35
recompute ratio:       690,223x
```

Measured time versus model path count has log-log slope `1.00381241` and `R² = 0.99998883`.

## Current-release boundary

- Official current stable release: glibc 2.43, released 2026-01-23
- Stable branch: `release/2.43/master`
- Exact 2.41 tag: `74f59e9271cbb4071671e5a474e7d4f1622b186f`
- 2.41 `fnmatch_loop.c` blob: `9ec5e0edc656a774b3d1ab43c86755fe0c236672`
- 2.42 `fnmatch_loop.c` blob: `83f8861653673058e0ba80368d7b54629661aee6`
- 2.42 retains the recursive mechanism
- Published 2.42→2.43 release file inventory does not list `posix/fnmatch_loop.c` as changed

This supports an inference that 2.43 retained the 2.42 source mechanism. It is not a substitute for a direct official 2.43 checkout/build and exact blob receipt.

## Environment and artifacts

- Debian glibc package: `2.41-12+deb13u2`
- Kernel: Linux `6.12.13`, x86-64
- CPU: AMD EPYC 9V74
- GCC: `14.2.0`
- Bash: `5.2.37`
- Base benchmark locale: C
- Separate locale probe: C and C.utf8
- Runtime libc SHA-256: `adeedbc69ac402b762a3bd94759441e0546c33972cb2c0f5bc6869a2d32efed6`
- Primary CSV SHA-256: `fa5aa5ab97076fb32334f2dc16a0ad91fd758d69a6f4345f158e3d6227ebc9bc`

Tracked artifacts:

- `bench_fnmatch.c`
- `bench_fnmatch_locale.c`
- `run-matrix.sh`
- `model_states.py`
- `results/fnmatch-matrix.csv`
- `results/reduced-state-model.csv`
- `results/locale-matrix.csv`
- `RESULTS.md`
- `STATE_ANALYSIS.md`
- `DOWNSTREAM_CONTEXT.md`

## Locale result

C.utf8 roughly doubles constant cost for the tested ASCII family while preserving the rapid growth shape. Locale changes cost but does not eliminate the ambiguity mechanism.

## Downstream sample

PipeWire uses `FNM_EXTMATCH` during data-loop selection. The requester-provided `node.loop.name` or `node.loop.class` is used as the pattern; configured loop names/classes are candidates.

This proves production use and mixed argument ownership. It does not prove that a low-trust client can supply a high-cost accepted property or that PipeWire is vulnerable. The exact demonstrated long-candidate family does not directly map to ordinary short PipeWire loop names.

## First incomplete step

Materialize and build official current stable glibc:

```sh
git clone https://sourceware.org/git/glibc.git
cd glibc
git checkout release/2.43/master
git rev-parse HEAD
git hash-object posix/fnmatch_loop.c
```

Run the retained benchmark against the built libc through the glibc test/build environment and record exact build configuration, source head, library identity, command, cleanup, and rerun.

Direct Git and official tarball transport failed in the current disposable runner. That is an environment retrieval limitation, not a glibc result.

## Next safe technical actions

1. Enumerate full matcher state needed for semantic-preserving deduplication: subpattern identity, continuation, string position/end, flags, leading-period state, narrow/wide mode, and `ends` state.
2. Compare a compiled-state or memoized prototype against glibc's existing semantic test corpus without proposing it upstream yet.
3. Build glibc 2.43 in a runner with source transport.
4. Map one PipeWire low-trust node-creation path only if it accepts arbitrary loop-selector properties; otherwise retain the consumer example as configuration-bound.
5. Recheck Sourceware Bugzilla and libc-alpha before preparing any public draft.

## Evidence boundary

Not demonstrated:

- current stable binary execution;
- formal worst-case proof for the complete grammar;
- wide-character, pathname, period, and negative-extglob full matrices;
- allocation or stack maximums;
- a semantic-preserving candidate patch;
- remote reachability or a default affected service;
- behavior in musl, BSD libcs, or Bash's separate matcher.

## Cleanup

Local benchmark binaries, temporary files, and timed-out processes were removed. No background process, mount, socket, package installation, credential, external fork, public issue, public pull request, comment, review, or email remains from this work.

## Authority

Internal Linux Fieldwork source reading, local execution, container work, code review, hypotheses, branch writes, and tracked investigation records are authorized. Any glibc, PipeWire, Sourceware, mailing-list, or other upstream contact requires explicit authorization.
