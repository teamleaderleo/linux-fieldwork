# `iwlwifi` missed-beacon clusters on Big Red

## In simple words

Big Red's Intel AX203 logged four short clusters in which firmware reported at
least 19 consecutive missed access-point beacons while ordinary data was still
arriving. The running driver deliberately stays connected in that case. It
disconnects only when at least four beacons have also been missed since the
last received packet.

This is worth retaining because 23 of 24 warning pairs occurred without a
NetworkManager state change during one otherwise stable association. It is not
yet a demonstrated Linux defect: the same AP association is now healthy, the
warning has been dormant for about 18 hours, and there is no matching AP-side
event capture. No module, radio, router, service or network setting should be
changed merely to silence or reproduce it.

Tracking: [Linux Fieldwork issue #698](https://github.com/teamleaderleo/linux-fieldwork/issues/698)

## Current state

- State: `MONITORING`
- Exact working parent: `b09dcabb5b9f4e239e5ab460804e41a3c24f5e4a`
- Latest authoritative gate: current-boot journal correlation, exact Ubuntu
  source package `7.0.0-30.30`, live station counters, and a 100-packet LAN
  loss control
- First incomplete step: capture one natural recurrence together with
  before/after station counters and an AP-side radio/event summary
- Cleanup state: the exact Ubuntu source package and selected extracted files
  were held only in a route-owned disk cache during inspection and removed
  after this record became durable; no monitor remains
- Next safe action: wait for a natural recurrence; do not toggle Wi-Fi,
  reload `iwlwifi`, restart NetworkManager, change crypto/power parameters, or
  interrupt SSH to manufacture one
- External-contact state: no upstream contact authorized or made

## Question and competing explanations

Do the warning clusters represent:

1. a driver/firmware beacon-counter anomaly while RX data proves the link is
   still usable;
2. real Beryl/AP beacon suppression or a channel/radio event while ordinary
   data frames continue; or
3. transient radio interference that neither endpoint alone can classify?

A recurrence without an AP event and with stable signal/data counters would
strengthen the first explanation. A matching AP channel, restart, beacon or
radio event would strengthen the second. Changed signal/retry behavior without
either endpoint event would keep the interference explanation live.

## Source and environment

- Host: physical `big-red`
- Distribution: Ubuntu 26.04, x86-64
- Running kernel/package: `7.0.0-30-generic` / `7.0.0-30.30`
- Adapter: Intel Arrow Lake CNVi device `8086:7740`, detected as Intel Wi-Fi 6
  AX203 and driven by `iwlwifi`/`iwlmvm`
- Firmware: `100.d6bb293f.0 bz-b0-hr-b0-100.ucode`
- `linux-firmware`: `20260319.git217ca6e4.1ubuntu`
- NetworkManager: `1.54.3-2ubuntu3`
- Exact source package: `linux-source-7.0.0_7.0.0-30.30_all.deb`, SHA-256
  `cc4a1eb27b03bf384293f203fb7a59850008038d4af4fee77c5e4b6b8e7700aa`
- Upstream comparison: Linux `08dbfad3f5040f5bdb6c529da20d6d4e81fefd72`
  observed during this investigation
- Privileges: ordinary station, journal and package reads; no driver debug
  trigger, packet capture, radio change, package installation or reboot

The selected Ubuntu source files were extracted from the package's inner
source tarball only after its bzip2 integrity check passed. The exact
`mac-ctxt.c` SHA-256 was
`2e679470bfa85ea4138647776a26cd71be3cc1698e349bb0c6122160a912324e`;
the threshold-defining `mvm.h` SHA-256 was
`cfef23c22b7f39a40c7eb541e5ae2166024f58e0acaffa995c9088232cf90310`.

SSID, BSSID, station MAC, local/peer addresses and raw unrelated journal
content are deliberately omitted.

## Exact source mechanism

Ubuntu's running source defines:

```c
#define IWL_MVM_MISSED_BEACONS_SINCE_RX_THOLD 4
#define IWL_MVM_MISSED_BEACONS_THRESHOLD 8
#define IWL_MVM_MISSED_BEACONS_THRESHOLD_LONG 19
```

In `drivers/net/wireless/intel/iwlwifi/mvm/mac-ctxt.c`, a notification with at
least 19 consecutive missed beacons takes one of two branches:

- `consec_missed_beacons_since_last_rx >= 4` calls
  `iwl_mvm_connection_loss()`;
- a smaller since-RX count emits the observed warning and stays connected.

The source has a nearby TODO saying the threshold should account for latency
conditions or channel-switch activity on another AP interface. Current
upstream source at the comparison commit retains the same stay-connected
branch and warning. This establishes that the observed decision is deliberate;
it does not establish whether firmware's beacon counts or the AP behavior are
correct.

## Baseline observations

The boot contained 24 warning pairs across four wall-clock clusters:

| Time (Asia/Shanghai) | Pairs | Consecutive missed | Since last RX | Link event |
|---|---:|---|---|---|
| 2026-08-29 04:44:36 | 1 | 19 | 3 | connection loss and reassociation followed |
| 2026-08-29 14:37:19 | 4 | 19-22 | 1-2 | none |
| 2026-08-29 14:56:48 | 2 | 19-20 | 1-2 | none |
| 2026-08-29 21:18:02-21:18:49 | 17 | 19-28 | 1 | none |

The final association began at boot time 26,358.351 seconds, after the first
cluster, and remained on the same AP. NetworkManager recorded no later state
transition, so the final 23 warning pairs occurred inside one uninterrupted
association. The warning itself did not ask mac80211 to disconnect because
every since-RX count remained below four.

At the final live control that association had lasted 125,827 seconds (about
35 hours). The sanitized station snapshot reported:

- authorized, authenticated and associated;
- signal `-52/-56 dBm`, average `-48 dBm`, beacon average `-41 dBm`;
- 836,318 received beacons and zero current `beacon loss`;
- 9,473,593 transmitted packets, 439,712 retries and zero failed packets;
- negotiated 80 MHz HE rates, with the sampled TX rate at 600.4 Mbit/s.

A 100-packet, five-second LAN control returned 100/100 packets with
0.882/1.422/3.687/0.438 ms minimum/average/maximum/deviation. Ten-minute
sysstat bins around the later clusters showed only about 31-95 KiB/s receive
and 10-47 KiB/s transmit averages. Those coarse bins rule out sustained bulk
traffic, not short bursts or radio contention.

No matching warning occurred after 2026-08-29 21:18:49 through the final
observation roughly 18 hours later.

## Separate warning classes

Eight `Unhandled alg: 0x703/0x707` messages occurred only at initial
association and one later reauthentication. The exact RX-status header maps
bits `0x700` to `SEC_ENC_ERR` (firmware could not decrypt the frame), while
the RX queue source explicitly discusses frames received before keys are
installed. Debian bug
[#1137238](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=1137238) records
the same `0x703` class during reassociation on another Intel adapter. This is
useful precedent, not proof of the missed-beacon mechanism, and no persistent
algorithm warning exists on Big Red.

One `Not associated and the session protection is over already` message
occurred during the early connection-activation sequence. Exact
`time-event.c` source emits it when an association-protection time event ends
before the virtual interface reports association. It also did not recur after
the stable association. Neither class should be folded into the missed-beacon
case merely because all three originate in `iwlwifi`.

## Reproduction and recurrence capture

The existing evidence can be reconstructed without printing network
identifiers:

```sh
journalctl -k -b --no-pager -o short-iso \
  | grep -E 'missed beacons exceeds threshold|missed_beacons:'

journalctl -b -u NetworkManager --no-pager -o short-iso \
  | grep 'device (wlp0s20f3): state change:'

iw dev wlp0s20f3 station dump
```

The raw `iw` output contains a station address; redact the `Station` line and
retain only the allowlisted counters above. On a natural recurrence, capture a
station snapshot immediately before any intervention, the bounded kernel and
NetworkManager windows, another station snapshot, and a sanitized Beryl
radio/event summary. Compare exact event time, association identity without
publishing it, beacon counters, signal, retries, failed packets and state
transitions.

## Interpretation

The current result supports monitoring, not tuning. The driver encountered an
unexpected beacon/data combination but followed its documented branch and
preserved a link that remained usable. There is no evidence that power saving,
software crypto, 802.11n, Bluetooth coexistence, NetworkManager or the kernel
should be reconfigured. In fact, NetworkManager and `iwlwifi` power saving are
already disabled, while the current module settings otherwise remain defaults.

Suppressing the warning, changing a threshold, or forcing a connection loss
would remove evidence or make availability worse without identifying which
endpoint supplied the surprising count.

## Evidence boundary and reopen rules

This is one AX203, one Beryl AP, one kernel/firmware pair, one boot and one
radio environment. It has no firmware debug dump, over-the-air beacon capture,
second AP/control adapter, AP-side event at the old timestamps, or controlled
recurrence. Current station counters are end-state evidence, not a snapshot
from inside the old clusters. Ten-minute traffic averages cannot exclude short
bursts. The work proves neither an Intel defect nor a Beryl defect.

Reopen active execution only if a natural recurrence provides at least one of:

- a warning cluster plus stable association and before/after station counters;
- a coincident AP radio/channel/beacon event;
- a user-visible latency, loss or reconnect event at the same timestamp;
- a new kernel or firmware build that changes the warning branch or recurrence
  rate under otherwise comparable conditions.

Until then, leave the working Wi-Fi path and remote access intact.

## Authority

Internal research and sanitized evidence retention are authorized. No Linux,
Intel, Ubuntu, Debian or router-vendor issue, comment, patch or other upstream
interaction has been authorized or created.
