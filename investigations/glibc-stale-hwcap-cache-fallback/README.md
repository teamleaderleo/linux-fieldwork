# glibc stale HWCAP cache fallback

## TL;DR

Current glibc cache lookup collapses an ordered set of eligible `ld.so.cache` entries to one malloc-owned pathname. `dl-load.c` tries that path once; if the file has disappeared, it leaves cache semantics and enters ordinary default-directory search. The existing glibc HWCAP cache test calls this behavior undesirable and says it would ideally fall back to the next cached implementation.

This investigation is testing the smallest internal API that can preserve the ordered cached alternatives without retaining pointers into a cache mapping that recursive `dlopen` can replace.

## Source boundary

Current source reviewed at:

- `gnutools/glibc@bd57d3231d7e700d03424854bd8b50b6ce169cc6`
- `elf/dl-cache.c::search_cache`
- `elf/dl-cache.c::_dl_load_cache_lookup`
- `elf/dl-load.c::_dl_map_new_object`
- `elf/tst-glibc-hwcaps-prepend-cache.c`

The previously retained disposable reproduction on Linux Fieldwork issue #503 remains the behavioral starting point. External contact is unauthorized.

## Observed current path

1. `search_cache` binary-searches the matching cache-name group.
2. It checks architecture flags, ISA compatibility, and active `glibc-hwcaps` priority.
3. It returns one best pathname.
4. `_dl_load_cache_lookup` copies that pathname before returning because allocation can recursively invoke `dlopen` and replace the cache mapping.
5. `dl-load.c` calls `open_verify` on that one pathname.
6. If the open fails, the cached pathname is freed and the loader immediately starts ordinary default-path search.

The cache caller has no operation that means “give me the next eligible cached path.”

## Existing project intent

`elf/tst-glibc-hwcaps-prepend-cache.c` already contains the stale-entry case. After the preferred cached HWCAP object is unlinked, the test explains that the loader would ideally revert to the next implementation in the cache. Current behavior fails because cache lookup returns only one filename.

## Candidate API question

A raw iterator pointer or retained cache index is unsafe by default. The current lookup deliberately copies its result because a recursive loader action during allocation can unmap or replace the cache.

The first candidate family therefore returns one **copied candidate snapshot**:

```text
exact requested cache-name group
-> filter architecture / ISA / active HWCAP entries
-> order named HWCAP candidates by runtime priority
-> retain cache order for equal-priority duplicates
-> append compatible ordinary cache candidates in cache order
-> copy the resulting pathnames out of the mapped cache
-> let dl-load try each copied pathname with open_verify
-> only after all cached candidates fail, enter ordinary default search
```

This keeps file opening in `dl-load.c` and cache interpretation in `dl-cache.c`.

## Required discriminators

- all files present: selection stays identical to current glibc;
- preferred HWCAP missing: next active cached HWCAP wins;
- all named HWCAP files missing: cached baseline wins;
- every cached candidate missing: ordinary default search still runs;
- inactive or ISA-incompatible HWCAP entries remain skipped;
- equal-priority duplicate entries retain existing cache order;
- cache data changing during the first open cannot invalidate the remaining candidate strings;
- exact current glibc `tst-glibc-hwcaps-prepend-cache` changes only the documented stale-file expectation;
- cache reload and ordinary non-HWCAP cache tests remain green.

## Evidence limit

The candidate-list representation is a design hypothesis until it is applied to current glibc and executed against the native test suite. No upstream report or patch submission is authorized.
