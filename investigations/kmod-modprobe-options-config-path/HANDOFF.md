# Handoff

## State

- Investigation: kmod nested `modprobe` configuration identity
- State: `EXECUTING`
- Linux Fieldwork branch: `investigation/kmod-modprobe-options-config-path`
- Linux Fieldwork base: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Exact workflow head before this handoff update: `f7fc35ba32718a289546c8621e38abfbd62daa8a`
- Internal Linux Fieldwork draft PR: `teamleaderleo/linux-fieldwork#412`
- Owned kmod fork: `teamleaderleo/kmod`
- Native characterization PR: `teamleaderleo/kmod#1`
- Characterization branch/head: `test/modprobe-options-config-path@d59bf6473c8619fb695a51e2c2e69cdec20b31e7`
- Reserved clean repair branch: `fix/modprobe-options-config-path@5086df53090b2fe9fa1c31351c05a78a12a4ba71`
- External-contact state: unauthorized; none made

## Current upstream and fork identity

- canonical repository: `https://git.kernel.org/pub/scm/utils/kernel/kmod/kmod.git`;
- source-reading mirror: `kmod-project/kmod`;
- mirror `master` rechecked 2026-08-03: `5086df53090b2fe9fa1c31351c05a78a12a4ba71`;
- owned-fork `master`: the same commit;
- owned-fork reserved repair branch: the same commit, with no source changes;
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

## Exact-master carrier repair

Run `30759642216` verified exact source identity in both compiler jobs, then failed before compiling kmod because Ubuntu 24.04 provides Mbed TLS 2.28.8 while this kmod revision requires `mbedx509 >= 3.6.0` when that optional backend is enabled.

That is carrier configuration, not product evidence. The workflow now:

- omits the unavailable Mbed TLS development package;
- passes `-Dmbedtls=disabled`;
- leaves OpenSSL, zstd, xz, and zlib enabled;
- builds exact upstream source with GCC and Clang under ASan/UBSan;
- runs the unchanged package discriminator twice;
- requires byte-identical normalized results, cleanup, and an unchanged source tree.

Runs `30801421368` and `30801555550` were superseded by later branch updates under branch-scoped concurrency. A cancelled run is not evidence.

## Native characterization carrier

The owned fork previously contained no PR and no source change. The new draft PR `teamleaderleo/kmod#1` adds a five-file, product-source-free native characterization:

- `testsuite/test-modprobe-options.c`;
- `testsuite/meson.build` registration;
- a no-space control configuration at `/etc/modprobe-config`;
- an otherwise identical spaced configuration at `/etc/modprobe config`;
- shared expected output `mod-loop-b`.

Both configurations define:

```text
alias lf_recursive_config_alias mod-loop-b
install mod-loop-a $MODPROBE --show-alias lf_recursive_config_alias
```

The test requires:

```text
modprobe -C /etc/modprobe-config mod-loop-a
```

to pass, and the otherwise identical quoted spaced-path invocation to produce the same result. On the unfixed base, the expected discriminator is:

- `modprobe_options_config_path_control`: pass;
- `modprobe_options_config_path_space`: fail.

Complete diff review found and repaired one test-only issue before execution: the standalone test now includes `<stdlib.h>` for the suite's `EXIT_*` macro path. Product source remains unchanged.

## Final hosted gate at the handoff boundary

The Linux Fieldwork workflow now contains two independent GCC/Clang matrices:

1. exact upstream source, package-style discriminator, ASan/UBSan;
2. exact characterization head `d59bf647...`, native fake-root test, ASan/UBSan.

The native job verifies the five-file fence and no `tools/` changes, then requires exactly one passing control and exactly one losing spaced-path test. It rejects unrelated native failures and uploads exact source, binary, log, status, and digest receipts.

This handoff update itself triggers the final exact-head workflow generation. No queued, pending, cancelled, or uninspected run is treated as a result.

## Overlap review

No matching open upstream issue or pull request was found for recursive `-C`, `MODPROBE_OPTIONS` pathname identity, or whitespace-bearing configuration paths. Upstream PR #139 discusses secure environment access generally, but it is not an implementation or duplicate of this defect.

Searches can miss differently worded or unindexed work. Repeat overlap review immediately before any public action.

## Candidate boundary

Do not put a quote-only repair on `fix/modprobe-options-config-path`. Valid pathnames can contain spaces, tabs, backslashes, single quotes, and double quotes; the current parser has no complete escape grammar.

Compare at least:

1. a complete encoder/decoder for internally generated `MODPROBE_OPTIONS` arguments;
2. a separate internal configuration-path transport that leaves legacy parsing unchanged;
3. a bounded parser rewrite with explicit compatibility tests.

A selected candidate must preserve no-space behavior, arbitrary non-NUL pathname bytes representable in the environment, repeated `-C` order, `-s`/`-q`/`-v` propagation, two recursive levels, malformed-data failure, and no module insertion in the focused tests.

## First incomplete step

1. fetch workflow runs associated with the final handoff commit;
2. inspect every exact-master and native-characterization job and artifact;
3. if both compiler matrices show the expected product split without sanitizer findings, retain exact receipts and begin the transport-candidate matrix on separate experimental branches;
4. keep `fix/modprobe-options-config-path` clean until one complete design wins;
5. if a job fails before the discriminator, repair only its carrier owner and rerun unchanged product logic.

## Cleanup

All local temporary configuration directories, helper scripts, nested outputs, and receipts were removed. Current work consists of user-owned Git branches, draft PRs, and hosted read-only execution. No module, process, mount, socket, lock, or persistent host configuration remains.

## Authority

Linux Fieldwork PR #412 and owned-fork PR #1 are internal user-owned surfaces. No kmod-project issue, pull request, email, mailing-list post, comment, review, reaction, or other external contact is authorized or performed.
