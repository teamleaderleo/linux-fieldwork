# kmod target map

## TL;DR

kmod is the userspace layer that resolves Linux kernel-module names, aliases, dependencies, configuration, insertion, removal, metadata, and generated indexes. It is a strong Linux Fieldwork target because its testsuite can fake module syscalls, `uname()`, and filesystem roots, allowing realistic module-management behavior to be exercised without loading anything into the host kernel.

The first active investigation is [`../../investigations/kmod-modprobe-options-config-path/`](../../investigations/kmod-modprobe-options-config-path/). It found that a `-C` configuration directory containing spaces is used correctly by the parent `modprobe`, but is serialized into `MODPROBE_OPTIONS` without quoting. A nested `modprobe` launched by an `install` rule silently falls back to default configuration while both levels exit successfully.

## Why this target matters

kmod sits on boot, device discovery, initramfs generation, driver policy, kernel-module packaging, and service startup paths. Small mistakes can change which module is selected, whether a blacklist applies, which dependencies are included in an initramfs, or whether parent and nested module operations use the same policy.

## Exact current source identity

- Project: kmod
- Canonical repository: `https://git.kernel.org/pub/scm/utils/kernel/kmod/kmod.git`
- GitHub mirror: `https://github.com/kmod-project/kmod.git`
- Mirror default branch: `master`
- Master observed 2026-08-01: `5086df53090b2fe9fa1c31351c05a78a12a4ba71`
- Local executable under the first investigation: Debian `kmod 34.2-2`, `/usr/sbin/modprobe`

The GitHub mirror is used for source reading. Revalidate the canonical git.kernel.org head before any upstream-shaped candidate or publication decision.

## Source map

### Command tools

- `tools/modprobe.c` — command-line parsing, `MODPROBE_OPTIONS`, recursive install/remove behavior, insertion and removal orchestration, dry-run/show output.
- `tools/depmod.c` — module dependency and index generation.
- `tools/modinfo.c` — module metadata, signatures, exports, and version information.
- `tools/insmod.c`, `tools/rmmod.c`, `tools/lsmod.c` — lower-level command surfaces.

### Library

- `libkmod/libkmod.c` — context creation, resource loading, logging, and top-level library ownership.
- `libkmod/libkmod-config.c` — aliases, options, blacklists, install/remove commands, soft dependencies, weak dependencies, and configuration precedence.
- `libkmod/libkmod-module.c` — lookup, dependency traversal, insertion/removal behavior, init state, holders, and module metadata.
- `libkmod/libkmod-index.c` — binary module indexes and lookup behavior.
- `libkmod/libkmod-file.c` — module file access, compression, signatures, and related file handling.

### Shared helpers

- `shared/` — arrays, strings, paths, temporary files, logging, and common option helpers.

### Tests

- `testsuite/README.md` — intended test architecture.
- `testsuite/test-modprobe.c` — command behavior and configuration interaction.
- `testsuite/test-libkmod.c` — library lookup, dependencies, blacklists, softdeps, weakdeps, state, and removal behavior.
- `testsuite/rootfs-pristine/` — synthetic configuration and index roots.
- `testsuite/module-playground/` — generated fixture modules.
- preload/fake syscall helpers — replace `init_module()`, `delete_module()`, filesystem access, and `uname()` so tests can run without host-kernel mutation.

## High-yield boundaries

1. **Recursive configuration identity** — parent `modprobe` versus nested `modprobe` launched by install/remove rules; argv serialization and configuration-path precedence.
2. **Alias and policy ordering** — aliases, blacklists, options, install commands, softdeps, weakdeps, and kernel-command-line policy.
3. **Dependency completeness** — depmod indexes, built-in modules, weak dependencies, cycles, duplicate providers, and initramfs-facing `--show-depends` output.
4. **Representation compatibility** — plain, XZ, Zstandard, and other module-file representations; signatures, exports, modversions, and malformed/truncated inputs.
5. **Removal lifecycle** — holders, reference counts, pre/post softdeps, wait behavior, first failure, and cleanup order.
6. **Index publication and freshness** — generated text/binary indexes, alternate output roots, quick mode, stale indexes, and partial publication.
7. **Cross-libc and cross-toolchain behavior** — glibc, musl, GCC, Clang, linker-section ordering, and testsuite discovery.

## Current local capabilities

Observed environment for the first probe:

```text
Linux 6.12.13 x86_64
Debian kmod 34.2-2
/usr/sbin/modprobe SHA-256 a775c12b9d71d9548654ff98ecc0e5e3378bdaccd52ccb62fa80a5f41e849caf
GCC 14.2.0
Clang 17.0.0
```

A Debian module tree is available under `/lib/modules/6.12.74+deb13+1-amd64`, but matching kernel headers and Meson were not available in the first runtime. The retained recursive-config probe requires neither headers nor kernel module insertion.

## Active investigation

- [`../../investigations/kmod-modprobe-options-config-path/`](../../investigations/kmod-modprobe-options-config-path/) — parent/nested configuration identity when `-C` contains whitespace.

## Candidate follow-ups

- Run the current upstream testsuite with its fake syscall/rootfs harness against GCC and Clang.
- Compare alias/blacklist/install/softdep ordering through both libkmod and `modprobe --show-depends`.
- Exercise depmod output-root publication under interruption and stale-index conditions.
- Build a compressed-module equivalence matrix across XZ and Zstandard.
- Check removal-holder and softdep cleanup ordering with fake loaded-module state.

Each follow-up needs its own discriminator and should not be folded into the recursive-config investigation unless it can change that investigation's mechanism or claim.

## Authority

This map and its investigations authorize only internal source reading and local or owned-system testing. No issue, email, patch, pull request, review, or other upstream interaction is authorized by this record.
