# LF-SCOUT-DEB-01 — Maintainer-script interruption and idempotency

## In simple words

A tiny local Debian package was installed inside disposable roots. Its `postinst` performs four visible actions. The runner terminates the script after each of the first three actions, then asks `dpkg` to continue configuration. Interruption before a deliberately unsafe append converged with a clean installation. Interruption after that append duplicated one registry entry. The fixture therefore distinguishes safe reruns from damaged final state and is ready for use against a compact real package.

## Scout identity and home lane

- Scout-ID: `LF-SCOUT-DEB-01`
- Home lane: `LF-07`
- Assignment: issue `#13`
- Working branch: `scout/lf-scout-deb-01/lf-07-maintainer-script-idempotency`
- Reviewer: `LF-SCOUT-PROC-01`
- Cross-review target: `LF-SCOUT-FS-01` on LF-14 after `READY FOR REVIEW`

## Exact source or package boundary

The tested package is the purpose-built local package `lf-script-idempotency-fixture` version `1.0`, architecture `all`, built only from:

- `artifacts/fixture/package/DEBIAN/control`
- `artifacts/fixture/package/DEBIAN/postinst`
- `artifacts/fixture/package/usr/share/lf-script-idempotency-fixture/payload.txt`

Input hashes are retained in `artifacts/results/fixture.sha256`.

The probe covers `dpkg --install` followed by `dpkg --configure` for one package in isolated roots. It does not cover apt dependency solving, multi-package transactions, upgrades, removals, purges, triggers from other packages, systemd execution, or shutdown during a transaction.

## Package selection rationale

A purpose-built package keeps the first target narrow and makes the interruption points unambiguous. It has four visible side effects and one deliberately non-idempotent action, allowing the harness to demonstrate both convergence and divergence in the same script. No upstream package claim follows from this seeded defect.

## Environment and privileges

The retained run used:

- Debian GNU/Linux 13 (trixie)
- Linux 6.12.13, x86_64
- uid 0
- `dpkg` 1.22.22
- `dpkg-deb` 1.22.22
- BusyBox 1.37.0

The exact record is `artifacts/results/environment.txt`.

Root was used because `dpkg --root` executes maintainer scripts in a chroot. The runner creates a minimal root containing BusyBox, its dynamic loader and libraries, an empty dpkg database, empty passwd and group files, and the directories required by this fixture. It deletes and recreates both the temporary roots and retained result directory on each run.

## Source and test map

### Maintainer-script map

The package contains only `postinst`.

| Order | `postinst configure` action | Visible state | Rerun property |
|---|---|---|---|
| 1 | Write `schema=1` | `/var/lib/lf-script-idempotency-fixture/state` | overwrite, convergent |
| 2 | Append payload registration | `/var/lib/lf-script-idempotency-fixture/registry` | deliberately non-idempotent |
| 3 | Generate configuration | `/etc/lf-script-idempotency-fixture/generated.conf` | overwrite, convergent |
| 4 | Replace an alternative-like symlink | `/usr/local/bin/lf-script-idempotency-fixture-current` | `ln -sfn`, convergent |

There are no `preinst`, `prerm`, or `postrm` scripts. No debhelper-generated snippets are present; the package is assembled directly with `dpkg-deb`.

### Interruption points

The script reads `/run/lf-script-idempotency-fixture/interrupt-after`. At the selected point it removes that one-shot marker, prints the point, and sends `SIGTERM` to itself.

- `after-state`: between actions 1 and 2
- `after-registry`: between actions 2 and 3
- `after-config`: between actions 3 and 4

The first `dpkg --install` returns `1`, records the package as `install ok half-configured`, and reports that the maintainer script was killed by `SIGTERM`. Recovery is:

```sh
dpkg --root="$root" --admindir="$root/var/lib/dpkg" \
  --configure lf-script-idempotency-fixture
```

## Probe design and distinguishing outcomes

Each case begins from a newly created root.

