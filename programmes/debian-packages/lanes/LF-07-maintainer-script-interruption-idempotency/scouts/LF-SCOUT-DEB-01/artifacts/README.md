# LF-SCOUT-DEB-01 retained artifacts

This directory contains the purpose-built Debian package fixture, the repeatable interruption runner, and the retained comparison evidence for LF-07.

## Run

From this directory:

```sh
sh ./run-probe.sh
```

The runner requires root, `dpkg`, `dpkg-deb`, BusyBox at `/usr/bin/busybox`, and ordinary GNU userland tools. It builds the package in a temporary work directory, creates four minimal chroot roots, performs one clean installation plus three interrupted installations, reruns each half-configured package with `dpkg --configure`, and rewrites `results/`.

An optional first argument selects the temporary work directory:

```sh
sh ./run-probe.sh /tmp/lf07-run
```

## Retained files

- `fixture/package/` — package control data, `postinst`, and payload.
- `run-probe.sh` — builds the package, creates disposable roots, injects `SIGTERM`, snapshots state, reruns configuration, and compares outcomes.
- `results/environment.txt` — execution environment.
- `results/fixture.sha256` — input hashes.
- `results/summary.tsv` — compact per-point result table.
- `results/clean.snapshot` — clean-install baseline.
- `results/after-*.snapshot` and `results/after-*.diff` — recovered states and baseline comparisons.
- `results/probe-transcript.txt` — installation, interruption, half-configured-state, and recovery transcript.

The built `.deb` and disposable roots live only in the selected temporary work directory.
