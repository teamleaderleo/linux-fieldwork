# Cleanup markers must carry contained relative paths

## In simple words

A setup step can validate a destination correctly and still hand dangerous text to cleanup. A durable marker becomes a later filesystem instruction. Store a canonical relative identifier, validate the complete marker before any action, then validate each entry again immediately before cleanup.

## Failure pattern

```sh
printf '/%s\0' "$untrusted_path" >> "$root/run/marker"
...
xargs --null rm -r "$root/{}"
```

An entry such as `/../../outside` can escape the intended root when cleanup concatenates it. An existing symlink below the root can redirect a lexically ordinary entry elsewhere.

Entry-by-entry validation also permits partial cleanup from invalid persisted state. A valid first entry may be removed or unmounted before a later invalid entry stops the command.

## Safer sequence

During setup:

1. canonicalize the root;
2. canonicalize the existing source;
3. preserve the configured destination identity when the consumer will reopen that exact path;
4. reject a spelling whose components cannot remain reachable after normalization;
5. resolve existing destination components;
6. require a strict descendant of the root;
7. perform the operation against that canonical destination;
8. record only the root-relative destination, without a leading slash, empty component, `.` or `..`.

Source and destination identities can differ. A terminal source symlink may safely use its canonical referent as the bind source while retaining the configured symlink pathname as the destination. Parent components require more care: turning `spelling/../repository` into `repository` leaves the configured path unreachable unless `spelling` also exists below the generated root. Reject that spelling or reproduce every required component deliberately.

During cleanup:

1. treat every NUL-delimited marker entry as untrusted persisted input;
2. reject absolute and non-canonical component spellings;
3. resolve each current destination so changed symlinks are visible;
4. require containment for every entry before invoking any cleanup action;
5. after the complete preflight succeeds, repeat lexical and canonical checks immediately before each removal or unmount;
6. retain the marker when validation or an action fails so the remaining state stays inspectable.

Example boundary:

```sh
validate_entry() {
    case "/$entry/" in
        *"/../"*|*"/./"*|*"//"*) return 1 ;;
    esac
    target=$(realpath -m -- "$root/$entry")
    case "$target" in
        "$root"/*) : ;;
        *) return 1 ;;
    esac
}

# Pass one: every entry must validate before action.
# Pass two: validate again, then act on that canonical target.
```

## Why validation repeats

The filesystem can change between setup and cleanup. A path that was contained during setup may traverse a newly created symlink later. The marker format limits ambiguity; cleanup-time resolution checks the current state.

The complete preflight gives static invalid marker state an all-or-zero action result. The second validation narrows the interval between checking an entry and acting on it.

This remains a check-then-act pathname contract. A hostile process with enough access may race a component or marker replacement after validation. Stronger adversarial boundaries use descriptor-relative APIs, no-follow policies, or isolated mount namespaces.

## Regression pattern

A focused regression should cover:

- a baseline traversal that points outside the root;
- candidate rejection before creation, copy, mount, removal, or unmount;
- a normal source and contained target;
- a terminal source symlink whose configured destination remains reachable;
- a parent-component spelling that would become unreachable after lexical normalization;
- a harmless dot component whose configured path stays reachable;
- a symlinked target parent;
- a marker with `..`;
- a marker whose current resolution follows a symlink outside the root;
- a valid entry followed by an invalid entry, with zero cleanup actions;
- preservation of a rejected marker and target for diagnosis;
- immediate rerun after correcting the marker;
- no real destructive operation in the test fixture.

## Related record

- issue #164
- PR #179
- `investigations/mmdebstrap-file-mirror-containment/README.md`
- `tests/test_file_mirror_automount_containment.py`
- `tests/test_file_mirror_automount_cleanup_preflight.py`
- `tests/test_file_mirror_automount_source_normalization.py`
- `tests/test_file_mirror_automount_parent_component_reachability.py`