1. Build the package from the retained fixture.
2. Install once without interruption and capture the clean baseline.
3. For each interruption point, write the one-shot marker and run `dpkg --install`.
4. Confirm the interrupted package state is `install ok half-configured`.
5. Run `dpkg --configure lf-script-idempotency-fixture`.
6. Capture the final state and compare it byte-for-byte with the clean baseline.

A sound interruption before the append should produce one registry line after recovery. Interruption after the append should produce two lines because configuration starts again from the top. Deterministic overwrites and `ln -sfn` should otherwise converge.

The snapshot covers:

- dpkg package status, version, and architecture;
- relevant file types, modes, hashes, contents, and symlink target;
- passwd and group hashes;
- service entries;
- alternatives entries;
- cache entries;
- generated configuration.

## Commands or scripts

Run from the report's `artifacts/` directory:

```sh
sh ./run-probe.sh
```

The runner performs syntax checks, builds the package, creates the roots, executes all four installation cases, captures evidence, and prints `results/summary.tsv`.

## Clean baseline

The clean installation reached `Status: install ok installed` and produced:

- one state marker containing `schema=1`;
- one registry line pointing to the payload;
- one generated configuration file;
- one symlink pointing to the installed payload;
- the installed payload file;
- unchanged empty passwd and group files;
- no service, alternatives-database, or cache entries.

The full baseline is `artifacts/results/clean.snapshot`.

## Observed results

| Point | First install | Pre-recovery package state | Final comparison | Registry lines |
|---|---:|---|---|---:|
| `after-state` | rc 1, killed by `SIGTERM` | `install ok half-configured` | converged | 1 |
| `after-registry` | rc 1, killed by `SIGTERM` | `install ok half-configured` | diverged | 2 |
| `after-config` | rc 1, killed by `SIGTERM` | `install ok half-configured` | diverged | 2 |

`after-state` has an empty diff. The other two comparisons differ only in the registry: the recovered file contains the payload line twice and has a different SHA-256 digest. Package state, state marker, generated configuration, symlink, payload, users/groups, services, alternatives, and caches match the clean baseline.

The compact table is `artifacts/results/summary.tsv`; full comparisons are retained as `after-*.snapshot` and `after-*.diff`. `artifacts/results/probe-transcript.txt` records the signal termination and recovery command output.

## Interpretation

The interruption mechanism works at meaningful boundaries and leaves dpkg in the expected half-configured state. A later `dpkg --configure` reruns the whole `postinst configure` path. Deterministic replacement operations converge. An append without an existence check duplicates state when the prior run reached that action.

The fixture catches a seeded idempotency defect while preserving a convergent control point. That makes it useful for the next stage: adapt the same one-shot signal mechanism to a compact real package and map any debhelper-generated sections before making a package-specific claim.

## Recovery commands and manual repair

Normal recovery for all points was:

```sh
dpkg --root="$root" --admindir="$root/var/lib/dpkg" \
  --configure lf-script-idempotency-fixture
```

This command restored dpkg's package state to `install ok installed` in every case.

For `after-registry` and `after-config`, package configuration completed while duplicated state remained. Matching the clean baseline requires manual removal of the extra registry line, for example by replacing the registry with one canonical line and rerunning the comparison. The runner does not perform that repair because the duplicate is the distinguishing observation.

## Evidence limits

- The package and defect are purpose-built and local.
- The minimal roots contain BusyBox instead of a complete Debian userland.
- Only initial installation and configuration are covered.
- The kill occurs inside `postinst`; dpkg itself remains alive.
- No concurrent package action, trigger chain, service manager, user creation, alternatives database update, or cache helper is exercised.
- Filesystem durability across power loss is outside this probe.
- A complete apt or dpkg transaction-recovery claim requires a broader fixture and real package targets.

## Promotion or stop decision

**Decision: `retain`.**

Retain the fixture and comparisons as a proven interruption harness. It detects the intended duplicate state and confirms a convergent control point. Broaden next to one compact real package before promoting any Debian-package finding.

## Upstream authority state

No upstream contact is authorized. No external issue, email, patch, merge request, or maintainer interaction was made.
