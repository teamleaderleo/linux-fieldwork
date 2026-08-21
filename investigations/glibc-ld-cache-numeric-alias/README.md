# glibc ld.so.cache numeric-name alias identity

State: `reproduced on Ubuntu Noble; current-head execution pending`

Owning issue: #502  
Evidence PR: #527  
External contact: `false — unauthorized`

## TL;DR

Ubuntu Noble glibc reproduces a byte-identity ambiguity in `ld.so.cache` lookup. `ldconfig` can retain byte-distinct SONAME keys such as `libalias.so.1` and `libalias.so.01`, while the loader groups those keys through the numeric comparator `_dl_cache_libcmp`.

In the retained fixture, requests for `libalias.so.1`, `libalias.so.01`, and even absent `libalias.so.001` all selected the **same** cached implementation. Reversing only configured directory order flipped all three requests from marker `101` to marker `202`. A comparator-distinct `.2` request remained missing and the control pair stayed exact.

A fresh sourceware-origin mirror at `gnutools/glibc@6288139c32a194e0005593c30af6c79bb698cdf2`, carrying commits through 2026-08-09, still uses the same comparator-equivalence predicate in `elf/dl-cache.c`. Current-head behavior is source-supported but remains unexecuted until the same fixture runs against a current build.

## Explain like I'm five

The cache sorts numbered library names as numbers. `1`, `01`, and `001` have the same numeric value. The loader also uses that sorting comparison to decide whether a requested name is the same cache key.

That means asking for a spelling that does not exist can still open a library whose cached name only compares numerically equal. When two such names exist, directory order can decide which library both spellings open.

## Why care

Dynamic-library lookup is an identity boundary. Natural numeric ordering is useful for cache sorting, while byte-level SONAME identity is a separate property.

The demonstrated consequence is narrow and concrete: enabling the cache can broaden the identity of a requested library name, and comparator-equivalent entries can become order-dependent. This investigation does not claim privilege escalation, a deployed compromise, or a production exploit path.

## Exact source boundary

### Current source

Current source was rechecked on 2026-08-10 against the fresh sourceware-origin mirror:

- repository: `gnutools/glibc`;
- exact commit: `6288139c32a194e0005593c30af6c79bb698cdf2`;
- mirror carries sourceware-origin commits through 2026-08-09.

Relevant files:

- `elf/dl-cache.c::search_cache` and `_dl_cache_libcmp`;
- `elf/cache.c::{compare,add_to_cache}`;
- `elf/ldconfig.c::search_dir`;
- `elf/dl-is_dso.h`;
- `elf/dl-load.c` cache lookup path.

Historical reference:

- glibc commit `686dfcd106e96e3f991cec76c8d0e434cf97fe54` changed cache lookup from `strcmp` to `_dl_cache_libcmp` in 1999.

An older GitHub code-search mirror used during orientation was later found stale and is not treated as current-head evidence.

### Source observations

1. Cache binary search treats `_dl_cache_libcmp(requested_name, cached_key) == 0` as name equality.
2. Decimal runs are accumulated and compared numerically, so leading-zero spellings can compare equal.
3. Directory collection deduplicates SONAMEs with exact `strcmp`, so byte-distinct SONAMEs remain distinct before cache insertion.
4. `add_to_cache` interns the exact SONAME and inserts a cache entry; comparator equality is used for ordering, not deduplication.
5. Ordinary `lib*.so*` names are admitted by the DSO filename heuristic.
6. The cache lookup returns one selected pathname to the loader; the inspected load path does not later require the opened object's SONAME spelling to equal the original requested cache key byte-for-byte.
7. The Aug 9 current source has newer cache-file reload logic, but the matching predicate remains comparator equality.

## Fixture

`probe.sh` creates two private chroot roots from one tiny runtime:

- directory A contains a DSO whose SONAME is `libalias.so.1` and whose marker returns `101`;
- directory B contains a DSO whose SONAME is `libalias.so.01` and whose marker returns `202`;
- comparator-distinct controls use `libcontrol.so.1` → `301` and `libcontrol.so.2` → `302`.

One root configures A before B; the other configures B before A. Each root gets its own `ldconfig`-generated `/etc/ld.so.cache`. The test process runs inside that private root through copied host loader/runtime files, so host `/etc/ld.so.cache` is never replaced or edited.

Queries per root:

- `libalias.so.1`;
- `libalias.so.01`;
- absent but comparator-equivalent `libalias.so.001`;
- comparator-distinct absent `libalias.so.2`;
- `libcontrol.so.1`;
- `libcontrol.so.2`.

## Executed result

