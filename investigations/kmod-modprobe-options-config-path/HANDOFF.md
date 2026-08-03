# Handoff

## State

- Investigation: kmod nested `modprobe` configuration identity
- Disposition: `HOLD — exact source reproduced; final native characterization queued; candidate compatibility review open`
- Linux Fieldwork branch: `investigation/kmod-modprobe-options-config-path`
- Linux Fieldwork base: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Exact Linux Fieldwork head before this handoff commit: `c939f86078925315c55050dff124fe3728f834c1`
- Internal Linux Fieldwork draft PR: `teamleaderleo/linux-fieldwork#412`
- Owned kmod fork: `teamleaderleo/kmod`
- Native characterization PR/head: `teamleaderleo/kmod#1@84ba8ae9db4f455965efa22afdd5cb177781106b`
- Candidate validation PR/head: `teamleaderleo/kmod#2@cdc366bfaf8bcd1a9c5903f090f1d529e36782c4`
- Formal review submissions on PRs #412, #1, and #2: none
- External-contact state: unauthorized; none made

## Exact source and overlap

- Canonical repository: `https://git.kernel.org/pub/scm/utils/kernel/kmod/kmod.git`
- Source-reading mirror: `kmod-project/kmod`
- Exact public/fork base and current master observed 2026-08-04: `5086df53090b2fe9fa1c31351c05a78a12a4ba71`
- Relevant source: `tools/modprobe.c`
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

The parent accepts and uses the requested configuration. For an `install` command, current kmod flattens `-C` and the raw pathname into `MODPROBE_OPTIONS`; the nested process reparses a changed argument vector, can use another configuration, and still returns success.

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

## Exact current-source execution — complete

Linux Fieldwork run `30847812068` reproduced exact public source under GCC and Clang with AddressSanitizer and UndefinedBehaviorSanitizer.

### GCC

- Job: `91800328201`
- Artifact: `8869400073`, `kmod-modprobe-config-gcc-30847812068-1`
- Artifact digest: `sha256:46a343b8c91f3695d5c5be2de6a53415e26a3a19b53d0048ddff6fee7f22108c`
- Built `modprobe` SHA-256: `24c2090c2ab3b1a30144ced511e7c539aff70be9f0d0cdf54df93822795060d9`
- First/rerun result SHA-256: `02be6e9a9fc623e79502145cbf10bc7db5018b2a1d31f7c8037ab6d0e47d7ac8` for both

### Clang

- Job: `91800328204`
- Artifact: `8869400168`, `kmod-modprobe-config-clang-30847812068-1`
- Artifact digest: `sha256:9415ea4d8456a25ce7e061f96c5c598de30961edbaa8f5ed9f0d401d07672242`
- Built `modprobe` SHA-256: `abeaea0326b0bbcbc9804c67c5ddf0c00c31574111fad15d122de3e4dcf0f8bb`
- First/rerun result SHA-256: `1e5c6bf102f03d8159d8bf1273a829d3f0d62bc0c9794f5016ce2242dfc110e4` for both

Both binaries report:

```text
kmod version 34
+ZSTD +XZ +ZLIB +OPENSSL -MBEDTLS
```

Both toolchains observed the same no-space pass, spaced-path loss, quoted pass, and parser-control losses. Both source trees and cleanup receipts were clean. No sanitizer finding occurred.

## Native characterization

The owned characterization remains exactly five test/fixture files and no product source:

- `testsuite/meson.build`
- `testsuite/test-modprobe-options.c`
- `testsuite/rootfs-pristine/test-modprobe/install-cmd-loop/correct-config-path.txt`
- `testsuite/rootfs-pristine/test-modprobe/install-cmd-loop/etc/modprobe-config/recursive.conf`
- `testsuite/rootfs-pristine/test-modprobe/install-cmd-loop/etc/modprobe config/recursive.conf`

Current fixture:

```text
alias lf_recursive_config_alias mod-loop-a
install mod-loop-b $MODPROBE --show-alias lf_recursive_config_alias
```

The outer carrier `mod-loop-b` is dependency-free. Both tests use the fake `init_module` contract and require no loaded modules. Expected child output uses kmod's canonical module spelling `mod_loop_a`.

Expected unfixed result under each compiler:

- `PASSED: modprobe_options_config_path_control`
- `FAILED: modprobe_options_config_path_space`
- no other `FAILED:` line
- no dirty-root or loaded-module residue
- clean source tree and retained artifact

### Native generation history

1. Initial generation omitted `TC_INIT_MODULE_RETCODES`; both cases reached the host syscall and failed with `EPERM`.
2. Head `2e52d25...` added fake insertion but used outer `mod-loop-a`, whose dependency loaded `mod-loop-b` before the recursive hook. Linux Fieldwork's focused shared-root gate exposed dirty state. Standard kmod run `30847595787` still completed repository setup/build and retained a focused test-binary failure; it is historical, not the final independent fixture.
3. Head `f5406e1...` removed dependency state. Run `30848493313`, Clang job `91802512593`, reached the intended split, but the expected receipt used input spelling `mod-loop-a` while kmod prints `mod_loop_a`.
4. Current head `84ba8ae...` changes only that expected output line.

Prior Linux runs `30849170891` and `30849170909` were queued on technical head `8bbb2c...` and superseded by later documentation synchronization.

Successor runs registered on Linux head `c939f860...`:

- Dedicated kmod matrix: `30850150937`
- Linux Fieldwork CI: `30850149774`

Both were queued at the latest observation. This handoff-only commit will create another successor while preserving the same exact workflow and native source pins. Read the newest run IDs associated with the final branch head; do not treat cancellation or queue state as product evidence.

