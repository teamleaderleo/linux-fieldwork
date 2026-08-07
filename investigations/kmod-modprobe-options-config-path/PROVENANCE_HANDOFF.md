# Provenance-aware recursive option handoff

## State

- Investigation: recursive `modprobe` configuration identity and adjacent empty-environment allocation correctness
- Disposition: `HOLD — recursive defect proven on current master; original fallback carrier exhausted under bounded recovery; allocator repair independently validated`
- Linux Fieldwork branch: `investigation/kmod-modprobe-options-config-path`
- Linux Fieldwork technical head before this handoff update: `3ead37769d58f1f94e78b9c6adf9988c6b8d30ba`
- Linux Fieldwork draft PR: `teamleaderleo/linux-fieldwork#412`
- Native characterization: `teamleaderleo/kmod#1@84ba8ae9db4f455965efa22afdd5cb177781106b`
- Provenance fallback experiment: `teamleaderleo/kmod#5@3bdcf36edfa04e217d67e0aa0570349b6f449eaf`
- Empty-environment allocation repair: `teamleaderleo/kmod#6@9dbb2701a2fcf96280a99b8d2ebcb4b0451be6b3`
- Formal reviews: none
- External contact: unauthorized; none made

## Source freshness

The original exact execution base was:

```text
kmod master: 5086df53090b2fe9fa1c31351c05a78a12a4ba71
modprobe.c:  413960cae0f39945a3f2d6509dc4a8c262ae2609
```

Exact upstream master used for the final refresh is:

```text
kmod master: dae6c02ffed2e8d16da8dba16d974fc955eebb1f
modprobe.c:  c4b5021137a01529d75d9979e262308ce371bbae
```

Source review and exact execution both show the relevant mechanisms remain present on that August 6, 2026 head:

- `env_modprobe_options_append()` still flattens option values into the single `MODPROBE_OPTIONS` string;
- `prepend_options_from_env()` still uses the old pointer-array allocation expression, copies `envlen + 1`, and uses the same space/quote parser.

Final exact-current refresh:

```text
workflow: .github/workflows/kmod-current-master-refresh.yml
run:      31143700852
GCC job:  92758721115
Clang job:92758721114
```

Both jobs passed exact source identity, ASan/UBSan build, two runs of the recursive configuration discriminator, the required explicit-empty ASan failure, cleanup, and artifact upload.

Artifacts:

```text
GCC:   8980706391  sha256:196244ac10e4ff7e2274b2e9ebd2a8a4d60eb841070ec2b6dc4eb6b2b52a32d8
Clang: 8980707642  sha256:0865ccc0ba4e5b32d26a91a34d839191b3409b55af038006bbf22d361e504d39
```

## Closed recursive-configuration baseline

Final native characterization run `30850597196` completed successfully under GCC and Clang sanitizers.

Both compiler jobs observed exactly:

```text
FAILED: modprobe_options_config_path_space
PASSED: modprobe_options_config_path_control
```

Package-style and exact-source behavior remains:

```text
no-space configuration path: parent/nested marker counts 1/1
spaced configuration path:   parent/nested marker counts 1/0
parent status: 0
nested status: 0
```

The current-master refresh reproduced that discriminator twice under both compilers. The parent uses the requested configuration. An `install` command starts another `modprobe`; the parent serializes `-C` and its raw pathname into `MODPROBE_OPTIONS`; the child reparses a changed argument vector and can silently use another configuration.

No unrelated failure, dirty fake-root state, loaded-module residue, or sanitizer finding occurred in the recursive characterization.

## Transport design review

### V1 — legacy parser rewrite held

PR #2 changes raw-backslash behavior and does not bound recursive option growth. It remains execution history, not selected source.

### Narrow exact-record V2 held

PR #3 carries only generated `-C/-s/-q/-v` state. A reversing inherited-`-d` control proved current kmod can preserve additional private options that this design drops.

### Strict provenance rejected

PR #4 separates inherited state from exact generated state, but rejects an install script that mutates `MODPROBE_OPTIONS` by appending `-q`. Current kmod accepts that mutation for representable legacy values, so strict mismatch rejection is not recursively equivalent.

### Provenance fallback experiment — original carrier recovery closed

PR #5 records a bounded fallback policy after exact metadata validates:

1. compare the actual legacy mirror with the expected inherited-plus-generated mirror;
2. when an install script changed the mirror, rebase the actual string as inherited state;
3. clear the exact generated suffix;
4. parse the rebased inherited state with the unchanged legacy parser;
5. publish it once to avoid later duplication;
6. continue to reject malformed exact/base records and positional exact records.

Its committed discriminator additionally requires pure CLI-origin base length `0`, byte-stable `(base_len, exact_len, legacy_len)` tuples through three recursive levels, inherited private-option retention, successful install-script `-q` mutation, representable new-parent/old-child behavior, honest old-parent/new-child loss, and visible failure for unrepresentable old-child handoff.

