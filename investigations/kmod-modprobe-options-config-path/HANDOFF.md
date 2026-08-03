# Handoff

## State

- Investigation: kmod nested `modprobe` configuration identity
- Disposition: `HOLD — native characterization complete; candidate v1 compatibility-blocked; exact-transport v2 model executed`
- Linux Fieldwork branch: `investigation/kmod-modprobe-options-config-path`
- Linux Fieldwork base: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Exact Linux Fieldwork head before this handoff update: `8f1c2b4425c2bb32e0dc1248f22d5e919e2fe1fd`
- Internal Linux Fieldwork draft PR: `teamleaderleo/linux-fieldwork#412`
- Owned kmod fork: `teamleaderleo/kmod`
- Native characterization PR/head: `teamleaderleo/kmod#1@84ba8ae9db4f455965efa22afdd5cb177781106b`
- Candidate v1 validation PR/head: `teamleaderleo/kmod#2@5eac368b1bdbb9901e333c3e621170fae69a5dfb`
- Formal review submissions on PRs #412, #1, and #2: none at the latest check
- External-contact state: unauthorized; none made

## Exact source and overlap

- Canonical repository: `https://git.kernel.org/pub/scm/utils/kernel/kmod/kmod.git`
- Source-reading mirror: `kmod-project/kmod`
- Exact public/fork base and latest observed master: `5086df53090b2fe9fa1c31351c05a78a12a4ba71`
- Relevant product source: `tools/modprobe.c`
- Relevant functions: `env_modprobe_options_append()` and `prepend_options_from_env()`
- Intent/documentation commit: `42d60a3267162a36ec6b6b39a7b91e5078b90979`
- Fresh open issue/PR searches found no matching recursive `-C` whitespace-path implementation.
- Upstream PR #139 concerns secure environment access generally and is not a duplicate.

Repeat source freshness, contribution policy, and overlap immediately before any authorized public action.

## Demonstrated package behavior

Debian `kmod 34.2-2` reproduces:

```text
no-space configuration path:
  parent marker: 1
  nested marker: 1

spaced configuration path:
  parent marker: 1
  nested marker: 0
  parent status: 0
  nested status: 0
  MODPROBE_OPTIONS=-C $TMP/space/conf dir
```

The parent accepts and uses the requested configuration. For an `install` command, current kmod flattens `-C` and its raw pathname into `MODPROBE_OPTIONS`; the nested process reparses a changed argument vector, can use another configuration, and still returns success.

Controls:

- manually quoted spaced path: selected configuration preserved;
- leading/repeated spaces: selected configuration lost while status remains 0;
- tab separator: selected configuration lost while status remains 0;
- unmatched quote: selected configuration lost while status remains 0;
- EUID 0 and EUID 65534 agree;
- immediate normalized rerun is byte-identical;
- no real module insertion or removal occurs.

Retained package identities:

```text
test SHA-256: 8006c8cb24ef44803565fb580bd9334edb807e210f3a5c0f313679f260c211c1
root result SHA-256: c6ffd6ac62937b2ceb78786fe3b7610b5125f91db356f1f747c69fe4fe8286bc
immediate rerun SHA-256: c6ffd6ac62937b2ceb78786fe3b7610b5125f91db356f1f747c69fe4fe8286bc
unprivileged result SHA-256: 759550141d24d03543d0686b235e82b0aab8015181b50bddb169e9d297acd9cf
```

## Exact current-source execution

Linux Fieldwork run `30847812068` first established exact current-source behavior under GCC and Clang with AddressSanitizer and UndefinedBehaviorSanitizer.

### GCC

- Job: `91800328201`
- Artifact: `8869400073`
- Artifact digest: `sha256:46a343b8c91f3695d5c5be2de6a53415e26a3a19b53d0048ddff6fee7f22108c`
- Built `modprobe` SHA-256: `24c2090c2ab3b1a30144ced511e7c539aff70be9f0d0cdf54df93822795060d9`
- First/rerun result SHA-256: `02be6e9a9fc623e79502145cbf10bc7db5018b2a1d31f7c8037ab6d0e47d7ac8`

### Clang

- Job: `91800328204`
- Artifact: `8869400168`
- Artifact digest: `sha256:9415ea4d8456a25ce7e061f96c5c598de30961edbaa8f5ed9f0d401d07672242`
- Built `modprobe` SHA-256: `abeaea0326b0bbcbc9804c67c5ddf0c00c31574111fad15d122de3e4dcf0f8bb`
- First/rerun result SHA-256: `1e5c6bf102f03d8159d8bf1273a829d3f0d62bc0c9794f5016ce2242dfc110e4`

Both toolchains observed the same no-space pass, spaced-path loss, quoted pass, and parser-control losses. Source trees and cleanup receipts were clean. No sanitizer finding occurred.

Final Linux run `30850597196` reran exact master at Linux Fieldwork head `22c4b0733935d4cf43cb4822454e96f8d57dfb4e`:

