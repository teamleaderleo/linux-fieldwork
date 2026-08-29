# GL.iNet Netify same-priority start ordering

## In simple words

On Beryl 7 firmware 4.9.0, an unused Netify detector survives boot because two
vendor services have the same startup priority. OpenWrt's process manager runs
the sorted names one at a time:

```text
S99gl_dpi
  all three DPI consumers are off -> stop Netify (not started yet)

S99gl_dpi_flow_statistics
  does not start or stop Netify

S99netifyd
  enabled instance -> start Netify
```

The result is deterministic rather than a race. The live detector used about
21.5 MiB RSS on a 512 MiB router and remained active despite every user-facing
DPI consumer being off.

Moving only Netify from `START=99` to `START=98` is the smallest source
candidate: Netify starts first, then `gl_dpi` stops it when all consumers are
off and leaves it running when QoS, flow statistics, or content protection is
on. The executable model proves those four states. No package containing that
candidate has been built, installed, or reboot-tested, so it is not presented
as a verified firmware fix.

## Current state

- State: `COMPLETE` for the ordering diagnosis and reduced candidate model
- Exact source boundary: live package/script identities below; Fieldwork parent
  `aa30056c9a174b9293597c5912cdfe7dc06d6b35`
- Latest authoritative gate: `python3 boot_order_model.py`; 12 decision rows
  printed and all eight flag combinations asserted for each variant, model
  SHA-256
  `afe77675d128faeec4f45512b083db20f89ed48deac670176e85f2a9b3be77fb`
- First incomplete step: package-level `START=98` canary across an attended
  reboot and each real DPI consumer
- Cleanup state: model writes nothing; no router process, link, service,
  package, route, or configuration changed during this investigation
- Next safe action: keep the current disable-only mitigation while all three
  consumers remain off; re-enable Netify before enabling any one of them
- External-contact state: no GL.iNet or OpenWrt contact authorized or made

## Intent and operation owner

This is a GL.iNet package-ordering defect, not an OpenWrt `procd` defect.

The exact installed `procd` revision uses `glob()` for `/etc/rc.d/S*`, does not
request `GLOB_NOSORT`, adds the returned paths in order, and sets the startup
run queue to one task. POSIX specifies sorted pathnames when `GLOB_NOSORT` is
absent. PID 1 exposed no `LC_ALL`, `LC_COLLATE`, or `LANG` variable, so no
locale override changes the default boot collation. The installed `rc.common`
generates a link by concatenating `S`, the declared priority, and the service
name.

The vendor scripts then disagree about lifecycle ownership:

- `gl_dpi` reads the three product flags and stops Netify only when all are
  zero;
- `netifyd` independently owns an enabled instance and starts it whenever its
  own boot link runs;
- both declare `START=99`, so the service names become the tie-breaker;
- `gl_dpi_flow_statistics` also declares `START=99`, but exact source review
  found no Netify start/stop operation in that sibling.

That architecture makes “Netify first, policy controller second” the local
ordering needed by the current scripts. A larger design could instead give the
controller complete start/stop ownership and remove Netify's independent boot
link, but current `gl_dpi` has no start branch when a consumer is enabled. The
live disable-only mitigation therefore cannot safely become an unconditional
package default.

Primary contracts:

