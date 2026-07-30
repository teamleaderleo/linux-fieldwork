# Caching proxy parent-swap race

## TL;DR

The composed caching-proxy candidate validates resolved cache paths before filesystem work, but later cache reads, temporary creation, and atomic replacement re-traverse those paths. This investigation inserts deterministic barriers after validation and tests whether a same-UID rename-plus-symlink swap redirects a cache hit or publication outside the validated cache root.

## Explain like I'm five

The proxy checks that a package belongs in its cache cabinet. Before it returns to fetch or place the package, another local process replaces one checked hallway with a shortcut. The test asks whether the proxy follows the shortcut into a different directory.

## Why care

A redirected old-cache read could return bytes from a local file outside the cache root through loopback HTTP. A redirected publication could write origin bytes outside the cache root with the proxy process's permissions. The scenario requires another process with the same user identity and mutation authority over a cache descendant. Deployment frequency and broader exposure remain unknown.

## Source and routing

- Linux owner: issue #227
- Parent composition: issue #188 and merged PR #198
- Fieldwork owner: `teamleaderleo/fieldwork` issue #276
- Exact base: `ed49c01a85e9d363626db5d2973a33b67209e13b`
- Branch: `investigation/caching-proxy-parent-swap-race`
- Generated candidate: `investigations/caching-proxy-complete-stack/compose.py`
- Owning implementation fragments: `compose_impl.py` lines containing `request_context()`, `oldpath.is_file()`, `cache_destination()`, `new_cache_temporary()`, and `os.replace()`
- Focused regression: `tests/test_caching_proxy_parent_swap_race.py`
- Imported source: unchanged
- Upstream contact: unauthorized

## Current source model

`request_context()` resolves each requested cache path and verifies that it is a strict descendant of the resolved cache root. The handler then stores ordinary `pathlib.Path` objects.

The cache-hit path later calls `oldpath.is_file()`, `oldpath.stat()`, and `oldpath.open()`. The publication path later derives a sibling temporary pathname with `path.with_name()`, opens it with `os.open()`, and publishes it with `os.replace()`. Each operation resolves pathname components again at operation time.

The composed finding already lists same-UID pathname/component replacement between validation and open as outside scope. This investigation turns that limit into an executable question.

## Competing outcomes

1. **Confined:** the validated path identity remains authoritative and a parent swap cannot redirect either read or publication.
2. **Read-only escape:** cache-hit operations follow the replacement parent, while publication remains confined.
3. **Publication-only escape:** temporary creation or replacement follows the replacement parent, while cache hits remain confined.
4. **Both escape:** both operations re-traverse the replacement parent and reach the outside directory.

## Probe design

The focused test subclasses the complete seven-test composed matrix, preserving ordinary request, cache, framing, retry, permission, concurrency, and cleanup controls.

Two additional tests use real loopback HTTP and real filesystem operations:

1. pause after both `request_context()` calls return but before `oldpath.is_file()`; rename the checked old-cache parent and replace it with a symlink to an outside directory containing known bytes;
2. pause at `cache_destination()` after the new path was validated but before temporary creation; rename the checked new-cache parent and replace it with a symlink to an outside directory containing a sentinel.

The tests assert HTTP status and body, origin request count, outside bytes, preserved checked directory, symlink state, final cache location, temporary cleanup, and inherited ordinary behavior.

## Exact commands

Focused direct execution:

```text
python3 tests/test_caching_proxy_parent_swap_race.py
```

Repository gate:

```text
Linux Fieldwork CI on the exact pull-request head
```

## Evidence boundary

The deterministic barriers model a same-UID process that can rename a descendant directory and create a symlink. They do not establish remote exposure, cross-UID mutation, configured-cache-root replacement, arbitrary ancestor replacement, crash durability, miss coalescing, or production frequency.

A reproduced race will justify evaluating an fd-relative descendant walk. It will not by itself prove that every deployed cache layout is attacker-controlled.

## Candidate-selection rule

A repair may proceed only after baseline execution reproduces an outside-root operation. The candidate must preserve:

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

Configured cache roots and their external ancestors may remain a separately stated trust boundary if the repair anchors all descendant traversal to an opened root directory.

## Current disposition

`research-active`.

The baseline probe is published but has no exact-head execution receipt yet. If either race reproduces, the next transition is a bounded fd-relative candidate plus controls. If both remain confined, retain a negative result and stop.
