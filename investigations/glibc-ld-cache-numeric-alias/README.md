# glibc ld.so.cache numeric-name alias identity

State: `executing`

Owning issue: #502  
External contact: `false — unauthorized`

## TL;DR

Current glibc uses `_dl_cache_libcmp` both to sort `ld.so.cache` keys and to decide whether a requested library name matches a cached key. Decimal runs are compared by numeric value, so byte-distinct spellings such as `libalias.so.1` and `libalias.so.01` compare equal.

Current `ldconfig` keeps byte-distinct SONAMEs distinct during directory collection and does not deduplicate comparator-equal cache entries. The loader then accepts the cached pathname selected by that comparator group without a later byte-for-byte SONAME check in the inspected cache path.

This investigation executes a disposable two-DSO fixture on Ubuntu 24.04 to determine the concrete lookup result and whether reversing cache directory order changes which implementation both spellings select.

## Explain like I'm five

The cache sorts numbered library names as numbers. `1` and `01` have the same numeric value. The loader also uses that sorting comparison to decide whether a requested name is the same cache key. We are checking whether asking for one exact spelling can therefore open the library registered under another spelling.

## Why care

Dynamic-library lookup is an identity boundary. Natural numeric ordering is useful for cache sorting, while byte-level SONAME identity is a separate property. If the two are collapsed, a valid cache can make an absent spelling resolve to a different SONAME or make selection depend on cache directory order.

The first goal is exact behavior, not severity. The fixture uses only harmless local DSOs and an isolated cache.

## Exact source boundary

Current source inspected 2026-08-10:

- glibc `elf/dl-cache.c::search_cache` and `_dl_cache_libcmp`;
- glibc `elf/cache.c::{compare,add_to_cache}`;
- glibc `elf/ldconfig.c::search_dir`;
- glibc `elf/dl-is_dso.h`;
- glibc `elf/dl-load.c` cache lookup path;
- historical glibc commit `686dfcd106e96e3f991cec76c8d0e434cf97fe54`, which changed cache lookup from `strcmp` to `_dl_cache_libcmp` in 1999.

Source observations:

1. cache binary search treats `_dl_cache_libcmp(...) == 0` as name equality;
2. digit runs are accumulated and compared numerically;
3. directory collection deduplicates SONAMEs with exact `strcmp`;
4. `add_to_cache` always inserts the exact interned SONAME and uses the numeric comparator only for ordering;
5. ordinary `lib*.so*` names are admitted by the DSO filename heuristic;
6. the cached pathname is passed to `open_verify`, then the opened object is mapped; the inspected path has no later exact requested-name-versus-SONAME rejection.

## Fixture

`probe.sh` creates two private chroot roots from one tiny runtime:

- directory A contains a DSO whose SONAME is `libalias.so.1` and whose marker returns `101`;
- directory B contains a DSO whose SONAME is `libalias.so.01` and whose marker returns `202`;
- comparator-distinct controls use `libcontrol.so.1` → `301` and `libcontrol.so.2` → `302`.

One root configures A before B; the other configures B before A. Each root gets its own `ldconfig`-generated `/etc/ld.so.cache`. The test process runs inside that private root through the host's exact loader/runtime copies, so host `/etc/ld.so.cache` is never replaced or edited.

Queries per root:

- `libalias.so.1`;
- `libalias.so.01`;
- absent but comparator-equivalent `libalias.so.001`;
- comparator-distinct absent `libalias.so.2`;
- `libcontrol.so.1`;
- `libcontrol.so.2`.

## Distinguishing outcomes

### Alias identity reproduced

The exact and leading-zero alias requests select the same marker inside one cache, an absent comparator-equivalent spelling resolves, the `.2` negative control remains missing, and reversing directory order changes the selected alias implementation.

### Exact identity preserved

Exact requests select their respective marker, the absent `.001` spelling remains missing, and reversing directory order does not change exact-name selection.

### Harness or model mismatch

Control SONAMEs select the wrong marker, `ldconfig` refuses the admitted fixture, the private root cannot execute the probe, or the result mixes behaviors in a way the source model did not predict. Classify that before changing the claim.

## Safety and cleanup

- no host `/etc/ld.so.cache` write or bind mount;
- no package installation;
- no network access from the probe;
- no real credentials or host-private input;
- every generated file lives under one `mktemp` root;
- `ldconfig -r` and `chroot` use GitHub-hosted disposable sudo only against that exact root;
- cleanup removes only the exact private root created by this run.

## Evidence boundary

A hosted pass can establish Ubuntu Noble glibc behavior for the runner image and the synthetic DSOs. Current glibc-main behavior remains source-derived until the same fixture is executed against a current build.

Even a reproduced alias does not by itself establish privilege escalation or a deployed security incident. The immediate consequence is cache-name identity ambiguity and potentially order-dependent DSO selection.

## Next action

Run the dedicated Ubuntu 24.04 workflow, retain the exact job/run and result artifact, then decide whether to add a current-glibc build lane or stop with a Noble characterization.
