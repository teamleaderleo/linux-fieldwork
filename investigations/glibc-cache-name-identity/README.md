# glibc `ld.so.cache` numeric-name identity

## TL;DR

Ubuntu Noble glibc 2.39 and Debian glibc 2.41 both reproduce a cache-only library identity defect: two byte-distinct SONAMEs can coexist in `ld.so.cache`, yet cache-backed `dlopen()` treats them as one name when `_dl_cache_libcmp` considers their numeric components equal. Bypassing the cache with the same loader and DSOs restores exact-name resolution.

The retained fixture proves this with leading-zero aliases (`libalias.so.1` / `libalias.so.01`) and a wide-decimal pair (`libwide.so.1` / `libwide.so.4294967297`). The cleanest first candidate is deliberately smaller than a comparator rewrite: preserve the historical comparator to locate an old-cache equivalence group, then require byte-exact SONAME equality before an entry can participate in normal architecture/HWCAP preference. Comparator overflow remains a related successor because changing the sort relation outright can break lookup in already-generated caches.

## Explain like I'm five

Linux keeps an index of shared libraries so programs can find them quickly. The index compares numbers inside names numerically. That lets `1` and `01` compare as the same numeric value even though they are different library names.

Literal example:

```text
cache contains libalias.so.1  -> implementation A
cache contains libalias.so.01 -> implementation B
program asks for either name
cache lookup -> both requests can reach the same implementation
cache bypass -> each request reaches its exact implementation
```

## Why care

`DT_NEEDED` and `dlopen()` library names are byte-string identities. A lookup cache should preserve which name was requested. Here enabling the cache changes the loaded object while all ordinary pathname inputs stay the same.

The practical consequence depends on package/install authority and cache generation. The current claim is a dynamic-loader/package identity correctness defect. No privilege-escalation claim is made.

## Current state

- State: `EXECUTING`
- Exact working branch: `investigation/glibc-cache-name-identity`
- Dedicated Noble implementation gate: workflow `31341993102`, job `93317188110` — success
- Noble artifact: `9046104503`, `glibc-cache-name-identity-noble-x86_64`, ZIP digest `sha256:480b08f4a6c1ec83a2f1bc8f33a5c916f1f83dc79b05f2ae7759e6081e3cad45`
- Noble image: `ubuntu-24.04` image `20260720.247.2`, Ubuntu 24.04.4 LTS, glibc `2.39-0ubuntu8.7`
- Local comparison: Debian glibc `2.41-12+deb13u3`
- First incomplete step: execute against a current glibc development build and then turn Candidate A into a glibc-native regression/candidate patch
- Cleanup state: disposable local roots removed; hosted fixture cleans its guarded private root
- External-contact state: `false — unauthorized`

## Intent and precedent

glibc deliberately uses `_dl_cache_libcmp` for natural numeric ordering of library names. Loader cache search uses that comparator for binary-search equality and for walking the complete matching-name group. The source explicitly warns that lookup must use the same algorithm that generated the sorted cache.

Primary source:

- https://sourceware.org/pipermail/glibc-cvs/2020q4/070924.html

`ldconfig` uses the same comparator when sorting cache entries. The HWCAP-era cache generator retained that relationship:

- https://sourceware.org/pipermail/glibc-cvs/2020q4/071196.html

Recent cache work continues to modify cache loading/lifetime and alternate-cache plumbing around this lookup boundary while retaining `search_cache` and `_dl_cache_libcmp`:

- https://sourceware.org/pipermail/libc-alpha/2025-June/167244.html
- https://sourceware.org/pipermail/libc-alpha/2026-April/176857.html

SmolRunner independently encountered the same comparator-equivalence boundary while implementing a strict Noble glibc 2.39 cache model. It chose to refuse comparator-equivalent byte aliases and comparator-overflowing names rather than treat them as one library identity.

## Question

Can glibc preserve exact requested SONAME identity when `ld.so.cache` contains byte-distinct keys that `_dl_cache_libcmp` considers equal, and what is the smallest old-cache-compatible repair?

## Source

- Project: GNU C Library (`glibc`)
- Executed package versions: Ubuntu glibc `2.39-0ubuntu8.7`; Debian glibc `2.41-12+deb13u3`
- Development-source review: current 2025–2026 `elf/dl-cache.c` patch series and RFCs retain this lookup/comparator boundary
- Current-main execution: pending
- Candidate source commit: none yet
- Local imported source: pending candidate phase

## Environment

### Hosted Noble gate

- GitHub runner image: `ubuntu-24.04` / `20260720.247.2`
- OS: Ubuntu 24.04.4 LTS
- Kernel: `6.17.0-1020-azure` x86_64
- glibc: `Ubuntu GLIBC 2.39-0ubuntu8.7` / 2.39
- gcc: `13.3.0`
- Workflow permissions: repository contents read-only
- Probe context: guarded private chroot; host `/etc/ld.so.cache` untouched

### Local comparison

- glibc: `Debian GLIBC 2.41-12+deb13u3` / 2.41
- architecture: x86_64 Linux
- privileges: root only for a disposable private chroot
- context: private `/tmp/glibc-cache-name-identity.*` roots; host loader configuration/cache untouched

## Baseline behavior

### Leading-zero aliases

Two harmless DSOs carry distinct marker functions and exact SONAMEs:

```text
libalias.so.1  -> marker 101
libalias.so.01 -> marker 202
```

Noble's real `ldconfig` emits both cache keys. The hosted run observed:

```text
cached request libalias.so.1  -> marker 202, /usr/lib/libalias.so.01
cached request libalias.so.01 -> marker 202, /usr/lib/libalias.so.01
bypass request libalias.so.1  -> marker 101, /usr/lib/libalias.so.1
bypass request libalias.so.01 -> marker 202, /usr/lib/libalias.so.01
```

