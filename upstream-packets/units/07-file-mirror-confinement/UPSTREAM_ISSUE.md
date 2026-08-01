# Upstream issue draft

Status: internal draft only; external contact is unauthorized.

## Title

`file-mirror-automount can select setup and cleanup targets outside the generated root`

## Draft

The `file-mirror-automount` hook derives mount/copy and cleanup targets by concatenating the generated-root path with text from APT repository URIs or the persisted cleanup marker.

This permits several related failures:

- a repository URI containing parent traversal can resolve outside the generated root;
- an existing symlink below the generated root can redirect the destination outside it;
- a generated-root argument resolving to `/` makes host paths appear contained;
- cleanup can act on valid early marker entries before discovering a later invalid entry;
- canonicalizing a terminal source symlink for both source and destination can make the configured `file:` URI unreachable inside the generated root.

A bounded repair can treat setup and cleanup as one contract:

1. canonicalize the generated root and refuse `/`;
2. reject configured repository paths containing any `..` component;
3. use the canonical existing host source for mount/copy/upload;
4. preserve a normalized configured URI path for the in-root destination;
5. resolve existing destination symlinks and require a strict child of the generated root;
6. store canonical root-relative NUL-delimited marker entries;
7. preflight the complete cleanup marker before any destructive action;
8. revalidate each entry immediately before `umount` or `rm -r`.

Disposable regressions use fake destructive commands and cover traversal, destination-parent symlink escape, root refusal, ordinary repositories and package files, terminal source-symlink reachability, parent-component rejection, complete cleanup preflight, marker retention, and corrected rerun.

The remaining boundary is a privileged concurrent actor replacing path or marker components after validation and before action. Descriptor-relative operations or a private mount namespace would be a larger follow-up design.

## Proposed next step

Prefer opening the prepared pull request directly unless the maintainer requests issue-first discussion. The patch and regression narrative are already bounded enough for code review.
