# LF-02 privileged host integrations follow-up

This follow-up starts from LF-SCOUT-ROOT-01's promoted chrootless `DPKG_ROOT` result and tests the two strongest adjacent host effects under a disposable privileged caller. Draft PR #22 targets a CI-only base branch containing the workflow definition, leaving the review-ready LF-02 branch unchanged.

The post-run correctness and evidence-quality review is retained in [`AUDIT.md`](AUDIT.md). It records one medium-severity raw-summary bug, lower-severity provenance/schema improvements, and informational coverage limits. The central host-mutation and inhibitor findings remain unchanged.

## Questions

1. Does Ubuntu's host dpkg `status-logger` successfully modify `/run/needrestart/unpacked` when the chrootless transaction has root authority?
2. Does `DPkg::Inhibit-Shutdown "false"` remove apt's host system-D-Bus/logind interaction without changing target package state?
3. When both apt inhibitors and the host `needrestart` dpkg configuration are disabled, does the same target transaction complete without either observed host-service action?

## Why this control exists

APT acquires a systemd-logind inhibition lock while running dpkg. Its supported boolean controls are `DPkg::Inhibit-Shutdown` and, in newer APT releases, `DPkg::Inhibit-Sleep`. The first LF-02 trace decoded the exact D-Bus call as a blocking shutdown inhibitor requested by `APT` for the reason `APT is installing or removing packages`.

The `needrestart` effect comes through a separate path: Ubuntu's host `/etc/dpkg/dpkg.cfg.d/needrestart` configures `/usr/lib/needrestart/dpkg-status` as dpkg's `status-logger`. Chrootless dpkg reads host configuration before command-line root options, so the logger executes on the host side.

## Matrix

The workflow runs the imported `mmdebstrap` source three times in `chrootless` mode with the LF-02 local package fixture:

| Case | Apt shutdown/sleep inhibitors | Host dpkg needrestart logger |
|---|---|---|
| `default-root` | enabled | enabled |
| `no-inhibit-root` | disabled with target apt options | enabled |
| `isolated-root` | disabled | temporarily moved aside and restored |

Every case uses a fresh target, `--variant=custom`, the local `.deb`, `--skip=update,check/chrootless`, and syscall tracing. The runner compares normalized maintainer-script and alternatives state across all three cases.

## Host safety

The GitHub-hosted runner is disposable. Even so, the script snapshots and restores `/run/needrestart/unpacked`, restores `/etc/dpkg/dpkg.cfg.d/needrestart` through an exit trap, and confines package payload effects to fresh target directories. No external project is contacted.

## Run

```sh
sudo -E bash investigations/lf-02-privileged-host-integrations/run.sh
```

Results are written to `investigations/lf-02-privileged-host-integrations/results/` and uploaded by the dedicated workflow.
