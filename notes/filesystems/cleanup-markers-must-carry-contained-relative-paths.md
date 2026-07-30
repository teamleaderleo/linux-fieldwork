# Cleanup markers must carry contained relative paths

## In simple words

A setup step can validate a destination correctly and still hand dangerous text to cleanup. A durable marker becomes a later filesystem instruction. Store a canonical relative identifier, then validate it again at cleanup time.

## Failure pattern

```sh
printf '/%s\0' "$untrusted_path" >> "$root/run/marker"
...
xargs --null rm -r "$root/{}"
```

An entry such as `/../../outside` can escape the intended root when cleanup concatenates it. An existing symlink below the root can redirect a lexically ordinary entry elsewhere.

## Safer sequence

During setup:

1. canonicalize the root;
2. canonicalize the existing source;
3. derive the destination below the root;
4. resolve existing destination components;
5. require a strict descendant of the root;
6. perform the operation against that canonical destination;
7. record only the root-relative destination, without a leading slash, empty component, `.` or `..`.

During cleanup:

1. treat every marker entry as untrusted persisted input;
2. reject absolute and non-canonical component spellings;
3. resolve the current destination again so changed symlinks are visible;
4. require containment again;
5. invoke removal or unmount only with the validated canonical path;
6. retain the marker when validation fails so the rejected state remains inspectable.

Example boundary:

```sh
case "/$entry/" in
    *"/../"*|*"/./"*|*"//"*) exit 1 ;;
esac
target=$(realpath -m -- "$root/$entry")
case "$target" in
    "$root"/*) : ;;
    *) exit 1 ;;
esac
```

## Why validation repeats

The filesystem can change between setup and cleanup. A path that was contained during setup may traverse a newly created symlink later. The marker format limits ambiguity; cleanup-time resolution checks the current state.

This remains a check-then-act pathname contract. A hostile process with enough access may race a component replacement after validation. Stronger adversarial boundaries use descriptor-relative APIs, no-follow policies, or isolated mount namespaces.

## Regression pattern

A focused regression should cover:

- a baseline traversal that points outside the root;
- candidate rejection before creation, copy, mount, removal, or unmount;
- a normal source and contained target;
- a symlinked target parent;
- a marker with `..`;
- a marker whose current resolution follows a symlink outside the root;
- preservation of a rejected marker for diagnosis;
- no real destructive operation in the test fixture.

## Related record

- issue #164
- `investigations/mmdebstrap-file-mirror-containment/README.md`
- `tests/test_file_mirror_automount_containment.py`
