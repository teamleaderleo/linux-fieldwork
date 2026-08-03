# Handoff

## State

- Investigation: kmod nested `modprobe` configuration identity
- State: `HOLD — exact source reproduced; final native characterization queued; candidate compatibility review open`
- Linux Fieldwork branch: `investigation/kmod-modprobe-options-config-path`
- Linux Fieldwork base: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Exact Linux Fieldwork technical head before this handoff commit: `8bbb2c076ae3a1668adb3a08a272b1b8ad27125f`
- Internal Linux Fieldwork draft PR: `teamleaderleo/linux-fieldwork#412`
- Owned kmod fork: `teamleaderleo/kmod`
- Native characterization PR: `teamleaderleo/kmod#1`
- Native characterization head: `84ba8ae9db4f455965efa22afdd5cb177781106b`
- Candidate repair PR: `teamleaderleo/kmod#2`
- Candidate carrier head: `3f07a0ecc3ee7ad7895c635f66b2dd97219d232f`
- Formal review submissions on PRs #412, #1, and #2: none
- External-contact state: unauthorized; none made

## Exact source identities and overlap

- canonical repository: `https://git.kernel.org/pub/scm/utils/kernel/kmod/kmod.git`;
- source-reading mirror: `kmod-project/kmod`;
- exact public/fork base and current master observed 2026-08-04: `5086df53090b2fe9fa1c31351c05a78a12a4ba71`;
- relevant source: `tools/modprobe.c`;
- relevant functions: `env_modprobe_options_append()` and `prepend_options_from_env()`;
- intent/documentation commit: `42d60a3267162a36ec6b6b39a7b91e5078b90979`;
- fresh open issue/PR searches found no matching recursive `-C` whitespace-path implementation;
- upstream PR #139 concerns secure environment access generally and is not a duplicate.

Repeat source freshness and overlap immediately before any authorized public action.

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

A manually quoted spaced path is a passing control. Leading/repeated spaces, tabs, and unmatched quotes silently lose the selected configuration while status remains 0. Root and EUID 65534 agree. No real module insertion or removal occurs.

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

- job: `91800328201`;
- artifact: `8869400073`, `kmod-modprobe-config-gcc-30847812068-1`;
- artifact digest: `sha256:46a343b8c91f3695d5c5be2de6a53415e26a3a19b53d0048ddff6fee7f22108c`;
- built `modprobe` SHA-256: `24c2090c2ab3b1a30144ced511e7c539aff70be9f0d0cdf54df93822795060d9`;
- first/rerun result SHA-256: `02be6e9a9fc623e79502145cbf10bc7db5018b2a1d31f7c8037ab6d0e47d7ac8` for both.

### Clang

- job: `91800328204`;
- artifact: `8869400168`, `kmod-modprobe-config-clang-30847812068-1`;
- artifact digest: `sha256:9415ea4d8456a25ce7e061f96c5c598de30961edbaa8f5ed9f0d401d07672242`;
- built `modprobe` SHA-256: `abeaea0326b0bbcbc9804c67c5ddf0c00c31574111fad15d122de3e4dcf0f8bb`;
- first/rerun result SHA-256: `1e5c6bf102f03d8159d8bf1273a829d3f0d62bc0c9794f5016ce2242dfc110e4` for both.

Both report `kmod version 34` with `+ZSTD +XZ +ZLIB +OPENSSL -MBEDTLS`. Both observed the same no-space pass, spaced-path loss, quoted pass, and parser-control losses. Both source trees and cleanup receipts were clean. No sanitizer finding occurred.

## Native characterization

The owned characterization remains exactly five test/fixture files and no product source:

- `testsuite/meson.build`;
- `testsuite/test-modprobe-options.c`;
- `testsuite/rootfs-pristine/test-modprobe/install-cmd-loop/correct-config-path.txt`;
- `testsuite/rootfs-pristine/test-modprobe/install-cmd-loop/etc/modprobe-config/recursive.conf`;
- `testsuite/rootfs-pristine/test-modprobe/install-cmd-loop/etc/modprobe config/recursive.conf`.

Current fixture:

```text
alias lf_recursive_config_alias mod-loop-a
install mod-loop-b $MODPROBE --show-alias lf_recursive_config_alias
```

The outer carrier `mod-loop-b` is dependency-free. Both tests use the fake `init_module` contract and require no loaded modules. Expected child output uses kmod's canonical module spelling `mod_loop_a`.

Expected unfixed result under each compiler:

- `PASSED: modprobe_options_config_path_control`;
- `FAILED: modprobe_options_config_path_space`;
- no other `FAILED:` line;
- no dirty-root or loaded-module residue;
- clean source tree and retained artifact.

### Native generation history

1. The first generation omitted `TC_INIT_MODULE_RETCODES`; both cases reached the host syscall and failed with `EPERM`.
2. Head `2e52d25...` added the fake syscall field but used outer `mod-loop-a`, whose dependency loaded `mod-loop-b` before the recursive hook. Linux Fieldwork's focused shared-root gate exposed dirty state. Standard kmod run `30847595787` still completed repository setup/build and retained one focused test-binary failure; it is historical evidence, not the final independent fixture.
3. Head `f5406e1...` removed dependency state. Run `30848493313`, Clang job `91802512593`, reached the intended product split: the spaced case failed through missing recursive alias resolution and the control returned success, but the expected receipt used input spelling `mod-loop-a` while kmod prints canonical `mod_loop_a`.
4. Current head `84ba8ae...` changes only that expected output line.

Runs registered for Linux technical head `8bbb2c...`:

- dedicated kmod matrix `30849170891`;
- Linux Fieldwork CI `30849170909`.