- exact master GCC job `91809392831`: success; artifact `8872328734`, digest `sha256:3c3f1c2bb5e39a1ff79afd0bc2147eded059898fee51c370854a3b9ba4e240cf`;
- exact master Clang job `91809393003`: success; artifact `8872330735`, digest `sha256:a078ebff15f174b550b0c813efe035a7894faa5c28bdb9febfd2a031cc0e3fcb`.

## Final native characterization — complete

The owned characterization is exactly five test/fixture files and no product source:

- `testsuite/meson.build`
- `testsuite/test-modprobe-options.c`
- `testsuite/rootfs-pristine/test-modprobe/install-cmd-loop/correct-config-path.txt`
- `testsuite/rootfs-pristine/test-modprobe/install-cmd-loop/etc/modprobe-config/recursive.conf`
- `testsuite/rootfs-pristine/test-modprobe/install-cmd-loop/etc/modprobe config/recursive.conf`

Fixture:

```text
alias lf_recursive_config_alias mod-loop-a
install mod-loop-b $MODPROBE --show-alias lf_recursive_config_alias
```

The outer carrier `mod-loop-b` is dependency-free. Both tests use fake module insertion and require no loaded modules. Expected child output uses canonical module spelling `mod_loop_a`.

Final run `30850597196` completed successfully with the required intentional split under both compilers:

```text
FAILED: modprobe_options_config_path_space
PASSED: modprobe_options_config_path_control
```

No other `FAILED:` line, dirty-root diagnostic, or loaded-module residue was present.

### Native GCC

- Job: `91809392813`
- Artifact: `8872300649`, `kmod-native-characterization-gcc-30850597196-1`
- Artifact digest: `sha256:885c7b262c3b01c2da2934e1ed07179b7f76b84d3008e9a42b6572e8119c8bb8`
- Built `modprobe` SHA-256: `2bee340f879e7c1086aeb9b33846be2b5c82b7208269fc13f97753c0c3228936`
- Test log SHA-256: `d47d011f74a340f944e26e27aa3a8cf1a9eccd908e4040104591b0faf06691eb`
- Source head: `84ba8ae9db4f455965efa22afdd5cb177781106b`
- Product blob: `413960cae0f39945a3f2d6509dc4a8c262ae2609`
- Source status before/after: empty

### Native Clang

- Job: `91809392817`
- Artifact: `8872573911`, `kmod-native-characterization-clang-30850597196-1`
- Artifact digest: `sha256:3b96ae73ce6ad2f9f49f2c50430c0faf1b872fdad9ccb497a43b3fe9c3b6c4a3`
- Built `modprobe` SHA-256: `60b01dade4c3bc8b04bdae9ea5273608775a67039b82efaabddec12d3ed9ac15`
- Test log SHA-256: `3d121c9b04a09f5f2b0b5ebcd4e9bf6f9ce7185bb96a1fbb42293391f6fec53d`
- Source head: `84ba8ae9db4f455965efa22afdd5cb177781106b`
- Product blob: `413960cae0f39945a3f2d6509dc4a8c262ae2609`
- Source status before/after: empty

Linux Fieldwork CI run `30850594565`, job `91809380048`, also completed successfully: patch validation, Python compilation, repository unit tests, shell syntax, and command-help gates passed.

The baseline and native-characterization questions are closed for the exact source and fixture identities above.

## Candidate v1

Candidate PR `teamleaderleo/kmod#2` remains a temporary read-only validation carrier. It does not contain a selected source commit.

Carrier files:

- `.github/modprobe-options.patch`
- `.github/modprobe-options-empty-argument.patch`
- `.github/modprobe-options-append-errors.patch`
- `.github/workflows/bootstrap-modprobe-options.yml`

The workflow has `contents: read`, does not persist credentials, never commits or pushes, checks exact base ancestry, removes carrier files only in the runner, requires a four-file materialized net diff, runs formatting and GCC/Clang suites, and restores the branch.

Read-only validation `30850452134`, job `91808908966`, failed before source execution because `.github/modprobe-options-empty-argument.patch` had corrupt hunk counts at line 32. The patch body was intact; three headers overstated their old/new line counts:

```text
6/29 -> 5/25
6/8  -> 5/7
10/15 -> 8/13
```

Only those hunk headers were repaired at candidate head `5eac368b1bdbb9901e333c3e621170fae69a5dfb`.

Successor read-only validation:

- Run: `30857305994`
- Status at latest observation: queued

A green successor is execution evidence only and cannot clear the source-review blocker below.

## Candidate v1 blocker — legacy raw backslashes

Candidate v1 gives every unquoted backslash escape semantics. Current kmod preserves a raw backslash literally in existing `MODPROBE_OPTIONS` values.

Compiled comparison:

```text
input: -C /foo\bar
current:   [-C] [/foo\bar]
candidate: [-C] [/foobar]

input: -C /foo\\bar
current:   [-C] [/foo\\bar]
candidate: [-C] [/foo\bar]

input: -C /foo\
current:   [-C] [/foo\]
candidate: INVALID

input: -C /foo\'bar
current:   [-C] [/foo\'bar]
candidate: [-C] [/foo'bar]
```

Candidate PR #2 comment `5171318344` retains the complete matrix. Do not materialize candidate v1 as source merely because its own writer/parser round-trip or its tests pass.