Local GCC 14.2 and Clang 17 ASan/UBSan multicall builds passed spaced recursive `-C` through three dependency-free levels, inherited `-d`, install-script `-q` mutation, repeated and clustered options, representable mixed-version direction, and safe malformed-state boundaries. That remains useful design history, not hosted source provenance.

The original hosted recovery run was:

```text
head:  94c42b0374c5b668eaf8f31a8daf79da1b268be0
run:   31047684477
GCC:   92447161754
Clang: 92447161730
```

The committed Base64 carrier matched its pinned digest. Decompression produced output despite gzip CRC/length errors, but both jobs failed before source execution at:

```text
error: corrupt patch at .../fallback.patch:889
```

`git apply --check` never succeeded; formatting, build, native tests, and the fallback discriminator were skipped.

#### Carrier provenance and localization

Branch history shows carrier-introduction commit `b13cebe88975595773ce6816e2aa7ebc5b0e22f6` added the already-damaged Base64 payload directly on exact base `5086df...`. Every later PR #5 commit before diagnostics changed only tests/workflows. There is no earlier clean fallback payload in branch history.

The decoded patch contains 29 diff sections:

- sections 1–28 individually pass `git apply --recount --check`;
- section 29, `tools/modprobe.c`, is corrupt;
- its content is byte-identical to clean strict PR #4 through local diff line 469;
- corruption begins immediately after the final intact `option_transport_clear(&selected);` transition;
- later hunk offsets show the fallback main hunk is net eight added lines longer than strict PR #4, but the decoded bytes are broadly mangled, so the net line delta cannot establish exact source.

Clean strict PR #4 is independently pinned by:

```text
uncompressed patch sha256: caed53a3a7f5dc57f2d4114da21a623dfd9ea1343881bdced3617adf30ecee32
gzip sha256:              ae01646901a5bc8305a4869446344022e21be420414ab6074fa1e2a7a5be75bd
```

#### Gzip exactness oracle

The original fallback gzip trailer remains internally useful:

```text
gzip bytes:              6434
trailer CRC32:            23be8cfa
trailer ISIZE:            36682
recovered output bytes:   36704
recovered output CRC32:   50dc6748
```

A byte-exact recovery claim must reproduce size `36,682` and CRC32 `23be8cfa`, then pass `git apply --check` and the exact 29-path fence.

#### Bounded byte-level recovery results

Every bounded small-corruption model tested returned zero candidates matching the original CRC32/ISIZE:

1. single bit anywhere — run `31144903377`;
2. arbitrary single decoded byte anywhere — run `31145103754`, including `1,636,080` full-payload substitutions;
3. one Base64 character substitution anywhere — run `31145253016`, `540,477` substitutions;
4. arbitrary adjacent two-byte replacement near mapped compressed offset `5354` — run `31145342454`, `4,259,775` substitutions across 65 pair starts;
5. two independent bit flips across 129 nearby bytes — run `31145625437`, job `92764337808`, `528,384` candidates.

The final two-bit receipt is artifact `8981366890`, ZIP SHA-256 `4e65b2b9831d3207f963b298c69b0f5f5cf1397a19d5c3b4d94ded5a77840fbf`.

These negative searches do not establish impossibility for arbitrary multi-byte damage. They close the economically bounded, high-probability carrier-repair models. Continuing brute-force recovery would be a poor provenance tradeoff.

PR #5 final head `3bdcf36edfa04e217d67e0aa0570349b6f449eaf` therefore keeps a lightweight read-only characterization rather than pretending to validate product source:

```text
workflow: Characterize damaged provenance fallback carrier
run:      31145763781
job:      92764744393
result:   success
artifact: 8981406622
sha256:   3e6124f16d17a7e2139fdbbccd6ef48fd782adba1587ed9c46dd0de0c371b02a
```

That gate requires exact base/carrier identity, the pinned trailer/recovered metrics, failed normal and recount application, exactly 28 valid sections plus the corrupt tools section, and a clean tree. It intentionally performs no product build/test.

Do not treat decoded PR #5 bytes as candidate source. A future fallback implementation should be a **reconstructed successor** from clean strict PR #4 plus the documented fallback policy and committed discriminator. It must be labeled reconstructed unless its complete patch independently reproduces the original gzip trailer and all patch/fence checks.

The fallback limitation remains: pathname identity cannot be recovered after an old parent has already flattened an unrepresentable value.

## Separate empty `MODPROBE_OPTIONS` allocation defect

When `MODPROBE_OPTIONS` exists but is empty, exact `prepend_options_from_env()` calculates no independent string storage and then copies the terminating NUL. The old base and exact August 6 current master reproduce under both GCC and Clang ASan:

```text
AddressSanitizer: heap-buffer-overflow
WRITE of size 1
```

The ordinary non-sanitized Debian binary still exits successfully. No exploitability or security-severity claim is made.

### Final allocator candidate

PR #6 keeps product source uncommitted and carries one exact two-file patch plus a read-only validator. The candidate:

- calculates pointer count and pointer bytes independently;
- calculates `envlen + 1` string bytes independently;
- uses checked multiplication/addition;
- leaves the legacy parser and raw-backslash behavior unchanged;
- adds a native `MODPROBE_OPTIONS=""` test using `modprobe --version`.

Exact carrier identity:

```text
head:         9dbb2701a2fcf96280a99b8d2ebcb4b0451be6b3
patch blob:   08612258b78b1b0529bf2bc999ac88d1df21cb94
patch sha256: eb043a8ba8579353723da0c68987cbccf86cb4b492278e4791016602f727a07d
file fence:   testsuite/test-modprobe.c tools/modprobe.c
```

Final old-base gate:

```text
run:   31143505815
GCC:   92758131800
Clang: 92758131757
```

Both jobs first reproduced the exact unmodified ASan loss, then passed patch application, exact two-file fence, clang-format, sanitizer build, direct explicit-empty success, focused `test-modprobe`, complete native suite, cleanup, and receipt upload.

Artifacts:

```text
GCC:   8980651971  sha256:515b97bffeb84e8d300791ea363691b07497eed3aea592b179317663fb1eeb16
Clang: 8980648324  sha256:f0d247ffaed4233332f8e41b0feaa1ff29dbdcabd76828b2a8ee5d1063d69f63
```

### Exact current-master candidate gate

The same final carrier applies directly to exact August 6 upstream master `dae6c02ffed2e8d16da8dba16d974fc955eebb1f` and passes:

```text
workflow: .github/workflows/kmod-current-master-empty-candidate.yml
run:      31143700889
GCC job:  92758721094
Clang job:92758721113
```

Both jobs passed exact source/carrier identity, patch application and two-file fence, formatting, sanitizer build, direct explicit-empty execution, focused `test-modprobe`, complete native suite, recursive scope control, cleanup, and receipt upload.

Artifacts:

```text
GCC:   8980711844  sha256:927aa6e2889e1a0c0126446998c9d1438f9f50761e753dc23901eab679068a51
Clang: 8980710940  sha256:387384f4671c049b5bed2c58930d13949d922774f61325a5947cb6b8fe1b4d65
```

The recursive scope control still shows the independent no-space `1/1` versus spaced-path `1/0` split.

One earlier current-master Clang generation failed after a successful build because the workflow left `CC` unset during Meson tests. `scripts/sanitizer-env.sh` assumed GCC and preloaded GCC ASan into a Clang-ASan binary. A workflow-only correction exported the matrix compiler; the pinned upstream source and allocator patch stayed unchanged, and the corrected run above is green.

### Standard final-head CI

At PR #6 head `9dbb2701a2fcf96280a99b8d2ebcb4b0451be6b3`, all observed standard fork CI is green:

- clang-format: `31143505841`;
- Build and Test: `31143505824`;
- Code Coverage: `31143505830`;
- CodeQL: `31143505832`;
- codespell: `31143505820`;
- dedicated allocator validation: `31143505815`.

The allocator repair is independently validated on the original exact base and exact current upstream head. It does not require choosing a recursive transport policy.

## Overlap refresh

Read-only upstream searches on 2026-08-07 found no open matching issue or pull request across these variants:

- `MODPROBE_OPTIONS`;
- `prepend_options_from_env`;
- `empty MODPROBE_OPTIONS`;
- `heap-buffer-overflow modprobe`;
- `modprobe -C whitespace`.

The broader `modprobe config path` issue search returned only issue #349 about `--force` test coverage, unrelated to these defects.

Search wording can miss differently described work. Refresh immediately before any authorized public action.

## Stop rule

Do not select or publish a recursive transport repair until:

1. any continued fallback implementation is introduced as a reconstructed successor from a clean provenance base;
2. its exact source/fence is retained independently of the damaged PR #5 carrier;
3. the reconstructed successor passes formatting, GCC/Clang sanitizer builds, focused reruns, complete suite, and the committed fallback discriminator;
4. mixed-version and install-script mutation limitations remain documented honestly;
5. no temporary carrier remains in a selected source diff;
6. standard final-head CI is inspected;
7. overlap, contribution policy, and formal review state are refreshed.

Do not label a successor as byte-exact PR #5 recovery unless its complete patch reproduces the original fallback trailer `(ISIZE=36682, CRC32=23be8cfa)` and passes the expected patch/fence checks.

The allocator lane has cleared its technical gates. Product source remains uncommitted, so any next allocator step should be a clean source-only owned-fork candidate or an explicitly retained patch-only handoff. Upstream publication still requires separate authorization.

## First incomplete steps

1. If continuing the recursive lane, create a reconstructed successor from clean strict PR #4 plus the documented fallback policy and committed discriminator; do not reuse damaged PR #5 source bytes.
2. Run that successor through exact fencing, formatting, GCC/Clang sanitizers, focused suite twice, complete suite, fallback discriminator, cleanup, and standard final-head CI.
3. For the allocator lane, consider a clean source-only owned-fork candidate based on the validated two-file patch.
4. Refresh overlap and formal-review state immediately before any promotion decision.
5. Do not contact upstream without explicit authorization.