Both were queued at the latest observation. This handoff-only commit will supersede them under branch concurrency while retaining the same workflow and source pins. Read the successor runs, not the cancelled queue entries.

## Candidate carrier and source design

Candidate PR `teamleaderleo/kmod#2` is an internal draft. Carrier head `3f07a0ecc3ee7ad7895c635f66b2dd97219d232f` temporarily contains:

- `.github/modprobe-options.patch`;
- `.github/modprobe-options-empty-argument.patch`;
- `.github/modprobe-options-append-errors.patch`;
- `.github/workflows/bootstrap-modprobe-options.yml`.

The one-shot workflow applies all patches with `git apply --check`, removes every carrier file including itself, checks formatting, builds and tests under GCC and Clang, and commits the real source/test diff only after every step succeeds on a non-PR event.

Candidate mechanism:

- generated values escape C whitespace, backslash, single quote, and double quote;
- an empty argument is encoded as `''`;
- allocation arithmetic is checked;
- append failures stop option processing;
- parser accepts repeated whitespace, quoted segments, and backslash escapes outside quotes;
- parser preserves empty quoted arguments;
- unmatched quotes and a trailing escape fail closed.

Native candidate coverage includes a recursive spaced configuration path, repeated `-C` with an empty argument, quote forms, backslash-escaped whitespace, repeated spaces/tabs, malformed quoting, and fake module insertion.

A separate byte-level model of the proposed writer/parser round-tripped the empty string, all six C whitespace bytes, quotes, backslashes, every non-NUL byte value, and 10,000 random byte strings. This is supporting evidence only; compiled C and target-native execution remain authoritative.

### Candidate carrier history

Earlier focused runs failed only in setup before source execution:

1. package installation lacked elevation;
2. `mbedx509` headers were absent;
3. Ubuntu 24.04 supplied Mbed TLS 2.28 while current kmod requires 3.6.

The carrier now disables only the unrelated Mbed TLS backend, matching an existing kmod Ubuntu configuration. Complete review also corrected the candidate fixture's output from `mod-loop-a` to canonical `mod_loop_a` at carrier head `3f07a0e...`.

Current bootstrap run `30849580121`, job `91806061935`, and ordinary carrier-head workflows were queued at the latest observation. A queued run is not a product result.

## Candidate review blocker — raw backslash compatibility

The byte model proves generated values round-trip under the new grammar; it does not prove compatibility for existing values parsed by current kmod.

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

The candidate gives every unquoted backslash escape semantics. Current kmod preserves it literally. This changes existing/private `MODPROBE_OPTIONS` values and contradicts the earlier boundary that legacy strings remain unchanged.

Before selecting this source, choose explicitly among:

1. preserve a backslash literally unless it precedes a byte the writer actually escapes, and define trailing-backslash behavior separately;
2. move internally generated `-C` arguments to an unambiguous private transport without redefining the legacy parser;
3. explicitly accept and document the compatibility break, add reversing native controls, and obtain maintainer direction.

Candidate PR #2 comment `5171318344` records this finding. A green bootstrap does not clear it.

## Candidate workflow review blocker

The temporary workflow grants `contents: write` on `pull_request`, although PR runs hard-checkout the owned branch and skip the commit step. Remove the PR trigger or split read-only and write jobs before retaining the workflow. The final materialized source commit must contain no bootstrap workflow or patch carrier.

## Separate adjacent question — recursive growth

Options parsed from `MODPROBE_OPTIONS` are appended back into the same variable while processing the nested invocation. Across multiple recursive levels this can duplicate the propagated option list and grow it rapidly. This predates the candidate and is not needed to explain the one-level pathname split, but it directly affects claims of complete recursive transport.

A successor probe should measure exact argv and environment growth over at least three dependency-free recursive levels, repeated `-C` ordering, and the point at which behavior changes. Keep it separate only if it does not invalidate the selected repair's stated scope.

## Stop rule

Do not call a repair ready until one exact final source head satisfies all of the following:

1. exact base and source identity retained;
2. losing baseline and final independent native characterization retained;
3. all temporary patch carriers apply without fuzz and disappear from the final commit;
4. final diff contains only intended product/test files;
5. clang-format passes;
6. sanitizer-enabled GCC build and native suite pass;
7. sanitizer-enabled Clang build and native suite pass;
8. standard final-head CI is inspected;
9. cleanup and immediate rerun evidence retained;
10. malformed, empty, repeated-option, pathname-byte, and legacy-backslash boundaries reviewed;
11. recursive option growth explicitly bounded;
12. formal review status recorded honestly;
13. overlap refreshed immediately before any authorized publication decision.

## First incomplete step

1. read the successor Linux Fieldwork runs created by this handoff commit;
2. require repository CI success and the exact native pass/fail split under both compilers;
3. read candidate bootstrap `30849580121` if it starts, but classify any green result as execution evidence only;
4. resolve the raw-backslash compatibility policy before materializing or selecting candidate source;
5. repair the temporary workflow's PR write-permission boundary;
6. keep final source, candidate experiment, native characterization, and recursive-growth successor as distinct identities;
7. update PRs #412, #1, and #2 with terminal receipts and exact heads.

If a job fails before its discriminator, repair only that carrier owner and rerun unchanged product logic.

## Cleanup

No local temporary configuration directory, helper process, module, mount, socket, lock, or persistent host configuration remains. Current state consists only of user-owned branches, internal draft PRs, retained evidence, and queued hosted execution.

## Authority

Linux Fieldwork PR #412 and kmod fork PRs #1 and #2 are internal user-owned review surfaces. No kmod-project issue, pull request, mailing-list post, email, comment, review, reaction, or other external contact is authorized or performed.