An ordinary versioned-file layout with `ldconfig`-created SONAME links reproduced the same collapse. Local fixture variants showed that which alias wins is a cache-generation/order detail; the stable defect is that the two requested identities collapse while cache bypass keeps them separate.

A separate local control linked executables with literal `DT_NEEDED` entries for each spelling and reproduced the same cache-only identity collapse.

### Wide-decimal aliases

The retained pair is:

```text
libwide.so.1
libwide.so.4294967297
```

Noble's real `ldconfig` emits both. The hosted run observed:

```text
cached request libwide.so.1          -> marker 302, libwide.so.4294967297
cached request libwide.so.4294967297 -> marker 302, libwide.so.4294967297
bypass request libwide.so.1          -> marker 301, libwide.so.1
bypass request libwide.so.4294967297 -> marker 302, libwide.so.4294967297
```

The historical comparator accumulates decimal runs into signed `int` values before comparing them. Wide decimal runs therefore add an overflow/ordering problem to the exact-name alias problem.

## Hypothesis or candidate

### Candidate A — byte-exact eligibility inside the legacy comparator group

Keep `_dl_cache_libcmp` for locating the contiguous equivalence group in existing caches. While scanning that group, make an entry eligible only when its key is byte-equal to the requested SONAME. Apply the existing architecture, ISA and HWCAP preference rules only among those exact-name entries.

Why this is the strongest first candidate:

- old caches remain searchable using the relation under which they were sorted;
- aliases such as `.1` and `.01` stop stealing one another's requests;
- several entries for one exact SONAME still receive ordinary HWCAP preference;
- no cache-format transition is required for the demonstrated leading-zero defect.

`candidate_model.py` makes that boundary executable: an alias with artificially better HWCAP priority is rejected for a `.1` request, while an optimized entry carrying the exact `.1` SONAME still beats its exact-name baseline.

### Candidate B — overflow-safe numeric comparison

The signed-`int` decimal accumulation needs a defined bound or an overflow-safe comparison. A new total ordering is attractive, but applying it directly to loader binary search would change the relation used to sort existing cache files.

Compatibility-aware possibilities to test after Candidate A include:

- an exact-name fallback for requests whose numeric runs exceed the legacy comparator's safe range;
- new `ldconfig` validation/order semantics paired with an old-cache loader path;
- a cache-format/version transition if maintainers prefer a comparator whose equality implies byte equality.

## Reproduction

Run the committed fixture as root in a disposable x86_64 environment:

```sh
sudo investigations/glibc-cache-name-identity/probe.sh
python3 investigations/glibc-cache-name-identity/candidate_model.py
```

The shell probe creates a guarded private `/tmp` root, copies only the current loader/libc needed by the tiny chroot, builds harmless marker DSOs, generates a private cache with `ldconfig -r`, compares cache-backed and `--inhibit-cache` lookup, and removes the complete private root on exit.

It performs no network operation and does not alter the host cache.

## Results

### Ubuntu Noble glibc 2.39

Dedicated workflow `31341993102`, job `93317188110` passed all three discriminator families:

- direct leading-zero aliases collapse with cache and remain exact without cache;
- versioned-file leading-zero aliases collapse with cache and remain exact without cache;
- wide-decimal aliases collapse with cache and remain exact without cache.

Artifact `9046104503` retains the probe output. ZIP digest: `sha256:480b08f4a6c1ec83a2f1bc8f33a5c916f1f83dc79b05f2ae7759e6081e3cad45`.

### Debian glibc 2.41

The same families reproduced locally. A literal-`DT_NEEDED` control also showed the cache can change which DSO satisfies the exact dependency name.

### Source alignment

`search_cache` uses `_dl_cache_libcmp` both to locate the requested name by binary search and to define the matching group it scans for the best cache entry. No byte-exact key check separates comparator-equivalent spellings before an entry becomes eligible.

## Interpretation

The negative control changes one factor: cache participation. The same loader and same DSO files resolve exact SONAME spellings correctly when the cache is inhibited. That isolates the demonstrated identity change to cache lookup semantics.

Two independent release families, glibc 2.39 and 2.41, reproduce the same result, and active 2025–2026 source work retains the relevant comparator/search boundary. Current development-head execution remains the next version gate.

The first candidate belongs in cache-entry eligibility rather than cache generation. That keeps compatibility with existing cache ordering while restoring exact SONAME identity. Overflow then deserves its own compatibility decision.

## Evidence boundary

Executed evidence covers x86_64 glibc 2.39 and 2.41. Current development head and other architectures remain pending. The fixture uses synthetic harmless DSOs and a private cache. It establishes wrong object identity under cache lookup; it does not establish package-manager reachability, privilege escalation, or a concrete affected production package.

Changing cache sorting can affect old/new cache interoperability, HWCAP ordering, architecture flags, and upgrades where a new loader reads an older generated cache. Those surfaces stay outside Candidate A and require dedicated evidence before a comparator-wide change.

## Next step

1. Execute the candidate model in the hosted gate and retain the final-head result.
2. Build/test a current glibc development checkout or owned fork with a glibc-native regression reproducing the leading-zero pair.
3. Implement Candidate A as an internal patch and prove exact `.1` / `.01` resolution plus ordinary same-name HWCAP selection.
4. Add wide-decimal regression coverage and choose a compatibility-aware overflow repair separately.
5. Obtain independent exact-diff review before any decision about an upstream packet.

## Authority

No glibc Bugzilla entry, mailing-list post, patch submission, email, review, or other external interaction is authorized or has been made. Work remains inside Linux Fieldwork, controlled repositories, and disposable local/owned CI.
