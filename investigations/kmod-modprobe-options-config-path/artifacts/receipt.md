# kmod recursive configuration receipt

## Exact executable and environment

```text
Debian package: kmod 34.2-2 amd64
libkmod package: libkmod2 34.2-2 amd64
modprobe: /usr/sbin/modprobe
modprobe SHA-256: a775c12b9d71d9548654ff98ecc0e5e3378bdaccd52ccb62fa80a5f41e849caf
kernel: Linux 6.12.13 x86_64 GNU/Linux
```

No kernel module was inserted or removed. The synthetic `install` rule replaced insertion with a temporary helper that recorded the environment and invoked `modprobe -c`.

## Root run

```text
script SHA-256: 8006c8cb24ef44803565fb580bd9334edb807e210f3a5c0f313679f260c211c1
result SHA-256: c6ffd6ac62937b2ceb78786fe3b7610b5125f91db356f1f747c69fe4fe8286bc
status: 0
```

Distinguishing fields:

```text
no-space direct marker: 1
no-space parent status: 0
no-space nested status: 0
no-space nested marker: 1
no-space MODPROBE_OPTIONS: -C $TMP/no_space/confdir

spaced direct marker: 1
spaced parent status: 0
spaced nested status: 0
spaced nested marker: 0
spaced MODPROBE_OPTIONS: -C $TMP/space/conf dir
```

## Immediate rerun

```text
rerun SHA-256: c6ffd6ac62937b2ceb78786fe3b7610b5125f91db356f1f747c69fe4fe8286bc
byte comparison with first normalized result: identical
status: 0
```

Temporary pathnames are normalized to `$TMP`, so byte identity compares behavior rather than random temporary-directory names.

## Unprivileged control

Command:

```sh
runuser -u nobody -- python3 test_modprobe_options_config_path.py
```

Result:

```text
EUID: 65534
result SHA-256: 759550141d24d03543d0686b235e82b0aab8015181b50bddb169e9d297acd9cf
status: 0
no-space direct/nested markers: 1 / 1
spaced direct/nested markers: 1 / 0
parent and nested statuses: 0 / 0
```

The different whole-file hash is expected because the receipt records EUID. The decision-changing fields match the root run.

## Parser controls

```text
normal single-quoted spaced path: status 0, marker 1
leading/repeated spaces: status 0, marker 0
tab separator: status 0, marker 0
unmatched quote: status 0, marker 0
```

The quoted control proves that spaced paths are accepted when their argv identity survives parsing. The other controls show that status-only checks cannot distinguish several parser failures.

## Cleanup

The Python `TemporaryDirectory` removed every configuration directory, helper, environment receipt, nested output, and status file after each run. No child process, module, mount, socket, lock, or persistent configuration remained.