## Recursive-growth boundary

Current propagation reparses inherited options and appends them back into the same variable. Across dependency-free recursive levels, the inherited list doubles.

For one 15-byte encoded pair:

```text
level  1:        2 tokens,       15 bytes
level  2:        4 tokens,       31 bytes
level  3:        8 tokens,       63 bytes
level 10:    1,024 tokens,    8,191 bytes
level 16:   65,536 tokens,  524,287 bytes
level 18:  262,144 tokens, 2,097,151 bytes
```

Candidate PR #2 comment `5171358526` retains the recurrence. This predates candidate v1 and does not explain the one-level pathname split, but it prevents broad claims about complete recursive transport.

## Exact-transport v2 model

A separate policy/mechanism model now tests a compatibility-preserving direction without modifying kmod source:

- script: `investigations/kmod-modprobe-options-config-path/model_exact_option_transport.py`;
- result: `investigations/kmod-modprobe-options-config-path/artifacts/exact-option-transport-model.json`;
- script SHA-256: `92a9c0ae9722c9b290240271a00bc2dfebfbabb2851cd85cc4b2f4fe2826ae39`;
- result-file SHA-256: `3b119aa542dd5c6898551e739f931c3b27c268bb3ca0b210d5e0f6f1c75a025b`.

Model policy:

1. when no versioned exact record exists, use argv already produced by the current legacy parser;
2. when an exact record exists, it is authoritative and the legacy string is only a compatibility/diagnostic mirror;
3. consume and rebuild the exact vector once per invocation rather than appending inherited options again.

Executed result:

- 10,007 generated byte-string cases round-tripped;
- empty values, all non-NUL byte values, whitespace, quotes, and backslashes were included;
- nine malformed records were rejected;
- three legacy raw-backslash argv cases remained unchanged when no exact record was present;
- exact input won when both representations were supplied;
- one five-argument record stayed at 39 bytes and five arguments through 20 recursive levels;
- canonical exact-record SHA-256: `9c6f39999b4cce6df34d06975ded4720b144c5db197a36c0ee54a7ae6d60d8a2`;
- generated corpus record SHA-256: `45e6e890f50f892243a5fcbb9baf1ea2f2e1d3d43bc849595595f2d017cc349c`.

This is model evidence only. It does not establish compiled C behavior, a variable name or wire contract acceptable to maintainers, hostile dual-variable precedence, supported environment-size limits, or integration with every install/remove topology.

## Current technical interpretation

The strongest next implementation direction is **not** a broader legacy grammar rewrite. It is a separate versioned, length-delimited internal argv transport with these premises:

- preserve current legacy parsing when no exact internal record exists;
- use exact length-delimited bytes for internally propagated arguments;
- consume and rebuild the exact record once per invocation;
- keep any legacy string as a non-authoritative compatibility mirror for install/remove scripts;
- reject malformed exact records and checked-arithmetic failures;
- add explicit precedence tests when both representations exist;
- prove stable option count and environment size through at least three real recursive levels.

Do not overwrite candidate v1. Create any v2 source experiment on a separate owned branch from exact base.

## Stop rule

Do not call a repair ready until one exact final source head satisfies all of the following:

1. exact public base and source identity retained;
2. losing package, exact-source, and final native-characterization evidence retained;
3. temporary patch/workflow carriers absent from the final source commit;
4. final net diff limited to intended product/test files;
5. legacy raw-backslash behavior either preserved or explicitly changed with maintainer direction;
6. exact transport malformed-input and checked-arithmetic controls pass;
7. repeated and empty arguments preserve order and identity;
8. at least three real recursive levels show bounded option count and environment size;
9. sanitizer-enabled GCC build and native suite pass;
10. sanitizer-enabled Clang build and native suite pass;
11. standard final-head CI is inspected;
12. cleanup and immediate rerun evidence retained;
13. formal review state recorded honestly;
14. overlap and policy refreshed immediately before any authorized publication decision.

## First incomplete step

1. Read successor candidate validation `30857305994` when terminal; classify it as candidate-v1 execution only.
2. Keep candidate v1 on HOLD regardless of green execution.
3. Create a separate candidate-v2 source experiment from exact base using the versioned length-delimited policy above.
4. Add native controls for legacy raw backslashes, empty/repeated arguments, malformed records, dual-representation precedence, and three recursive levels.
5. Run focused GCC/Clang sanitizers before ordinary fork CI.
6. Retain one exact final source-only diff if v2 succeeds.
7. Do not contact upstream without explicit authorization.

If a job fails before its discriminator, repair only that carrier owner and rerun unchanged product logic.

## Cleanup

No local temporary configuration directory, helper process, module, mount, socket, lock, or persistent host configuration remains. Current state consists only of user-owned branches, internal draft PRs, retained evidence, and hosted execution.

## Authority

Linux Fieldwork PR #412 and kmod fork PRs #1 and #2 are internal user-owned review surfaces. No kmod-project issue, pull request, mailing-list post, email, comment, review, reaction, or other external contact is authorized or performed.
