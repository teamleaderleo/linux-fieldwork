# Handoff

## State

- Investigation: kmod nested `modprobe` configuration identity
- State: `EXECUTING`
- Linux Fieldwork branch: `investigation/kmod-modprobe-options-config-path`
- Linux Fieldwork base: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Linux Fieldwork head before this handoff update: `5828e9fa6a1d960c7b151876c50f7c0b6c664c95`
- Internal Linux Fieldwork draft PR: `teamleaderleo/linux-fieldwork#412`
- Owned kmod fork: `teamleaderleo/kmod`
- Native characterization PR: `teamleaderleo/kmod#1`
- Candidate repair PR: `teamleaderleo/kmod#2`
- External-contact state: unauthorized; none made

## Exact source identities

- canonical repository: `https://git.kernel.org/pub/scm/utils/kernel/kmod/kmod.git`;
- source-reading mirror: `kmod-project/kmod`;
- exact public/fork base: `5086df53090b2fe9fa1c31351c05a78a12a4ba71`;
- relevant source: `tools/modprobe.c`;
- relevant functions: `env_modprobe_options_append()` and `prepend_options_from_env()`;
- intent/documentation commit: `42d60a3267162a36ec6b6b39a7b91e5078b90979`;
- native characterization head: `f5406e1c15772bb306b9f2760cce44b2b6e9256f`;
- candidate carrier head: `52d4a64502ab9fcc0157dfa90a66596d0e3b32ae`.

## Demonstrated baseline

Debian `kmod 34.2-2` and exact source both reproduce the same split:

```text
no-space configuration path:
  parent marker: 1
  nested marker: 1

spaced configuration path:
  parent marker: 1
  nested marker: 0
  parent status: 0
  nested status: 0
```

Current kmod accepts the requested configuration in the parent. An `install` command invokes nested `modprobe`; the parent flattens `-C` and its raw pathname into `MODPROBE_OPTIONS`; the child reparses different argv and can use different configuration while still returning success.

Exact-master Linux Fieldwork run `30847812068` reproduced this result under both GCC and Clang with AddressSanitizer and UndefinedBehaviorSanitizer, clean reruns, and no sanitizer finding.

A target-native losing generation at `2e52d25e54a94fb531fd442079c7cf686f3e910b` also completed kmod's standard matrix with exactly one focused failure under both GCC and Clang: expected `parent` plus `nested`, observed only `parent`. Its build/test run was `30847595787`; format, spelling, and CodeQL passed. Later native head `f5406e1...` improves fixture independence and remains characterization only.

Retained package identities:

```text
test SHA-256: 8006c8cb24ef44803565fb580bd9334edb807e210f3a5c0f313679f260c211c1
root result SHA-256: c6ffd6ac62937b2ceb78786fe3b7610b5125f91db356f1f747c69fe4fe8286bc
immediate rerun SHA-256: c6ffd6ac62937b2ceb78786fe3b7610b5125f91db356f1f747c69fe4fe8286bc
unprivileged result SHA-256: 759550141d24d03543d0686b235e82b0aab8015181b50bddb169e9d297acd9cf
```

## Candidate boundary

The current private candidate is a bounded encoder/parser rewrite, not a quote-only change.

Generated `MODPROBE_OPTIONS` arguments:

- escape all C whitespace bytes;
- escape backslash, single quote, and double quote;
- encode an empty argument as `''`;
- use checked allocation arithmetic;
- stop the command if allocation or `setenv()` prevents complete propagation.

The parser:

- accepts repeated whitespace;
- accepts single-quoted and double-quoted segments;
- accepts backslash escapes outside quotes;
- preserves empty quoted arguments;
- rejects unmatched quotes and trailing escapes instead of silently accepting a truncated vector.

Native coverage includes:

- recursive `-C` with a space-bearing path;
- repeated `-C` with an empty second value;
- existing single-quoted and double-quoted forms;
- backslash-escaped whitespace;
- repeated spaces and tabs;
- unterminated quote and trailing-backslash failures;
- no real module insertion.

A separate byte-level model of the exact grammar round-tripped the empty string, all six C whitespace bytes, quotes, backslashes, every non-NUL byte value, and 10,000 random byte strings. This is supporting evidence only; compiled C and the native suite remain authoritative.

## Current candidate carrier

Candidate PR `teamleaderleo/kmod#2` is an internal draft. Head `52d4a64502ab9fcc0157dfa90a66596d0e3b32ae` temporarily contains:

- `.github/modprobe-options.patch`;
- `.github/modprobe-options-empty-argument.patch`;
- `.github/modprobe-options-append-errors.patch`;
- `.github/workflows/bootstrap-modprobe-options.yml`.

The one-shot workflow applies all three patches with `git apply --check`, removes every carrier file including itself, checks the diff, runs clang-format, builds and tests with sanitizer-enabled GCC and Clang, and only then commits the real source/test change back to the branch.

Focused gate history:

1. run `30847747276` failed before patch application because the reusable hosted-runner setup invoked package installation without elevation;
2. run `30847866493` applied the patch and passed formatting, then failed during configuration because `mbedx509` was absent;
3. run `30848267319` applied the patch and passed formatting, then showed Ubuntu 24.04 supplies Mbed TLS 2.28 while current kmod requires 3.6;
4. the focused gate now disables only the unrelated Mbed TLS signature backend, matching kmod's own Ubuntu matrix boundary.

Current authoritative focused run: `30849004709`, job `91804204728`, queued at the latest observation. Standard carrier-head CI runs were also queued. A queued run is not product evidence.

## Separate adjacent question

Options parsed from `MODPROBE_OPTIONS` are appended back into the same variable while processing the nested invocation. Across multiple recursive levels this can duplicate the propagated option list and grow it rapidly. That behavior predates the candidate and is not required to explain the pathname split.

Keep it as a separate successor unless execution proves it interferes with the current fix. A successor probe should measure exact argv and environment growth over at least three dependency-free recursive levels, repeated `-C` ordering, and the point at which behavior changes.

## Stop rule for the current repair

Do not call the repair ready until one exact final source head satisfies all of the following:

1. exact base and source identity are retained;
2. losing baseline remains attributable to current source;
3. all patch carriers apply without offset or fuzz and disappear from the final commit;
4. the final diff contains only intended product/test fixtures;
5. clang-format passes;
6. sanitizer-enabled GCC build and native suite pass;
7. sanitizer-enabled Clang build and native suite pass;
8. kmod's standard final-head CI is inspected, not inferred from the bootstrap;
9. cleanup and immediate rerun evidence are retained;
10. malformed-input, empty-argument, repeated-option, and pathname-byte boundaries are reviewed;
11. the recursive option-duplication successor is explicitly separated;
12. overlap is rechecked immediately before any authorized publication decision.

## First incomplete step

Inspect focused run `30849004709` on carrier head `52d4a645...`.

- If it fails, classify the first source or carrier failure and repair only that owner.
- If it passes and creates a real source commit, verify the exact final diff, fetch all final-head standard CI, rerun the focused gate without carrier state, and update PR #2 plus this handoff with exact hashes and artifacts.

## Cleanup

No local temporary configuration directory, helper process, module, mount, socket, lock, or persistent host configuration remains. Current state consists only of user-owned branches, internal draft PRs, retained evidence, and queued hosted execution.

## Authority

Linux Fieldwork PR #412 and kmod fork PRs #1 and #2 are internal user-owned review surfaces. No kmod-project issue, pull request, mailing-list post, email, comment, review, reaction, or other external contact is authorized or performed.