### Exact retained run

- fieldwork branch head carrying the hardened probe: `42c3ac5d69112ab5c44b91558a5bcbf9a7e16fe7`;
- pull-request merge ref executed by Actions: `5587ac53d41901c89f1e928854f3fdda455839c7`;
- workflow run: `31346113352`;
- job: `93328265706`;
- artifact: `9047380783` (`glibc-cache-numeric-alias-gha-31346113352-1`);
- artifact ZIP SHA-256 reported by Actions: `0be9f851f908d6ca69b12f4ca135762f00c73f9506754cc6eeed8d9f90cd2614`;
- environment: GitHub-hosted `ubuntu-24.04`, image `20260720.247.2`, Ubuntu 24.04.4, x86_64, runner 2.336.0.

The workflow pins checkout to `11d5960a326750d5838078e36cf38b85af677262`, pins upload-artifact to `ea165f8d65b6e75b540449e92b4886f43607fa02`, grants read-only repository permission, and removes the ephemeral checkout credential after fetch with `persist-credentials: false`.

### Observed table

```text
root  request             result
ab    libalias.so.1       101
ab    libalias.so.01      101
ab    libalias.so.001     101
ab    libalias.so.2       MISSING
ab    libcontrol.so.1     301
ab    libcontrol.so.2     302
ba    libalias.so.1       202
ba    libalias.so.01      202
ba    libalias.so.001     202
ba    libalias.so.2       MISSING
ba    libcontrol.so.1     301
ba    libcontrol.so.2     302
classification            alias_identity_reproduced
```

### What the run demonstrates

- `libalias.so.001` was never present as a file or SONAME, yet `dlopen("libalias.so.001")` resolved through the generated cache.
- Exact requests for `.1` and `.01` did not independently select their exact SONAME entries inside the cache.
- Reversing only configured directory order changed the selected implementation for all comparator-equivalent spellings.
- The comparator-distinct absent `.2` request remained missing.
- The comparator-distinct control libraries selected their own markers in both roots.

The first implementation-head run (`31345618162`, job `93326878341`, artifact `9047331932`) produced the same semantic table. Its checkout retained the ephemeral read-only Actions credential in local Git configuration until post-job cleanup; that harness-hygiene issue was corrected before the exact retained run above.

## Candidate repair boundary

The narrow candidate is to keep `_dl_cache_libcmp` for cache ordering and for locating the comparator-equivalent range, but require exact byte-string key equality when choosing entries inside that range. Architecture/HWCAP preference would then apply only among exact-key matches.

This avoids changing natural numeric ordering for cache generation while restoring the distinction between ordering equivalence and library-name identity.

Before recommending that change upstream, execute it against a current Aug 9 glibc build and check:

- exact `.1` versus `.01` selection;
- absent `.001` remains missing;
- ordinary numeric ordering remains unchanged;
- duplicate exact SONAME entries in different directories retain existing directory preference;
- named HWCAP selection still applies correctly within an exact SONAME group;
- cache-free lookup remains the negative control;
- existing elf/ldconfig and HWCAP tests remain green.

## Adjacent comparator question

`_dl_cache_libcmp` still accumulates arbitrarily long decimal runs into signed `int` and returns signed differences. Ordinary Linux DSO names can contain numeric runs long enough to exceed that domain.

That is a separate invariant from the leading-zero identity result: the comparator must remain a stable total ordering for both cache generation and binary lookup. Do not merge it into the demonstrated alias claim until a standalone comparator and end-to-end cache fixture establish the actual behavior under the glibc build flags.

## Safety and cleanup

- no host `/etc/ld.so.cache` write or bind mount;
- no package installation;
- no network access from the probe after checkout;
- no real credentials or host-private input;
- every generated file lives under one `mktemp` root;
- `ldconfig -r` and `chroot` use GitHub-hosted disposable sudo only against that exact root;
- cleanup removes only the exact private root created by the run.

## Evidence boundary

The hosted run establishes Ubuntu Noble glibc behavior for the exact runner image and synthetic DSOs. Current Aug 9 glibc source retains the same matching rule, but current-head execution is still pending.

The demonstrated effect is cache-name identity ambiguity and directory-order-dependent DSO selection. No claim is made about a deployed application, privilege boundary, or exploitability beyond that behavior.

## Next action

Build `gnutools/glibc@6288139c32a194e0005593c30af6c79bb698cdf2` in disposable CI and run the same fixture against that loader/cache implementation. If it reproduces, add a focused glibc regression and a minimal exact-key candidate, then perform a separate bounded check for the signed-integer comparator domain.
