# Handoff

## State

- Investigation: kmod nested modprobe configuration identity
- State: `EXECUTING`
- Linux Fieldwork branch: `investigation/kmod-modprobe-options-config-path`
- Linux Fieldwork base: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Exact carrier repair head before this handoff update: `448d9c294cf328c9200160fbbd33fb9ef441683a`
- Internal draft PR: #412
- Owned kmod fork: `teamleaderleo/kmod`
- Reserved clean candidate branch: `fix/modprobe-options-config-path`
- External-contact state: unauthorized; none made

## What exists

- kmod target map and registry entry;
- durable investigation record and deterministic package-level probe;
- root, EUID 65534, quoted-control, parser-control, cleanup, and immediate-rerun receipts;
- exact-master GCC/Clang sanitizer execution workflow at `.github/workflows/kmod-modprobe-config-path.yml`;
- a user-owned kmod fork whose `master` and `fix/modprobe-options-config-path` branch are still identical to exact upstream commit `5086df53090b2fe9fa1c31351c05a78a12a4ba71`.

No product or native-test commit has yet been placed on the reserved fork branch.

## Exact upstream identities

- Canonical repository: `https://git.kernel.org/pub/scm/utils/kernel/kmod/kmod.git`
- Source-reading mirror: `https://github.com/kmod-project/kmod.git`
- Exact mirror master under test: `5086df53090b2fe9fa1c31351c05a78a12a4ba71`
- Current mirror master rechecked 2026-08-03: unchanged at `5086df53090b2fe9fa1c31351c05a78a12a4ba71`
- Relevant source: `tools/modprobe.c`
- Relevant functions: `env_modprobe_options_append()` and `prepend_options_from_env()`
- Intent/documentation commit: `42d60a3267162a36ec6b6b39a7b91e5078b90979`
- Current local executable: Debian `kmod 34.2-2`, `/usr/sbin/modprobe`
- Local executable SHA-256: `a775c12b9d71d9548654ff98ecc0e5e3378bdaccd52ccb62fa80a5f41e849caf`

## Latest demonstrated package result

```text
no-space config:
  direct marker=1
  parent status=0
  nested status=0
  nested marker=1

spaced config:
  direct marker=1
  parent status=0
  nested status=0
  nested marker=0
  MODPROBE_OPTIONS=-C $TMP/space/conf dir
```

A manually quoted spaced path is a passing control. Leading/repeated spaces, tabs, and unmatched quotes silently lose the selected configuration while status remains 0. Root and EUID 65534 agree. No module insertion or removal occurs.

## Exact retained evidence

```text
test SHA-256: 8006c8cb24ef44803565fb580bd9334edb807e210f3a5c0f313679f260c211c1
root result SHA-256: c6ffd6ac62937b2ceb78786fe3b7610b5125f91db356f1f747c69fe4fe8286bc
immediate rerun SHA-256: c6ffd6ac62937b2ceb78786fe3b7610b5125f91db356f1f747c69fe4fe8286bc
unprivileged result SHA-256: 759550141d24d03543d0686b235e82b0aab8015181b50bddb169e9d297acd9cf
```

## Exact-master carrier history

Run `30759642216` reached exact source identity successfully in both GCC and Clang jobs, then stopped during Meson configuration before compiling product code.

The first clear owner was an optional dependency mismatch:

```text
Dependency mbedx509 found: 2.28.8
kmod requirement: >= 3.6.0
```

Ubuntu 24.04 supplies Mbed TLS 2.28.8. This is carrier configuration, not kmod behavior. Source identity and cleanup checks passed; no discriminator ran.

Carrier head `448d9c294cf328c9200160fbbd33fb9ef441683a` removes the unavailable development package and configures exact kmod with `-Dmbedtls=disabled`. OpenSSL, zstd, xz, and zlib remain enabled. This is an optional-backend adjustment only; no kmod source is patched.

Fresh run `30801421368` was queued at the latest observation. No queued run is treated as a result.

## Fork and overlap review

- `teamleaderleo/kmod` is a writable public fork controlled by the repository owner.
- `master` equals upstream `master@5086df53090b2fe9fa1c31351c05a78a12a4ba71`.
- `fix/modprobe-options-config-path` exists but is identical to `master`.
- no pull request exists in the owned fork;
- no matching open upstream issue was found for `MODPROBE_OPTIONS`, recursive `-C`, or whitespace-bearing configuration paths;
- no matching upstream pull request was found;
- upstream PR #139 only discusses secure environment access generally and is not an implementation or duplicate of this pathname-identity defect.

These are search results, not proof that differently worded prior art does not exist. Repeat overlap review before any public action.

## Candidate design boundary

Do not commit a partial quote-only repair to the clean fork branch. A valid Linux pathname may contain spaces, tabs, backslashes, single quotes, and double quotes. The current parser has no general escape grammar, so wrapping the path in one quote style is incomplete.

The next candidate comparison should include at least:

1. a complete encoder/decoder for internally generated `MODPROBE_OPTIONS` arguments;
2. a separate internal configuration-path transport that leaves legacy external parsing unchanged;
3. a bounded parser rewrite with explicit compatibility controls.

Each candidate must preserve:

- ordinary no-space behavior;
- arbitrary non-NUL pathname bytes representable in an environment string;
- repeated `-C` ordering;
- existing `-s`, `-q`, and `-v` propagation;
- recursion through more than one install/remove layer;
- caller-visible failure for malformed internally generated data;
- no module insertion in the focused test.

## First incomplete step

Read exact-master run `30801421368` when terminal.

- If both compiler jobs reproduce the loss without sanitizer findings, retain job/artifact identities and implement the native `testsuite/test-modprobe.c` discriminator on a separate characterization branch in `teamleaderleo/kmod`.
- Keep `fix/modprobe-options-config-path` clean until the characterization loses on exact master and the candidate matrix selects a complete transport.
- If setup/build fails, repair only the dependency or workflow owner and rerun unchanged product logic.
- If source behavior differs, preserve the exact result and reclassify the current-source boundary before changing a candidate.

After exact-master execution:

1. add the native fake-root regression;
2. prove the exact master loses;
3. compare complete transport candidates, including spaces, both quote characters, backslashes, tabs, repeated `-C`, existing environment content, and two recursive levels;
4. run GCC and Clang sanitizer builds;
5. retain cleanup, rerun, exact diff, job, and artifact identities;
6. repeat current upstream overlap review before any publication decision.

## Cleanup

All local temporary configuration directories, helper scripts, nested outputs, and receipts were removed. The current work is hosted read-only execution machinery plus documentation. No process, module, mount, socket, lock, or persistent host configuration remains.

## Authority

PR #412, the Linux Fieldwork workflow, and writes to `teamleaderleo/kmod` are internal user-owned surfaces. No kmod-project issue, pull request, email, mailing-list post, comment, review, reaction, or other external contact is authorized or performed.
