# Caching proxy pathname replacement races

## TL;DR

The composed caching-proxy candidate validates resolved cache paths before filesystem work, but later reads, temporary creation, and atomic replacement traverse pathname components again. Deterministic barriers reproduce three distinct outside-root operations:

- old-cache parent replacement serves and copies outside bytes;
- old-cache final-component replacement serves and copies outside bytes;
- new-cache parent replacement publishes origin bytes outside the validated root.

A new-cache final symlink is the negative control: atomic replacement replaces the symlink itself and preserves its outside target. Every mutated case restores state and completes an immediate clean rerun. A bounded fd-relative repair is now justified.

## Explain like I'm five

The proxy checks a shelf address inside its cache cabinet. Before it returns, another local process changes either the hallway or the package label into a shortcut.

The tests show that changed hallways redirect both reading and writing, and a changed old package label redirects reading. But a changed new package label is replaced rather than followed. After each experiment, the cabinet is restored and used normally again.

## Why care

A redirected cache read can return bytes from a local file outside the cache root through loopback HTTP. A redirected publication can write origin bytes outside the cache root with the proxy process's permissions.

The scenario requires another process with the same user identity and mutation authority over a cache descendant. The probe establishes filesystem behavior, not deployment frequency, remote reachability, or cross-user access.

## Source and routing

- Linux owner: issue #227
- Parent composition: issue #188 and merged PR #198
- Fieldwork owner: `teamleaderleo/fieldwork` issue #276
- Exact current-main base: `8827ad0764a532b737d8b501cf0980b7f330294a`
- Current branch: `investigation/caching-proxy-parent-swap-race-current-main`
- Predecessor branch: `investigation/caching-proxy-parent-swap-race`
- Generated candidate: `investigations/caching-proxy-complete-stack/compose.py`
- Implementation owner: `investigations/caching-proxy-complete-stack/compose_impl.py`
- Focused regression: `tests/test_caching_proxy_parent_swap_race.py`
- Imported source: unchanged
- Upstream contact: unauthorized

## Current source model

`request_context()` resolves a requested cache path and verifies that it is a strict descendant of the resolved cache root. The handler then retains an ordinary `pathlib.Path`.

The cache-hit path later performs existence, metadata, and open operations through that pathname. The publication path later derives a sibling temporary name, opens it with `os.open()`, and publishes it with `os.replace()`. Those operations interpret pathname components again at operation time.

Parent replacement and final-component replacement therefore differ:

- a replaced parent redirects every later descendant traversal;
- an old-cache final symlink is followed by metadata and open calls;
- a new-cache final symlink is replaced atomically by `os.replace()` without modifying its target.

## Probe design

The focused class inherits the complete composed regression matrix, preserving ordinary request, cache, framing, retry, permission, concurrency, and cleanup controls.

It adds four real loopback HTTP and filesystem probes:

1. **Old-cache parent replacement**
   - pause after old and new paths validate;
   - rename the checked old-cache parent;
   - replace it with a symlink to an outside directory containing known bytes;
   - require the outside bytes in the HTTP response and copied new cache.

2. **Old-cache final-component replacement**
   - begin with a safe old-cache object;
   - pause after validation;
   - rename the checked object and replace only its final name with a symlink to an outside object;
   - require the outside bytes in the HTTP response and copied new cache.

3. **New-cache parent replacement**
   - pause after new-path validation but before temporary creation;
   - rename the checked parent and replace it with a symlink to an outside directory;
   - require origin bytes to be published below the outside directory.

4. **New-cache final-component replacement control**
   - pause before temporary creation;
   - create a final-name symlink to an outside sentinel;
   - require the final cache object to replace the symlink while preserving the outside sentinel bytes.

After each replacement case, the test restores the checked component, clears or resets raced state, performs an immediate request against the same roots, and verifies ordinary behavior plus hidden-temporary cleanup.

The complete matrix is also launched under real optimized Python with `python -O`. A child marker prevents recursive spawning while leaving all behavioral tests active.

## Exact baseline evidence

Pre-restack exact head `dabe79cefb6062e20dc6201556b5f541a8470bbc` passed Linux Fieldwork CI run `30587406344` on Ubuntu 24.04. The intended `lab-tools` job ran 232 tests successfully, including:

- `test_validated_old_cache_parent_swap_reaches_outside_file`;
- `test_validated_old_cache_final_component_swap_reaches_outside_file`;
- `test_validated_new_cache_parent_swap_publishes_outside_root`;
- `test_validated_new_cache_final_symlink_is_replaced_not_followed`;
- `test_matrix_under_optimized_python`.

That run checked out the exact pull-request merge of `dabe79ce...` into base `ed49c01a...`. It is authoritative for the predecessor baseline and provenance for this current-main restack; the current head still needs its own exact-head gate.

## Exact commands

Focused execution:

```text
python3 tests/test_caching_proxy_parent_swap_race.py
```

The test itself runs the complete matrix again under:

```text
python3 -O tests/test_caching_proxy_parent_swap_race.py
```

Repository gate:

```text
Linux Fieldwork CI on the exact pull-request head
```

## Observed results

| Operation | Exact observed outcome |
| --- | --- |
| old-cache parent replacement | HTTP 200 carries outside bytes; origin is not contacted; copied new cache contains outside bytes |
| old-cache final replacement | HTTP 200 carries outside bytes; origin is not contacted; copied new cache contains outside bytes |
| new-cache parent replacement | HTTP 200 carries origin bytes; final cache object is published below the outside directory |
| new-cache final symlink | final symlink is replaced; outside target bytes remain unchanged |
| cleanup and rerun | mutated component restored, hidden temporaries absent, immediate same-root rerun succeeds |
| optimized Python | complete matrix passes under real `python -O` |

## Interpretation

**Demonstrated behavior:** post-validation parent replacement redirects cache-hit reads and fresh publication. Old-cache final-component replacement redirects reads. New-cache final-component replacement does not follow the symlink target during atomic publication.

**Design consequence:** path validation alone is not authoritative when later operations re-traverse mutable descendants. A repair should keep an opened directory identity and perform descendant operations relative to that descriptor.

**Open question:** the exact fd-relative design must preserve current mode, atomicity, readonly, framing, retry, cleanup, and response contracts.

## Evidence boundary

The deterministic barriers model a same-UID process that can rename a cache descendant and create a symlink. They do not establish remote exposure, cross-UID mutation, configured-cache-root replacement, arbitrary external ancestor replacement, crash durability, request coalescing, or production frequency.

The reproduced outside operations justify evaluating a directory-fd-relative descendant walk. They do not prove that every deployed cache layout grants another process the required mutation authority.

## Candidate-selection rule

A repair must preserve:

- ordinary old-cache reads;
- ordinary new-cache publication;
- `0666 & umask` mode behavior;
- atomic final-name replacement;
- hidden unique temporaries;
- readonly behavior;
- complete-stream validation;
- post-commit error behavior;
- loopback request and response contracts;
- cleanup and rerun.

Configured cache roots and their external ancestors may remain a stated trust boundary if the repair anchors every descendant operation to an opened root directory and never re-enters through an untrusted pathname.

## Current disposition

`repair-justified`.

Land the current-main baseline record after exact-head CI and complete two-file review. Then continue issue #227 with one canonical fd-relative candidate rather than adding a second independent fix carrier.

## Authority

Internal Linux Fieldwork work only. No Debian or other external issue, email, patch, merge request, comment, or review is authorized or included.
