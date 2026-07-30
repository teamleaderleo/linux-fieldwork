# LF-15 — OverlayFS Copy-Up and Metadata Behavior

## In simple words

OverlayFS presents lower and upper files as one view, yet copy-up can change inode identity and metadata relationships. This lane tests assumptions made by package tools, scanners, backup tools, and container workflows.

## Programme

[`Filesystems, archives, and disk images`](../../STATUS.md)

## State

`mapped` — ready after privileged mount capability is confirmed.

## Question

Which application assumptions break when OverlayFS changes inode identity, copies up metadata or data, handles hard links, or redirects directories?

## Why this could matter

A consumer may trust inode identity, hard-link relationships, security xattrs, or rename behavior that differs after copy-up.

## Likely targets

Linux OverlayFS, package managers, container runtimes, file scanners, backup tools, and root filesystem builders.

## First probe

Create lower and upper fixtures covering hard links, open descriptors, xattrs, rename, chmod, chown, and copy-up. Observe inode identity, link relationships, metadata, and data consistency before and after each operation.

## Environment

Privileged CI or a VM with OverlayFS support.

## Promotion signal

Promote when a userspace tool loses a link relationship, trusts unstable inode identity, drops security metadata, or mishandles renamed directories.

## Stop signal

Close when behavior follows documented OverlayFS semantics and the selected consumer already accounts for it.

## Expected outputs

- minimal OverlayFS fixture;
- operation and metadata matrix;
- consumer behavior report;
- candidate investigation or retained compatibility note.

Create `artifacts/` only when evidence is retained.

## Authority

No upstream contact is authorized.