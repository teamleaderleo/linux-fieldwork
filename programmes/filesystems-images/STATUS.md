# Filesystems, Archives, and Disk Images

## In simple words

This programme studies how Linux tools turn archives and block images into filesystems while preserving path containment, ownership, metadata, durability, and cleanup.

## Current direction

- **Mapped:** [LF-14 — archive extraction and metadata contracts](lanes/LF-14-archive-extraction-metadata-contracts/brief.md)
- **Mapped:** [LF-15 — OverlayFS copy-up, hard links, xattrs, and rename](lanes/LF-15-overlayfs-copy-up-metadata/brief.md)
- **Inbox:** LF-16 — rename, fsync, and crash durability
- **Inbox:** LF-17 — temporary files and directory contracts
- **Inbox:** LF-18 — disk-image dissection, growth, and cleanup
- **Inbox:** LF-19 — verified and authenticated root images

## First sequence

Build the archive corpus under LF-14 first. Use its fixtures when LF-15 or later image work needs repeatable metadata cases. VM-backed durability and device-mapper lanes stay queued until the lighter fixtures are reliable.

## Candidate targets

`mmdebstrap`, GNU tar, `libarchive`, `dpkg-deb`, Linux OverlayFS, `systemd-dissect`, `cryptsetup`, device mapper.

## Authority

Programme mapping grants no upstream-contact authority.