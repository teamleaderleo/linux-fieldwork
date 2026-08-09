# glibc `ld.so.cache` numeric-name identity

## TL;DR

Current glibc can place two byte-distinct SONAMEs in `ld.so.cache` and then treat them as one lookup identity when `_dl_cache_libcmp` considers their numeric components equal. A disposable glibc 2.41 x86_64 fixture reproduced both a leading-zero pair (`libalias.so.1` / `libalias.so.01`) and a wide-decimal pair (`libwide.so.1` / `libwide.so.4294967297`): cache-backed lookup collapses the pair onto one DSO, while bypassing the cache loads each exact requested SONAME.

The immediate next gate is the same no-network fixture on Ubuntu Noble glibc 2.39. The first candidate boundary should preserve the historical cache sort contract while requiring byte-exact key identity inside the comparator-equivalent group. Comparator overflow deserves a second compatibility-aware correction because changing the cache ordering outright can invalidate already-generated caches.

## Explain like I'm five

Linux keeps an index of shared libraries so programs can find them quickly. The index sorts numbers inside names numerically. That makes `1` and `01` look like the same number even though they are different library names.

Literal example:

```text
cache contains libalias.so.1  -> implementation A
cache contains libalias.so.01 -> implementation B
program asks for libalias.so.01
cache lookup -> implementation A or B according to the collapsed cache group
cache bypass -> implementation B exactly
```

The same mechanism also reaches very large digit strings because the comparator converts each decimal run into a C `int` without a checked bound.

## Why care

`DT_NEEDED` and `dlopen()` library names are byte strings supplied as identities. A cache accelerator should preserve which name was requested. Here the cache changes that answer: two exact names that resolve separately through ordinary directory search can resolve to one object when the cache participates.

The practical consequence depends on who can install libraries and regenerate the cache. Treat the current result as a dynamic-loader/package identity correctness defect. No privilege-escalation claim is made.

## Current state

- State: `EXECUTING`
- Exact working head: branch `investigation/glibc-cache-name-identity`; update after hosted gate
- Latest authoritative gate or artifact: local disposable Debian glibc 2.41 x86_64 reproduction; issue #502 live checkpoints
- First incomplete step: execute the committed probe on GitHub-hosted Ubuntu 24.04 / glibc 2.39
- Cleanup state: local disposable chroots removed; committed probe guards its `/tmp` cleanup root
- Next safe action: hosted Noble run, then candidate-model tests against the legacy cache ordering
- External-contact state: `false — unauthorized`

## Intent and precedent

glibc deliberately uses `_dl_cache_libcmp` for natural numeric ordering of library names. Loader cache search uses that comparator for binary-search equality and for walking the complete matching-name group. The source comment says the loader must use the same algorithm that generated the sorted cache.

Primary source:

- https://sourceware.org/pipermail/glibc-cvs/2020q4/070924.html

`ldconfig` uses the same comparator when sorting cache entries. The HWCAP-era cache generator retained that relationship:

- https://sourceware.org/pipermail/glibc-cvs/2020q4/071196.html

Recent cache work still leaves `_dl_cache_libcmp` and `search_cache` at this boundary, while changing cache lifetime and alternate-cache behavior:

- https://sourceware.org/pipermail/libc-alpha/2025-June/167244.html
- https://sourceware.org/pipermail/libc-alpha/2026-April/176857.html

SmolRunner independently encountered the same comparator-equivalence boundary while implementing a strict glibc 2.39 cache model. It chose to refuse comparator-equivalent byte aliases and comparator-overflowing names instead of treating them as one library identity.

## Question

Can current glibc preserve exact requested SONAME identity when `ld.so.cache` contains two byte-distinct keys that `_dl_cache_libcmp` considers equal, and what is the smallest cache-compatible repair?

## Source

- Project: GNU C Library (`glibc`)
- Requested revision or package version: Ubuntu Noble glibc 2.39 plus current runtime/main comparison
- Resolved commit: pending current-main source checkout
- Candidate source commit: none yet
- Local source path: none yet; first fixture exercises installed glibc
- Import metadata: none yet

## Environment

First reproduced environment:

- Distribution and release: Debian container environment
- glibc: `Debian GLIBC 2.41-12+deb13u3` / 2.41
- Kernel and architecture: x86_64 Linux host kernel
- Shell: bash
- Privileges: root only for a disposable private chroot
- Context: private `/tmp/glibc-cache-name-identity.*` roots; host `/etc/ld.so.cache` untouched
- Relevant tools: system `gcc`, `ldconfig`, dynamic loader, `chroot`

Hosted Noble environment will be recorded from the exact workflow job.

## Baseline behavior

### Leading-zero aliases

Two harmless DSOs carry distinct marker functions and exact SONAMEs:

```text
libalias.so.1  -> marker 101
libalias.so.01 -> marker 202
```

`ldconfig` accepts both and emits both cache keys. Across the local fixture variants, cache-backed requests for both names collapse to the same loaded object. Which member wins can differ with the package/file layout: direct SONAME-named files selected the `.01` implementation in one fixture, while ordinary versioned files with `ldconfig`-created SONAME links selected `.1` in another.

