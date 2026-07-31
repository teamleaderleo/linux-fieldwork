# Archive reproducibility must separate directory and file mtimes

A global timestamp-normalization flag can make two archives byte-identical while
destroying metadata that packages intentionally supplied on regular files.
Conversely, a clamp policy can preserve legitimate file mtimes while allowing
directory timestamps to differ solely because two construction modes create the
same directories at different times.

When a reproducibility comparison fails on timestamps:

1. compare member paths and types before changing policy;
2. classify directory and non-directory mtimes separately;
3. retain a regular file with a deliberately old mtime as a reversing control;
4. test full normalization, directory-only normalization, and comparison-only
   normalization independently;
5. treat archive filters as format transformations that need sparse, PAX, xattr,
   link, and extraction controls;
6. do not weaken a byte-identity assertion merely because contents match;
7. do not normalize all members merely because it makes the test green.

The narrow repair is the one that removes the construction-mode variance while
preserving unrelated metadata contracts.
