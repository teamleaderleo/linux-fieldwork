# Directory timestamp authority after rename

Tracking: #392. Related evidence: #380, PR #383. Product candidate: PR #389.

## In simple words

An open directory handle keeps pointing to the same folder even when its old name
is moved or replaced. That prevents a timestamp write from following a new
shortcut. It does not prove the folder still belongs to the temporary root.

This matrix separates **object identity** from **current tree membership**.

## Exact starting point

- evidence base: PR #383 head `169d1d95d58ae362d13aec1f115fb2c0c6c58f16`;
- descriptor candidate executed head: PR #389 `0319755b71ec594f2019cf40cd3cf9ee68ad7d60`;
- descriptor CI: `30656680618` / 1069, success;
- imported/product source changes in this unit: none.

## Policies compared

### A. Open-time authority

A directory opened below the pinned root remains owned until the archive
operation finishes. Rename does not revoke authority. Handle-based `utime`
therefore changes the originally opened inode even after that inode is moved
outside the root.

This policy is immune to pathname redirection and has the broadest retained
authority.

### B. Best-effort current-membership authority

Immediately before mutation, duplicate the directory handle and repeatedly open
`..` relative to the current descriptor. Compare `(device,inode)` identities
until the pinned root is reached or the filesystem root/cycle is reached.

This policy:

- accepts an unchanged directory;
- accepts a rename elsewhere below the same pinned root;
- rejects a directory currently outside the root;
- accepts a directory moved back below the root before the check.

It is still not atomic with timestamp mutation. Moving the directory outside
after the final ancestry check but before handle-based `utime` causes the now
outside inode to be changed.

### C. No pre-tar tree mutation

Rewrite directory headers in the output stream instead of changing the temporary
tree. This avoids tree-membership authority but re-enters archive transformation
risk. LF-14 already showed that the current Python tar rewrite path can damage
GNU PAX sparse members even when the filter exits successfully. A header-only
candidate therefore needs extraction, PAX, xattr, link, sparse, and format
controls before it can outrank a quiescent-tree policy.

This unit records C as the non-mutating alternative; it does not implement or
select it.

## Executed matrix

`tests/test_mmdebstrap_directory_mtime_authority.py` uses real Linux directory
file descriptors and deterministic renames.

It proves:

1. open-time authority changes the same inode after an out-of-root rename while
   an old-path symlink target remains unchanged;
2. current-membership accepts no movement and in-root rename;
3. current-membership rejects out-of-root rename with no replacement;
4. current-membership rejects out-of-root rename followed by a symlink or
   regular-file replacement;
5. moving the same inode back into the root before the check restores current
   membership;
6. moving it outside after a successful check exposes the residual
   check-to-`utime` race;
7. current mmdebstrap calls `setup($options)` before final archive creation and
   later invokes GNU tar with pathname `-C $options->{root}`; the source section
   contains no descendant `waitpid` or descriptor-membership validation between
   those points.

## Process-ownership interpretation

The source establishes an **ordering** boundary: `setup()` returns before final
tar creation. It does not, by itself, prove that every package/helper descendant
is gone or incapable of renaming the tree. The final GNU tar traversal is also
pathname-based and therefore already assumes that the completed root remains
stable enough to archive.

Do not turn that observation into an invented quiescence guarantee. A separate
process-tree execution must determine whether any owned descendants remain at
this boundary.

## Current decision

Best-effort membership is strictly narrower than open-time authority, but it
cannot close the final race. Adding it to PR #389 would add complexity without
creating a complete membership guarantee.

The next product decision has two honest paths:

1. **quiescent-tree premise:** prove no owned descendant can rename the tree
   after `setup()` and treat opened inodes discovered during final archive
   preparation as operation-owned until the archive finishes; or
2. **no-tree-mutation implementation:** normalize archive directory headers with
   complete archive-format controls.

Until one path wins, PR #389 remains mechanically green but not sid-ready.

## Stop/reopen rule

Stop membership-check implementation work here. Reopen it only if a concrete
failure model shows that the narrowed residual race is acceptable while
open-time authority is not.

Continue with one bounded archive-boundary process-tree probe. If that probe
finds no live owned descendants across repeated root/chrootless executions, the
quiescent-tree premise becomes testable. If descendants remain, investigate
their ownership and shutdown before selecting pre-tar mutation.

## Authority

Internal source reading and disposable local/hosted filesystem controls only. No
merge, package publication, release, deployment, credential use, spending, or
public-upstream interaction is authorized or performed.