With `ld-linux --inhibit-cache --library-path ...`, the same requests load their exact corresponding DSOs.

A separate local control linked executables with literal `DT_NEEDED` entries for each spelling and reproduced the same cache-only identity collapse.

### Wide-decimal aliases

A second pair uses:

```text
libwide.so.1
libwide.so.4294967297
```

Both enter the real cache. Cache-backed lookup can collapse the large decimal spelling onto the other entry, while cache bypass loads the exact large-spelling DSO.

The historical comparator accumulates digit runs into signed `int` values before comparing them. Very large decimal runs therefore introduce an overflow problem in addition to the exact-name alias problem.

## Hypothesis or candidate

### Candidate A — exact-name eligibility inside the legacy comparator group

Keep `_dl_cache_libcmp` for locating the contiguous legacy-equivalence group in existing caches. While scanning that group, make an entry eligible only when its key is byte-equal to the requested name.

This is the strongest first candidate because:

- it preserves compatibility with caches already sorted using the historical comparator;
- it keeps HWCAP/architecture/flag preference among entries for one exact SONAME;
- it repairs the demonstrated cache-only wrong-object selection for leading-zero aliases;
- it can be regression-tested without changing cache format or sort order.

### Candidate B — make numeric comparison overflow-safe

The signed-`int` decimal accumulation should also receive a defined bound or an overflow-safe comparison. Replacing the comparator with a new total ordering everywhere is attractive but changes the ordering relation for old cache files. The loader explicitly relies on matching the generator's ordering, so this needs a cache-compatibility plan rather than a one-line comparator rewrite.

Possible compatible directions to test after Candidate A:

- detect over-wide numeric runs and use an exact-name linear fallback for that lookup;
- make new `ldconfig` reject or specially order unrepresentable numeric runs while the loader retains an old-cache path;
- introduce a cache-format/version transition if a total-order comparator is judged worth the compatibility cost.

## Reproduction

Run the committed fixture as root in a disposable environment:

```sh
sudo investigations/glibc-cache-name-identity/probe.sh
```

The probe:

1. creates a guarded private `/tmp` root;
2. copies only the current loader and libc needed by the tiny chroot;
3. builds harmless marker DSOs;
4. generates a private `ld.so.cache` with system `ldconfig -r`;
5. compares cache-backed `dlopen()` with `--inhibit-cache` lookup;
6. checks leading-zero aliases under two packaging layouts;
7. checks a wide-decimal alias;
8. removes the complete private root on exit.

It does not alter the host loader configuration or host cache and performs no network operation.

## Results

### Local glibc 2.41

Demonstrated:

- both leading-zero SONAME spellings can coexist in a generated cache;
- both wide-decimal SONAME spellings can coexist in a generated cache;
- cache-backed lookup collapses each pair onto one object;
- cache-bypass lookup keeps the two identities separate;
- literal `DT_NEEDED` requests exhibit the same leading-zero behavior;
- the winning leading-zero alias can change with library/file layout, consistent with the cache comparator treating the two keys as equal and later ordering details deciding their relative placement.

Hosted artifacts: pending.

## Interpretation

The defect is in cache identity semantics, rather than ordinary pathname search or ELF SONAME parsing. The negative control uses the same dynamic loader and the same DSOs while disabling only cache lookup; exact-name behavior returns immediately.

The source mechanism agrees with the experiment. `search_cache` calls `_dl_cache_libcmp` to decide that it found the requested name and continues scanning entries while that comparator returns zero. It has no byte-exact key check before an entry becomes eligible.

The cleanest first repair therefore belongs in cache lookup eligibility. Comparator overflow remains a related successor because it can create additional false equivalence and makes the ordering relation unsafe for arbitrary digit runs.

## Evidence boundary

Current executed evidence covers one x86_64 glibc 2.41 environment. Ubuntu Noble 2.39 and current glibc main execution remain pending. The fixture uses synthetic harmless DSOs and a private cache. It establishes wrong object identity under cache lookup; it does not establish real-world exploitability, package-manager reachability, a privilege boundary crossing, or behavior on non-Linux glibc ports.

Changing cache sorting could affect old/new cache interoperability, HWCAP ordering, architecture flags, and upgrades where a new loader briefly reads an older generated cache. Those compatibility surfaces must be tested before selecting any comparator-wide patch.

## Next step

1. Run `probe.sh` on GitHub-hosted Ubuntu 24.04 and retain the glibc/image identity and full output.
2. Add a small candidate model proving exact-name filtering preserves HWCAP selection among truly identical keys.
3. Reproduce against a current glibc main build.
4. If all three agree, prepare an internal candidate patch and glibc-native regression test in an owned fork or imported source tree.
5. Review the candidate against old-cache compatibility before any upstream packet decision.

## Authority

No glibc Bugzilla entry, mailing-list post, patch submission, email, review, or other external interaction is authorized or has been made. Work remains inside Linux Fieldwork, controlled repositories, and disposable local/owned CI.
