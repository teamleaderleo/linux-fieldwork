# Priority-zero upstream packet index

Canonical initiative: issue #397.

This index maps each contribution unit to its durable packet directory. Issue #397 remains authoritative for priority and scope. The packet directory becomes authoritative for the unit's technical state after it is created.

| Unit | Tranche | Contribution unit | Initial state | Packet directory |
| ---: | ---: | --- | --- | --- |
| 00 | 0 | mmdebstrap: explicit `TMPDIR` is honored without silent fallback | SENT; record closeout | `units/00-mmdebstrap-explicit-tmpdir/` |
| 01 | 1 | mmdebstrap tarfilter: GNU basic and extended transform regex compatibility | Near release | `units/01-tarfilter-regex-dialects/` |
| 02 | 1 | mmdebstrap caching_proxy: complete request, response, and atomic-cache repair | Composed; rebase and package | `units/02-caching-proxy-complete-repair/` |
| 03 | 1 | mmdebstrap gpgvnoexpkeysig: complete verifier-wrapper lifecycle | Composed; real fixture needed | `units/03-gpgvnoexpkeysig-lifecycle/` |
| 04 | 1 | mmdebstrap QEMU image builder: atomic publication and terminating signals | Internally complete; upstream extraction needed | `units/04-qemu-image-builder-lifecycle/` |
| 05 | 1 | mmdebstrap run_qemu.sh: host, guest, signal, and cleanup precedence | Internally complete; upstream extraction needed | `units/05-run-qemu-result-precedence/` |
| 06 | 2 | mmdebstrap chrootless maintainer-script boundary hardening | Composition or justified split needed | `units/06-chrootless-maintainer-boundary/` |
| 07 | 2 | mmdebstrap file-mirror-automount: setup and cleanup confinement | Focused candidate; current rebase needed | `units/07-file-mirror-confinement/` |
| 08 | 2 | mmdebstrap package tests: current-sid phase-correct execution | Compose product test corrections | `units/08-current-sid-package-tests/` |
| 09 | 2 | mmdebstrap package tests: declare `bsdutils` for `dev-ptmx` | Small bounded candidate | `units/09-dev-ptmx-bsdutils/` |
| 10 | 2 | mmdebstrap package tests: exact subordinate-ID account matching | Small bounded candidate | `units/10-subid-exact-match/` |
| 11 | 2 | mmdebstrap coverage.py: cancellation owns selected backend group | Narrow candidate review-ready | `units/11-coverage-backend-cancellation/` |
| 12 | 2 | mmdebstrap proxysolver: faithful ordinary and signal results | Compose small source unit | `units/12-proxysolver-result-propagation/` |
| 13 | 2 | mmdebstrap make_mirror.sh: top-level signal and proxy ownership | Select final composed lifecycle | `units/13-make-mirror-top-level-lifecycle/` |
| 14 | 2 | mmdebstrap make_mirror.sh: update_cache worker-owned cleanup | Extract final composed worker lifecycle | `units/14-make-mirror-update-cache/` |
| 15 | 2 | mmdebstrap tarfilter: transform, target, and PAX metadata semantics | Substantial internal composition | `units/15-tarfilter-transform-metadata/` |
| 16 | 2 | mmdebstrap tarfilter: type-excluded hard-link dependency handling | Resolve final-name identity and compose | `units/16-tarfilter-type-hardlinks/` |
| 17 | 2 | mmdebstrap archive output: deterministic directory mtimes | HOLD: operation-authority policy | `units/17-directory-mtime-authority/` |
| 18 | 3 | mmdebstrap tarfilter: byte-preserving no-option passthrough | READY FOR AUTHORIZATION | `units/18-tarfilter-no-option-passthrough/` |
| 19 | 3 | mmdebstrap tarfilter: preserve shifted PAX uid/gid semantics | Clear fix; candidate needed | `units/19-tarfilter-pax-idshift/` |
| 20 | 3 | mmdebstrap tarfilter: preserve dotfile identity during normalization | Clear fix; candidate needed | `units/20-tarfilter-dotfile-identity/` |
| 21 | 3 | mmdebstrap tarfilter: retain parent metadata for nested includes | Design and compatibility matrix needed | `units/21-tarfilter-parent-metadata/` |
| 22 | 3 | mmdebstrap tarfilter: treat NUL and `0` as regular-file types | Small bounded fix | `units/22-tarfilter-regular-type-class/` |
| 23 | 3 | util-linux lscpu: derive cpuset ownership from owning mount | Destination/adoption decision | `units/23-util-linux-lscpu-cpuset/` |

## Claim and creation rule

When beginning unit `NN`:

1. refresh issue #397 and the linked canonical carriers;
2. comment `CLAIMED — unit NN` with the proposed Linux Fieldwork branch;
3. create `upstream/unit-NN-short-slug` from current `main`;
4. copy `_template/` into the exact packet directory shown above;
5. fill every identity field that is already knowable before changing source;
6. update the packet and `HANDOFF.md` continuously;
7. post a `UNIT CHECKPOINT` on #397 after the first durable commit.

A claim is visibility, not an exclusive reservation. Competing variants use different branches and identify themselves in the packet.

## Sequential focus

Default pickup order is the first unfinished unit in the lowest active tranche. A worker may take a later unit when an earlier unit is already active or technically held, but should not start a new broad discovery lane merely because closeout work is less exciting.

## State update rule

Do not rewrite this table for every test run. Update the unit packet and issue checkpoint during active work. Change this index when:

- a packet directory is created or renamed;
- a unit becomes `READY FOR AUTHORIZATION`, `HOLD`, `SPLIT`, `RETIRED`, or `SENT`;
- a canonical successor replaces the unit;
- issue #397 changes the unit boundary.

## Exclusions

DuckDB work is intentionally excluded. Investigations without a selected source correction remain outside this index until issue #397 promotes them into a pull-request-sized unit.