## Candidate v1 carrier

Candidate PR `teamleaderleo/kmod#2` is an internal draft at carrier head `cdc366bfaf8bcd1a9c5903f090f1d529e36782c4`.

Temporary carrier files:

- `.github/modprobe-options.patch`
- `.github/modprobe-options-empty-argument.patch`
- `.github/modprobe-options-append-errors.patch`
- `.github/workflows/bootstrap-modprobe-options.yml`

The workflow is validation-only:

- `contents: read`
- checkout credentials are not persisted
- exact base ancestry is required
- all patches use `git apply --check`
- carrier files are removed only in the runner
- the materialized net diff is compared against exact base `5086df...`
- only four product/test paths are allowed
- clang-format, GCC build/tests, and Clang build/tests run
- the runner restores the carrier branch state
- no commit or push step exists

Exact read-only PR validation:

- Run: `30850452134`
- Status at latest observation: queued

Ordinary carrier-head workflows were also queued. A green validation result is execution evidence only and cannot clear source-review blockers.

## Candidate v1 mechanism

Generated recursive values:

- escape C whitespace, backslash, single quote, and double quote
- encode an empty argument as `''`
- use checked allocation arithmetic
- stop option processing if allocation or `setenv()` prevents complete propagation

Parser behavior:

- accept repeated whitespace
- accept single-quoted and double-quoted segments
- accept backslash escapes outside quotes
- preserve empty quoted arguments
- reject unmatched quotes and trailing escapes

Native candidate coverage includes:

- recursive `-C` with a spaced path
- repeated `-C` with an empty second value
- single-quoted and double-quoted forms
- backslash-escaped whitespace
- repeated spaces and tabs
- unterminated quote and trailing-backslash failures
- fake module insertion only

A separate byte-level model of the proposed writer/parser round-tripped:

- empty string
- all six C whitespace bytes
- single quote, double quote, and backslash
- every non-NUL byte value
- 10,000 random byte strings

The model establishes writer/parser agreement for generated values. Compiled C and target-native tests remain authoritative.

## Candidate review blocker — legacy raw backslashes

The candidate gives every unquoted backslash escape semantics. Current kmod preserves a raw backslash literally in existing `MODPROBE_OPTIONS` values.

A compiled direct comparison of the exact current and candidate parser bodies produced:

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

Candidate PR #2 comment `5171318344` records this finding.

Before selecting source, choose explicitly among:

1. preserve a backslash literally unless it precedes a byte the writer actually escapes, and define trailing-backslash behavior separately;
2. move internally generated `-C` arguments to an unambiguous private transport without redefining the legacy parser;
3. explicitly accept and document the compatibility break, add reversing native controls, and obtain maintainer direction.

A green validation run does not clear this blocker.

## Adjacent recursive-growth boundary

Options parsed from `MODPROBE_OPTIONS` are appended back into the same variable while the nested invocation processes them. Across dependency-free recursive levels, the inherited list doubles.

For one 15-byte encoded pair (`-C /config\\ dir`):

```text
level  1:        2 tokens,       15 bytes
level  2:        4 tokens,       31 bytes
level  3:        8 tokens,       63 bytes
level  8:      256 tokens,    2,047 bytes
level 10:    1,024 tokens,    8,191 bytes
level 16:   65,536 tokens,  524,287 bytes
level 18:  262,144 tokens, 2,097,151 bytes
```

Candidate PR #2 comment `5171358526` records the exact recurrence.

This predates candidate v1 and does not explain the demonstrated one-level pathname split. It does limit broad claims about complete recursive transport. A separate native successor should measure at least three dependency-free levels, repeated `-C` ordering, exact environment growth, and termination behavior.

## Stop rule

Do not call a repair ready until one exact final source head satisfies all of the following:

1. exact public base and source identity retained;
2. losing package and exact-source evidence retained;
3. final independent native characterization retained under GCC and Clang;
4. temporary carrier patches and workflow absent from the final source commit;
5. final net diff limited to intended product/test files;
6. clang-format passes;
7. sanitizer-enabled GCC build and native suite pass;
8. sanitizer-enabled Clang build and native suite pass;
9. standard final-head CI is inspected;
10. cleanup and immediate rerun evidence retained;
11. malformed, empty, repeated-option, pathname-byte, and legacy-backslash boundaries reviewed;
12. recursive-growth scope explicitly bounded;
13. formal review state recorded honestly;
14. overlap and policy refreshed immediately before any authorized publication decision.

## First incomplete step

1. Read the newest Linux Fieldwork successor runs after this handoff commit.
2. Require repository CI success and the exact native pass/fail split under both compilers.
3. Read candidate validation `30850452134` if terminal; classify it as execution evidence only.
4. Resolve the legacy raw-backslash policy before modifying or materializing candidate source.
5. Keep package reproduction, exact-source reproduction, native characterization, candidate experiment, and recursive-growth successor as separate identities.
6. Update PRs #412, #1, and #2 with terminal receipts and final exact heads.
7. Do not contact upstream without explicit authorization.

If any job fails before its discriminator, repair only that carrier owner and rerun unchanged product logic.

## Cleanup

No local temporary configuration directory, helper process, module, mount, socket, lock, or persistent host configuration remains. Current state consists only of user-owned branches, internal draft PRs, retained evidence, and queued hosted execution.

## Authority

Linux Fieldwork PR #412 and kmod fork PRs #1 and #2 are internal user-owned review surfaces. No kmod-project issue, pull request, mailing-list post, email, comment, review, reaction, or other external contact is authorized or performed.