- exact installed procd source:
  [`rcS.c` at `2cfc26f8456a4d5ba3836c914a742f3d00bad781`](https://github.com/openwrt/procd/blob/2cfc26f8456a4d5ba3836c914a742f3d00bad781/rcS.c)
- pathname ordering:
  [POSIX `glob()`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/glob.html)

## Source boundary

Live owned router, inspected read-only on 2026-08-29 Asia/Shanghai:

- GL.iNet Admin Panel 4.9.0
- OpenWrt `21.02-SNAPSHOT`; Linux `5.4.281`; `aarch64`
- BusyBox `1.33.2-4`; base-files `1462`
- procd `2021-03-08-2cfc26f8-2`, resolved upstream commit
  `2cfc26f8456a4d5ba3836c914a742f3d00bad781`
- `gl-sdk4-dpi 1.0.2-git-2026.183.32762-bb1f1e7`
- `netifyd 2026-01-01-v5.2.1-1`

Exact installed script hashes:

```text
91e806ba6783b84a70e153ed5b8542c5b540a90414dcce37a6e3a7e95e5f1e64  gl_dpi
f31aa8079544d5222224494cb9549bd4fae13c91fd843173b44d250210cd3005  gl_dpi_flow_statistics
191db87a6210eac237ab454054d248356e37b875cadb067fd5c130aca52b5030  netifyd
ebeeedc132a75942ce876465e4636a75f745e468c573fdf9ad058e57e58a0341  rc.common
```

The vendor scripts were inspected in place under `/etc/init.d`; they are not
copied into this repository. No imported OpenWrt tree is used. The exact
upstream procd blob and package commit are sufficient for the generic ordering
contract; the hashes above bind the device-specific transitions.

The reduced model ran on Big Red with Ubuntu 26.04.1, Linux x86-64, Python
3.14.4, and ordinary user privileges. It starts no service and needs no router
access.

## Baseline evidence

Before mitigation, the live boot had this final state:

- QoS priority, flow-statistics, and content-protection flags were each `0`;
- `ubus call gl-dpi get_dpi_status` returned status `0`;
- the Netify config contained one enabled instance;
- `netifyd` was enabled independently and remained resident at about
  21.5 MiB RSS;
- the detector logged repeated license-file and occasional netlink-buffer
  errors despite the three product consumers being off.

Disabling only Netify's independent autostart and stopping it raised available
memory from about 75 MiB to about 99 MiB. Tailscale, IP egress, and the
OpenClash resolver stayed responsive. The router currently retains
`K1netifyd` for shutdown semantics but no `S99netifyd` start link.

This live result supplies the real final-state observation. The source and
model below explain why it occurs without requiring another router reboot.

## Distinguishing model

[`boot_order_model.py`](boot_order_model.py) fixes the exact service names and
models only the two operations that can change Netify state:

1. `gl_dpi` stops Netify when all three flags are zero;
2. an enabled `netifyd` boot entry starts Netify.

It includes the flow-statistics sibling as a closed pass-through and refuses
unknown service names. Run:

```sh
python3 investigations/glinet-netify-start-order/boot_order_model.py
```

The four decision rows are all-off plus each consumer enabled alone:

| Variant | All off | QoS only | Flow only | Content only |
| --- | --- | --- | --- | --- |
| current `S99` tie | running | running | running | running |
| Netify `START=98` | stopped | running | running | running |
| independent Netify disabled | stopped | stopped | stopped | stopped |

The current row reproduces the real unused resident process. The `START=98`
row is the negative control that changes the all-off result without damaging
the three enabled-consumer rows. The disable-only row explains the operational
rollback boundary.

## Interpretation

The defect is saturated inside the exact firmware/package boundary:

- same-priority names, sorted and executed serially, establish the startup
  order;
- exact vendor source establishes the two state transitions and the sibling's
  non-interference;
- the historical live final state matches the predicted current row;
- changing only the priority makes the model lose its all-off failure while
  preserving every single-consumer control.

`START=98` is therefore the smallest source candidate and has a smaller
reasoning radius than redesigning service ownership. An update-safe repair
belongs in the vendor package rather than another local edit that firmware or
package updates can overwrite.

## Evidence boundary and reopen conditions

This investigation proves ordering and the reduced state transition. It does
not prove:

- a rebuilt GL.iNet package installs or survives sysupgrade correctly;
- actual QoS, flow statistics, or content protection works after `START=98`;
- boot timing, process readiness, database state, hardware acceleration, or
  memory behavior under those enabled features;
- the same hashes or behavior on another firmware/model;
- that the adjacent flow-statistics monitor has no independent resource issue;
- indefinite success of the separate live Tailscale memory mitigation.

Reopen the diagnosis if a current-firmware boot runs `S99netifyd` before
`S99gl_dpi`, if another exact init owner starts or stops Netify, or if one of
the source hashes changes. Treat package/reboot validation as a successor
execution gate, not missing evidence for the demonstrated current ordering.

## Decision

Retain the current live mitigation while all three consumers remain off. Before
enabling any DPI consumer, re-enable Netify's independent boot entry and verify
that feature across a reboot.

If GL.iNet package testing is later authorized in an attended window, compare
the unchanged package against only `netifyd START=98`, then require all-off and
each single-consumer state, process count, memory, DNS/routing, Tailscale, and
OpenClash to pass. Do not combine that canary with a firmware, OpenClash, radio,
or route-policy update.

No upstream issue, patch, email, comment, or other external interaction is
authorized or made.
