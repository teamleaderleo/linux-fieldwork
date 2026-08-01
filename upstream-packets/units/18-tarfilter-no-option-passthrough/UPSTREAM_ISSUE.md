# Upstream issue draft

## Title

tarfilter with no options rewrites archives instead of copying them

## Draft

`tarfilter` contains a byte-copy path for invocations without filtering or rewrite options, but the path is unreachable.

`argparse` always creates the `strip_components` attribute for the normal `--strip-components` argument. When the option is omitted, its value is `None`; the current guard checks attribute existence:

```python
and not hasattr(args, "strip_components")
```

That condition is always false. A no-option invocation therefore parses the input and writes a new uncompressed PAX archive.

This changes ordinary compressed inputs byte-for-byte and removes their gzip, bzip2, or xz framing. It also sends GNU PAX sparse input through archive rewriting even though the caller requested no operation.

A bounded correction checks whether each operation is active:

- custom path, PAX, type, and transform actions remain detected by attribute presence;
- strip-components and ID shift are checked by value;
- explicit numeric zero remains a no-op, matching the existing later truthiness checks.

The regression requires byte identity for plain, gzip, bzip2, xz, and GNU PAX sparse archives, plus explicit strip zero and ID-shift zero. Separate controls verify that active path, PAX, type, strip, transform, and ID-shift operations still enter the rewrite path and produce their expected results.

## Evidence boundary

This report concerns only no-operation selection. Sparse-member rewriting during active filtering and other tarfilter path, transform, and PAX semantics remain separate work.

## Contact state

Draft only. External submission requires explicit authorization.
