# Handoff

## State

- Investigation: kmod nested `modprobe` configuration identity
- State: `EXECUTING`
- Linux Fieldwork branch: `investigation/kmod-modprobe-options-config-path`
- Linux Fieldwork base: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Exact technical head before this handoff update: `f4d082e77db4f840444d6cafde3cf3846f559f1d`
- Internal Linux Fieldwork draft PR: `teamleaderleo/linux-fieldwork#412`
- Owned kmod fork: `teamleaderleo/kmod`
- Native characterization PR: `teamleaderleo/kmod#1`
- Characterization branch/head: `test/modprobe-options-config-path@2e52d25e54a94fb531fd442079c7cf686f3e910b`
- Reserved clean repair branch: `fix/modprobe-options-config-path@5086df53090b2fe9fa1c31351c05a78a12a4ba71`
- Formal review submissions on PRs #412 and #1: none
- External-contact state: unauthorized; none made

## Current upstream and fork identity

- canonical repository: `https://git.kernel.org/pub/scm/utils/kernel/kmod/kmod.git`;
- source-reading mirror: `kmod-project/kmod`;
- exact public/fork base: `5086df53090b2fe9fa1c31351c05a78a12a4ba71`;
- owned-fork reserved repair branch is still identical to that base;
- relevant source: `tools/modprobe.c`;
- relevant functions: `env_modprobe_options_append()` and `prepend_options_from_env()`;
- intent/documentation commit: `42d60a3267162a36ec6b6b39a7b91e5078b90979`.

## Demonstrated package behavior

Debian `kmod 34.2-2` reproduces the policy split:

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

A manually quoted spaced path is a passing control. Leading/repeated spaces, tabs, and unmatched quotes silently lose the selected configuration while status remains 0. Root and EUID 65534 agree. No module insertion or removal occurs.

Retained identities:

```text
test SHA-256: 8006c8cb24ef44803565fb580bd9334edb807e210f3a5c0f313679f260c211c1
root result SHA-256: c6ffd6ac62937b2ceb78786fe3b7610b5125f91db356f1f747c69fe4fe8286bc
immediate rerun SHA-256: c6ffd6ac62937b2ceb78786fe3b7610b5125f91db356f1f747c69fe4fe8286bc
unprivileged result SHA-256: 759550141d24d03543d0686b235e82b0aab8015181b50bddb169e9d297acd9cf
```

## Hosted execution through run 30802150246

Repository CI `30802150076` passed at head `73338e82046f7eefb0b9a13f7cfe8e88ba2c82f7`.

Dedicated run `30802150246` produced four distinct outcomes:

1. **Exact master / GCC: success.** Exact public source built under ASan/UBSan, the unchanged package-style discriminator ran twice, normalized outputs matched byte-for-byte, the no-space case retained the selected configuration, and the spaced case lost it while both parent and child returned success.
2. **Exact master / Clang: harness failure after a successful build.** The executable could not start because `libclang_rt.asan-x86_64.so` was not on the runtime search path.
3. **Native characterization / GCC: harness failure.** Both paired tests attempted real module insertion and failed with `Operation not permitted` because the new test omitted `TC_INIT_MODULE_RETCODES`.
4. **Native characterization / Clang: the same native-test ownership defect, with Clang sanitizer handling also still requiring an explicit runtime contract.**

No failed job above refutes the package result or the successful exact-master GCC reproduction.

## Repairs now committed

### Owned native characterization

Head `2e52d25e54a94fb531fd442079c7cf686f3e910b` adds only:

```c
[TC_INIT_MODULE_RETCODES] = "",
```

to both paired tests. This matches kmod's existing `modprobe_install_cmd_loop` fixture and routes insertion through the suite's fake syscall layer. The source fence remains five test/fixture files and no product source.

### Linux Fieldwork execution carrier

Head `f4d082e77db4f840444d6cafde3cf3846f559f1d`:

- pins native characterization head `2e52d25...`;
- installs `libclang-rt-18-dev` for both matrices;
- uses `-Db_lundef=false` only for Clang sanitizer builds;
- exports Clang's resource-directory runtime path for direct exact-master execution;
- passes exact compiler identity into the native sanitizer wrapper;
- retains `-Dmbedtls=disabled` while OpenSSL, zstd, xz, and zlib remain enabled;
- adds `tests/test_kmod_modprobe_config_path_workflow.py` to lock exact source pins, optional-feature selection, Clang runtime handling, and the expected native pass/fail split.

Fresh runs:

- dedicated kmod workflow `30847691878`;
- Linux Fieldwork CI `30847692052`.

They were queued/in progress at the latest observation and are not yet product evidence.

## Native characterization contract

The paired fake-root fixture defines:

```text
alias lf_recursive_config_alias mod-loop-b
install mod-loop-a $MODPROBE --show-alias lf_recursive_config_alias
```

Expected unfixed result:

- `modprobe_options_config_path_control`: `PASSED`;
- `modprobe_options_config_path_space`: `FAILED`;
- no other native test failure;
- no real module insertion;
- no `tools/` or library diff.

## Overlap review

No matching open upstream issue or pull request was found for recursive `-C`, `MODPROBE_OPTIONS` pathname identity, or whitespace-bearing configuration paths. Upstream PR #139 discusses secure environment access generally, but it is not an implementation or duplicate of this defect.

Repeat overlap review immediately before any authorized public action.

## Candidate boundary

Do not put a quote-only repair on `fix/modprobe-options-config-path`. Valid pathnames can contain spaces, tabs, backslashes, single quotes, and double quotes; the current parser has no complete escape grammar.

Compare at least:

1. a complete encoder/decoder for internally generated `MODPROBE_OPTIONS` arguments;
2. a separate internal configuration-path transport that leaves legacy parsing unchanged;
3. a bounded parser rewrite with explicit compatibility tests.

A selected candidate must preserve no-space behavior, pathname identity, repeated `-C` order, `-s`/`-q`/`-v` propagation, two recursive levels, malformed-data failure, and no real module insertion in focused tests.

## First incomplete step

1. inspect all jobs and artifacts from `30847691878` and repository CI `30847692052`;
2. require both exact-master compiler jobs to reproduce the package split without sanitizer findings;
3. require both native jobs to show exactly one passing no-space control and one losing spaced-path discriminator;
4. retain exact binary, log, source, artifact, and digest identities;
5. only then begin separate transport-candidate experiments while keeping `fix/modprobe-options-config-path` clean.

If a job still fails before its discriminator, repair only that carrier owner and rerun unchanged product logic.

## Cleanup

All local temporary configuration directories, helper scripts, nested outputs, and receipts were removed. Current work consists of user-owned Git branches, draft PRs, and hosted read-only execution. No module, process, mount, socket, lock, or persistent host configuration remains.

## Authority

Linux Fieldwork PR #412 and owned-fork PR #1 are internal user-owned surfaces. No kmod-project issue, pull request, email, mailing-list post, comment, review, reaction, or other external contact is authorized or performed.
