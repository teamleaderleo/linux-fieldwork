# BlueZ zero-address HCI advertisement

## In simple words

During one long Bluetooth discovery session, the controller on `big-red`
reported advertisers whose address was `00:00:00:00:00:00`. BlueZ then emitted
6,550 paired object/interface errors because address type participates in its
device lookup while the D-Bus object path is derived from the address alone.

This is not yet a demonstrated BlueZ defect. A controlled recurrence now
identifies the long-lived ChatGPT desktop process as the BlueZ discovery
client, but the raw HCI report already contained the zero address, so the
earlier kernel regression discussed in
[BlueZ issue 1157](https://redirect.github.com/bluez/bluez/issues/1157) does not explain
this observation. The next useful results are to map that main-process request
to the exact in-app surface and distinguish a non-compliant nearby advertiser
from a controller/firmware parsing edge.

## Current state

- State: `MITIGATED`; Bluetooth is rfkill-blocked and its service is stopped
  and boot-disabled after a measured recurrence and explicit user authorization
- Owning issue: [#685](https://github.com/teamleaderleo/linux-fieldwork/issues/685)
- Evidence parent for the discovery-owner result: Linux Fieldwork
  `652b45424d119a8181615da4ca38a1b271a5d75f`; this revision records the later
  spontaneous stop boundary
- Latest authoritative gate or artifact: current-boot journal summary, an
  earlier bounded raw `btmon` trace, a controlled system-bus owner trace, the
  2026-08-31 03:18:28 adapter/rfkill verification, and the 04:57 service-state
  verification on `big-red`
- First incomplete step: confirm the restored blocked state after the next
  ordinary reboot; do not reboot merely to test it
- Cleanup state: Bluetooth rfkill is blocked, Wi-Fi rfkill is unblocked,
  `bluetooth.service` is disabled and inactive, the bounded monitors exited,
  and no diagnostic process remains
- Next safe action: leave the adapter off. If Bluetooth is needed, run
  `sudo systemctl enable --now bluetooth.service`, `sudo rfkill unblock
  bluetooth`, and `bluetoothctl power on`; if the scan/error stream then
  recurs, capture the bounded owner and HCI evidence before changing another
  component
- External-contact state: no new upstream contact authorized or made

## Intent and precedent

BlueZ's [Adapter API](https://bluez.readthedocs.io/en/latest/adapter-api/)
documents that discovery sessions are shared between clients. BlueZ issue
[1157](https://redirect.github.com/bluez/bluez/issues/1157) contains the same userspace
error text, but its published trace begins with a non-zero HCI advertiser and
later becomes zero in the kernel management path. Linux commit
[`eb73b5a91572`](https://redirect.github.com/torvalds/linux/commit/eb73b5a9157221f405b4fe32751da84ee46b7a25)
fixed that pending-advertisement path and is present in the running Ubuntu
kernel source.

Here, the all-zero address was already present in the controller's raw HCI LE
Extended Advertising Report. BlueZ issue
[715](https://redirect.github.com/bluez/bluez/issues/715) also records that BlueZ cannot
reconstruct an address when the HCI report itself supplies all zeroes.

## 2026-08-31 recurrence and adapter-off disposition

The scan recurred without a connected Bluetooth device. A two-hour journal
window contained 282 matching zero-address messages, beginning at 02:17:47 and
ending at 03:08:43 Asia/Shanghai. The adapter reported `Powered=true`,
`Discovering=true`, `Pairable=false`, and zero connected devices.

The user authorized disabling unused Bluetooth. `bluetoothctl power off` was
applied after the zero-device preflight. The 03:10:38 verification reported
`Powered=false`, `Discovering=false`, `Pairable=false`, zero connected devices,
an active `bluetooth.service`, unchanged unblocked rfkill state, and no failed
system or user units. At 03:11:48 the final matching message was 185 seconds
old and the same adapter state held.

Because the installed BlueZ configuration keeps its default `AutoEnable=true`,
adapter power-off alone could be lost after service startup. At 03:14:15,
Bluetooth-only rfkill was therefore blocked. The immediate gate showed
Bluetooth blocked, Wi-Fi unblocked, adapter power and discovery false, the
default route present, and the Tailscale backend running. `systemd-rfkill`
stores each rfkill class on change and restores it at boot. One rfkill state
file was updated, its socket was active, and no kernel command-line override
disabled restoration. At 03:18:28 there had been zero matching messages since
the rfkill change; the final message was 585 seconds old, Tailscale was still
running, and no system or user unit was failed.

This is a radio-state mitigation, not a source fix. The known Linux fix for
issue 1157 is already present and owns a different transition: this host's
earlier raw HCI capture contained the zero address before BlueZ received it.
There is no evidence-backed upstream patch to fold into this machine for the
observed mechanism.

At 04:54, the user explicitly authorized fully disabling unused Bluetooth.
`systemctl disable --now bluetooth.service` stopped the active service and
removed its boot and D-Bus activation links. The 04:57 gate reported the
service disabled and inactive, Bluetooth still soft-blocked, and no failed
system units. The verification command initially left one `bluetoothctl show`
client waiting because BlueZ was no longer available; that route-owned client
and its parent shell were terminated, and a process recheck was clean.

## Question

When discovery recurs, does a deliberate scan consistently receive an all-zero
address from the controller, and can the result be attributed to one advertiser
or controller/firmware path without disrupting normal Bluetooth clients?

## Source

- Project: BlueZ, Linux Bluetooth management path, and the host controller
- Package version: `bluez 5.85-4ubuntu0.1`
- Running kernel: `7.0.0-30-generic`
- Corresponding Ubuntu source package: `7.0.0-30.30`
- Candidate source commit: none
- Local source path: not imported
- Import metadata: none

## Environment

- Distribution and release: Ubuntu 26.04.1 LTS
- Kernel and architecture: Linux `7.0.0-30-generic`, x86-64
- Host context: physical REDMI Book Pro 16 2025, named `big-red`
- Privileges: journal and system-bus reads, one bounded adapter-only power
  cycle, and the later user-authorized adapter power-off mitigation
- Relevant tool version: BlueZ `5.85-4ubuntu0.1`

## Baseline behavior

The current boot recorded 6,550 matching messages from 2026-08-28 22:58:59
through 2026-08-29 14:17:30 Asia/Shanghai:

```text
src/device.c:device_new() Unable to register device interface for 00:00:00:00:00:00
Unable to create object for found device 00:00:00:00:00:00
```

The adapter was discovering while the count rose. It later reported
`Discovering=false`, and a final equal five-minute window contained no matching
message.

The first event began about ten seconds after a Chromium-backed authentication
flow loaded. WebAuthn includes `ble` and `hybrid` authenticator transports, so a
browser/passkey surface was a plausible discovery trigger. A controlled
recurrence now confirms that the ChatGPT desktop main process owns the BlueZ
scan, but does not yet identify which renderer/surface asked that main process
to start it or the producer of the malformed advertisement. A prior 20-second
system-bus trace saw no new adapter method call while the already-active scan
continued.

A renderer lifecycle inventory narrows, but does not close, that gap. ChatGPT
renderer client 45, PID 40524, started at 22:58:49; the first zero-address
message followed at 22:58:59. Clients 41 and 43 started at 22:54:20 and
22:57:54. Client 45 remains alive while discovery and the error stream continue.
The desktop currently exposes one ChatGPT top-level window and no separate auth
popup. A read-only browser-tab inventory could reach Edge but not ChatGPT's
in-app browser, so no tab title, URL, page contents, screenshot, or authentication
material was collected. The ten-second boundary makes client 45 the strongest
surface candidate, not a demonstrated owner.

The recurrence later ended without intervention. The final paired messages
were logged at 2026-08-29 19:16:59 Asia/Shanghai. At the 19:52-19:55 snapshots,
the adapter reported `Discovering=false`, ChatGPT PID 4237 was still active,
renderer PID 40524 was no longer present, and the latest 2-, 5-, and 15-minute
windows each contained zero matching lines. The current-boot total had reached
8,506 lines. This proves a dormant stop boundary with the main app preserved;
it does not prove that renderer 45 caused the stop because no exit event was
captured at the transition.

The later 23:25 snapshot adds a renderer-class negative control. ChatGPT main
PID 4237 remained active, and renderer client 66, PID 1522010, had remained
active since 19:03:26 -- before the final error -- while the adapter reported
`Discovering=false`. The Bluetooth service journal had no entry after 20:00,
and the latest-hour zero-address count remained zero. Therefore neither the
main desktop process nor the mere existence of a ChatGPT renderer is sufficient
to sustain discovery or the error stream. This strengthens a surface-specific
request/lifecycle hypothesis without proving that renderer 45 owned it. No app,
process, adapter, service, or setting was changed.

## Hypotheses and discriminators

1. **Nearby advertiser:** the same zero-address report should correlate with a
   stable payload/radio pattern across controller and machine comparisons.
2. **Controller or firmware parsing:** the anomaly should vary with controller,
   firmware, or low-level event form even under the same nearby radio traffic.
3. **Discovery client only controls exposure:** closing the owning scan client
   should stop reports but cannot explain why an HCI report contains a zero
   address.

A negative control must show ordinary non-zero advertisements in the same
bounded trace.

## Reproduction plan

Only after a measured recurrence:

```sh
busctl get-property org.bluez /org/bluez/hci0 org.bluez.Adapter1 Discovering
journalctl -u bluetooth --since '-5 min' --no-pager -o cat \
  | grep -c '00:00:00:00:00:00'
```

Then capture a short D-Bus discovery-owner trace and a minimal `btmon` window.
Compare equal time windows before and after closing only the identified
authentication/passkey surface. Sanitize unrelated device addresses and
payloads before retaining or sharing any trace.

## Results

- Demonstrated: the raw HCI report on this host already carried both
  public-zero and random-zero advertiser forms.
- Demonstrated: the userspace log signature alone cannot identify the issue
  1157 kernel regression; its fix is present here and protects a different
  transition.
- Demonstrated: discovery and the error stream stopped without intervention.
- Demonstrated on 2026-08-29: with no connected devices and Pairable disabled,
  a normal `StopDiscovery` from a new client failed while discovery stayed
  active. After an adapter-only power off/on, system-bus sender `:1.87` issued
  `SetDiscoveryFilter(Transport="le")` and `StartDiscovery`; `busctl` mapped
  that sender to the long-lived ChatGPT desktop main process, PID 4237. The
  Edge client connected hours after the original recurrence and was not the
  owner. The adapter was restored powered-on and no app or service was killed.
- Demonstrated on 2026-08-29 at 16:53 Asia/Shanghai: ChatGPT renderer client 45
  started ten seconds before the first zero-address message and remained alive;
  the adapter was still discovering, sender `:1.87` still mapped to ChatGPT PID
  4237, and the journal contained 7,512 matching lines this boot, 566 in the
  previous hour, and 78 in the latest five-minute sample. The immediately
  preceding and latest equal five-minute windows contained 50 and 70 lines.
  One ChatGPT top-level window and no separate auth popup were exposed. No app,
  tab, process, adapter, service, or setting was changed.
- Demonstrated on 2026-08-29 at 19:52-19:55 Asia/Shanghai: the last paired
  zero-address messages were at 19:16:59; discovery was false and the latest
  2-, 5-, and 15-minute windows were clean while the ChatGPT main process
  remained active. Renderer PID 40524 was no longer present. The boot total was
  8,506 lines. No process, app, adapter, service, or setting was changed.
- Demonstrated on 2026-08-29 at 23:25 Asia/Shanghai: discovery and the
  latest-hour error stream remained inactive while ChatGPT main PID 4237 and
  renderer client 66/PID 1522010 were both active. Client 66 had started before
  the final error and persisted after the dormant boundary. ChatGPT main-process
  presence and generic renderer presence are therefore useful negative controls,
  not sufficient trigger conditions.
- Demonstrated on 2026-08-31: the scan and error stream recurred, with 282
  matching messages in two hours and zero connected devices. After explicit
  user authorization, adapter power was turned off and Bluetooth-only rfkill
  was blocked for boot persistence. The adapter then remained not powered and
  not discovering, the BlueZ service stayed active, Wi-Fi stayed unblocked,
  and the error stream emitted zero matching messages after the rfkill change
  through the 585-second quiet gate.
- Demonstrated on 2026-08-31 at 04:57 Asia/Shanghai: after a second explicit
  authorization to disable Bluetooth fully, `bluetooth.service` was stopped
  and boot-disabled while Bluetooth remained soft-blocked. No failed system
  units appeared. One route-owned `bluetoothctl show` verifier that waited
  after BlueZ stopped was terminated and did not survive the cleanup check.
- Not demonstrated: which ChatGPT renderer/surface requested discovery, which
  radio/controller event produced the malformed address, or whether current
  upstream source still mishandles any recoverable identity.

## Evidence boundary

The retained observation is from one controller, kernel, BlueZ package, boot,
and radio environment. The D-Bus trace proves the active discovery client. The
client-45 timestamp and later absence make it a candidate; the quiet client-66
interval proves only that generic renderer presence is insufficient. Neither
result proves which surface requested discovery, what ended the session, the
origin of the malformed radio report, or the exact in-app surface. No second
controller, firmware comparison, transition-time renderer trace, or
current-source BlueZ build has run.

## Next step

Confirm that the journal remains quiet in the next routine health snapshot.
Leave Bluetooth off while it has no user. If it becomes useful, restore it with
`sudo systemctl enable --now bluetooth.service`, `sudo rfkill unblock
bluetooth`, and then `bluetoothctl power on`. A recurrence after rollback
should trigger the bounded D-Bus-owner and HCI plan before any package, kernel,
firmware, or application change. After the next ordinary reboot, confirm the
service stayed disabled and Bluetooth stayed blocked; do not reboot for this
test.

## Authority

Internal research and sanitized evidence retention are authorized. No upstream
issue, comment, patch, or other external interaction has been authorized or
created. One earlier controlled adapter-only power cycle was performed after
confirming there were no connected devices; it restored power immediately and
exposed the scan owner. On 2026-08-31 the user explicitly authorized disabling
unused Bluetooth, so the adapter was powered off with zero connected devices.
Bluetooth-only rfkill was then blocked so systemd will restore the state at
boot. The later user authorization also covered stopping and boot-disabling
`bluetooth.service`. Rollback is `sudo systemctl enable --now
bluetooth.service`, `sudo rfkill unblock bluetooth`, and `bluetoothctl power
on`. Do not restart BlueZ, kill browsers, change firmware, or replace the
kernel merely to reproduce or silence the messages.
