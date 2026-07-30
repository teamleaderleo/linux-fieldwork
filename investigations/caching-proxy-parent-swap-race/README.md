# Caching proxy pathname replacement races

## TL;DR

The composed caching-proxy candidate validates resolved cache paths before filesystem work, but later reads, temporary creation, and atomic replacement traverse pathname components again. This investigation places deterministic barriers after validation and tests parent-directory and final-component replacement separately.

The matrix now also restores the mutated state and performs an immediate clean rerun. No repair is selected until the exact-head baseline executes and records which operations actually escape.

## Explain like I'm five

The proxy checks a shelf address inside its cache cabinet. Before it returns to fetch or place the package, another local process changes either:

- the hallway leading to the shelf; or
- the package label at the final shelf.

The tests ask whether the proxy follows the changed route outside the cabinet. They then put the cabinet back and prove it can be used normally again.

## Why care

A redirected cache read could return bytes from a local file outside the cache root through loopback HTTP. A redirected publication could write origin bytes outside the cache root with the proxy process's permissions.

The scenario requires another process with the same user identity and mutation authority over a cache descendant. The probe establishes filesystem behavior, not deployment frequency, remote reachability, or cross-user access.

## Source and routing

- Linux owner: issue #227
- Parent composition: issue #188 and merged PR #198
- Fieldwork owner: `teamleaderleo/fieldwork` issue #276
- Exact base: `ed49c01a85e9d363626db5d2973a33b67209e13b`
- Branch: `investigation/caching-proxy-parent-swap-race`
- Generated candidate: `investigations/caching-proxy-complete-stack/compose.py`
- Implementation owner: `investigations/caching-proxy-complete-stack/compose_impl.py`
- Focused regression: `tests/test_caching_proxy_parent_swap_race.py`
- Imported source: unchanged
- Upstream contact: unauthorized

## Current source model

`request_context()` resolves a requested cache path and verifies that it is a strict descendant of the resolved cache root. The handler then retains an ordinary `pathlib.Path`.

The cache-hit path later calls existence, metadata, and open operations through that pathname. The publication path later derives a sibling temporary name, opens it with `os.open()`, and publishes it with `os.replace()`. Those operations interpret pathname components again at operation time.

This means parent replacement and final-component replacement are not necessarily equivalent:

- a replaced parent can redirect all later descendant traversal;
- an old-cache final symlink may be followed by metadata and open calls;
- a new-cache final symlink may instead be replaced atomically by `os.replace()` without modifying its target.

The probe records those outcomes separately rather than describing every symlink race as one behavior.

## Competing outcomes

1. **Confined:** validated identity remains authoritative and no outside operation occurs.
2. **Read-only escape:** cache-hit reads follow a replacement component, while publication remains confined.
3. **Publication-only escape:** temporary creation or replacement follows a replacement parent, while reads remain confined.
4. **Both escape:** reads and publication reach outside directories.
5. **Component split:** parent replacement escapes, while final publication replacement remains confined because the symlink itself is atomically replaced.

## Probe design

The focused class inherits the complete composed regression matrix, preserving ordinary request, cache, framing, retry, permission, concurrency, and cleanup controls.

It adds four real loopback HTTP and filesystem probes:

1. **Old-cache parent replacement**
   - pause after old and new paths validate;
   - rename the checked old-cache parent;
   - replace it with a symlink to an outside directory containing known bytes;
   - record the returned body, origin count, copied cache bytes, symlink, and preserved directory.

2. **Old-cache final-component replacement**
   - begin with a safe old-cache object;
   - pause after validation;
   - rename the checked object and replace only its final name with a symlink to an outside object;
   - record which bytes are returned and copied.

3. **New-cache parent replacement**
   - pause after new-path validation but before temporary creation;
   - rename the checked parent and replace it with a symlink to an outside directory;
   - record temporary placement, final publication, outside sentinel state, and origin count.

4. **New-cache final-component replacement control**
   - pause before temporary creation;
   - create a final-name symlink to an outside sentinel;
   - require the result to distinguish replacing the symlink itself from following and overwriting its target.

After each replacement case, the test restores the checked component, removes or resets the raced cache object, performs an immediate request against the same roots, and verifies ordinary behavior plus temporary cleanup.

The complete matrix is also launched under real optimized Python with `python -O`. A child marker prevents recursive spawning while leaving all behavioral tests active.

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

## Required evidence

For each race, retain:

- exact head and base;
- HTTP status and response body;
- origin request count;
- preserved checked object or directory;
- replacement symlink state;
- inside and outside bytes;
- final cache location;
- hidden-temporary cleanup;
- clean rerun result;
- ordinary and optimized Python status.

## Evidence boundary

The deterministic barriers model a same-UID process that can rename a cache descendant and create a symlink. They do not establish remote exposure, cross-UID mutation, configured-cache-root replacement, arbitrary external ancestor replacement, crash durability, request coalescing, or production frequency.

A reproduced outside operation justifies evaluating a directory-fd-relative descendant walk. It does not prove that every deployed cache layout grants another process the required mutation authority.

## Candidate-selection rule

A repair may proceed only after exact-head baseline execution reproduces an outside-root operation. The candidate must preserve:

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

Configured cache roots and their external ancestors may remain a stated trust boundary if the repair anchors every descendant operation to an opened root directory and does not re-enter through an untrusted pathname.

## Current disposition

`research-active`.

The expanded baseline probe is published but has no exact-head execution receipt yet. If a race reproduces, the next transition is a bounded fd-relative candidate with compatibility controls. If all operations remain confined, retain the negative result and stop.
