# Test carrier — vmspawn ordinary-user bind startup

## Exact identities

- Canonical systemd base: `ac33190d1f66e870d511827cbed3ebeee2d704c2`
- Controlled fork: `teamleaderleo/systemd`
- Branch: `research/vmspawn-unmapped-bind-userns`
- Current test-only head: `8a2d77b08f511d30a9cb81c9f2c147dfd5aa638b`
- Test path: `test/units/TEST-87-AUX-UTILS-VM.vmspawn-user-bind.sh`
- Product source changed: no
- Canonical-project contact: none

## Purpose

Create the first failing discriminator before changing `src/vmspawn/vmspawn.c`.

The public issue uses a bootable image and a guest-visible host/guest probe. That is the strongest end-to-end gate, but it requires a prepared guest image. The first controlled test isolates the earlier host-side transition:

- baseline exits before executing virtiofsd because `namespace_enter()` receives an invalid user-namespace fd from an unprivileged process;
- a guarded path should start virtiofsd, reach QEMU, and remain alive until the test's external timeout.

## Harness conventions used

The test follows nearby TEST-87 and systemd shell-test conventions:

- `set -eux` plus `pipefail`;
- sources `test/units/util.sh`;
- uses `find_qemu_binary`;
- skips under ASan;
- locates `virtiofsd` in PATH, `/usr/libexec`, or `/usr/lib`;
- locates the current direct-boot kernel using the same path sequence as the existing vmspawn test;
- runs as the standard integration-test `testuser` through `runas()`;
- enables linger and starts `user@UID.service` so `XDG_RUNTIME_DIR` is usable;
- forces TCG with `--kvm=no` and disables vsock to avoid host-device permissions;
- uses `--register=no`, `--keep-unit`, and `--notify-ready=no` to avoid unrelated registration and guest-readiness dependencies;
- uses a unique machine name and process cleanup fallback.

## Fixture

The root disk is a 64 MiB sparse raw file with no filesystem. That is intentional: the guest does not need to boot for this gate.

The ordinary user owns:

- the sparse raw disk;
- a bind source directory;
- a `host-probe` file inside the bind source.

The command receives:

- `--user`;
- `--image=<sparse raw disk>` so the root disk itself does not require virtiofsd;
- `--bind=<ordinary directory>` so the runtime mount takes the unmapped bind path;
- direct kernel boot;
- no KVM, vsock, TPM, registration, or ready notification.

## Classification

The command is wrapped in an eight-second timeout.

### Expected baseline

- vmspawn exits before the timeout;
- log contains `Failed to enter user namespace for virtiofsd: Operation not permitted`;
- test exits nonzero and retains the failure in CI output.

### Expected candidate

- vmspawn reaches its long-running QEMU phase;
- external timeout returns status 124;
- test passes.

### Neutral environment result

The test skips when the installed QEMU lacks usable `vhost-user-fs` support. Other early exits are failures, not silent skips.

## Why this is not the final regression

This startup gate proves that an ordinary unmapped bind no longer dies before virtiofsd exec. It does not prove the guest can mount the share or read its contents.

The next stronger gate should use a bootable TEST-87 image and require this sequence:

1. guest reads the exact `host-probe` contents through the bind;
2. guest creates `guest-probe` in the same share;
3. host observes `guest-probe` after vmspawn exits;
4. translated UID and foreign-UID controls continue to pass.

## Candidate boundary

Only after the baseline failure is retained should product code be changed. The narrow candidate remains:

- skip `namespace_enter()` when `userns_fd` is invalid;
- preserve namespace entry for translated and foreign-UID paths;
- leave the general `namespace_enter()` capability contract unchanged;
- assess the helper's `block_dlopen()` side effect separately rather than invoking an invalid namespace operation for incidental hardening.

## Open review questions

- Is `--keep-unit` preferred for this nested ordinary-user test, or should a dedicated user scope be retained and explicitly stopped?
- Should unsupported `vhost-user-fs` remain a neutral skip or be covered by a separate QEMU capability probe?
- Which standard TEST-87 bootable image is best for the second guest-visible gate?
- Does the existing integration image guarantee `testuser` and user-manager support on every TEST-87 architecture?
- Should the host-side test assert the virtiofsd exec boundary directly through logs or `/proc`, in addition to the timeout classification?

## Authority

This is a controlled-fork, test-only carrier. No systemd issue comment, pull request, review, email, or other canonical-project interaction was created.
