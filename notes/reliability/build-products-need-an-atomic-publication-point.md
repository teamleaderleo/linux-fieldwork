# Build products need an atomic publication point

## In simple words

A tool should not expose its final output pathname while the object is still being constructed. If a later stage fails, callers cannot tell a partial product from a successful one and an older valid output may already be damaged.

## Stable rule

Separate construction from publication:

```text
private temporary object -> complete all mutations -> validate -> atomic rename -> success
```

For filesystem outputs, the temporary object should be on the same filesystem as the final pathname. A private sibling directory is often safer than a predictable sibling filename:

- the directory name comes from `mktemp -d`;
- the real producer creates the file inside it with normal umask semantics;
- failure cleanup removes only the private state;
- final publication uses one rename.

## Why direct final-name writes are fragile

When a pipeline writes directly to the final pathname:

- an early stage can truncate an existing product;
- later failure leaves a plausible partial object;
- signal cleanup may remove or retain the wrong state;
- retries cannot distinguish prior success from failed replacement;
- observers can open the file before construction finishes.

A final success message does not create a publication boundary if the name was visible earlier.

## Review checklist

1. Identify the first operation that creates or truncates the output.
2. Enumerate every later operation that can fail.
3. Determine whether an existing output must survive failure.
4. Put the temporary object on the destination filesystem.
5. Preserve intended new-file mode; `mktemp` files are normally 0600.
6. Use quoted, option-terminated rename and cleanup commands.
7. Clear temporary-path state after successful rename.
8. Test absent and existing final paths under injected failure.
9. Test signal cleanup separately from ordinary failure.
10. State symlink, metadata, concurrency, and crash-durability semantics.

## Symlink and metadata semantics

Atomic replacement usually replaces a final symlink rather than following it. That is safer but can differ from in-place writing. A new inode also does not inherit the old file's mode, ownership, ACLs, or xattrs unless the tool implements that policy deliberately.

## Limits

Rename atomicity does not guarantee crash durability. Stronger guarantees require flushing the file and destination directory. It also does not prevent concurrent publishers or validate the completed bytes.

## Related record

- `investigations/qemu-builder-atomic-image/README.md`
- Issue #191
