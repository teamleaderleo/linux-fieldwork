# Boot, Devices, and Deeper Kernel Work

## In simple words

This programme holds VM- and kernel-dependent work around early userspace, hotplug, eBPF, io_uring, and controlled block failures.

## Current direction

- **Inbox:** LF-30 — initramfs dependency discovery and atomic update
- **Inbox:** LF-31 — udev and device hotplug races
- **Inbox:** LF-32 — eBPF verifier and userspace-tool compatibility
- **Inbox:** LF-33 — io_uring cancellation and resource release
- **Inbox:** LF-34 — block fault injection and recovery

## First sequence

Keep these lanes mapped at programme level until a reusable QEMU testbed exists. LF-30 is the strongest first VM lane because it connects directly to Debian package hooks and image generation.

## Candidate targets

`initramfs-tools`, `dracut`, systemd-udevd, Linux BPF and io_uring interfaces, `liburing`, device mapper, filesystems, image builders.

## Authority

Programme mapping grants no upstream-contact authority.