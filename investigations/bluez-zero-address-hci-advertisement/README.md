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
[BlueZ issue 1157](https://github.com/bluez/bluez/issues/1157) does not explain
this observation. The next useful results are to map that main-process request
to the exact in-app surface and distinguish a non-compliant nearby advertiser
from a controller/firmware parsing edge.

## Current state

- State: `MONITORING`
- Owning issue: [#685](https://github.com/teamleaderleo/linux-fieldwork/issues/685)
- Evidence parent for the discovery-owner result: Linux Fieldwork
  `652b45424d119a8181615da4ca38a1b271a5d75f`; this revision records the later
  spontaneous stop boundary
- Latest authoritative gate or artifact: current-boot journal summary, an
  earlier bounded raw `btmon` trace, a controlled system-bus owner trace, and a
  later adapter/journal/process snapshot on `big-red`
- First incomplete step: on a future measured recurrence, capture the exact
  transition that ends discovery and correlate it with renderer lifecycle;
  timestamp correlation alone is not identity proof
- Cleanup state: the adapter is powered on and reports `Discovering=false`;
  ChatGPT remains active, the bounded monitors exited, and no diagnostic
  process remains
- Next safe action: wait for a measured recurrence. Do not reopen an auth
  surface, restart BlueZ, toggle the adapter, or close ChatGPT merely to
  reproduce a dormant symptom
- External-contact state: no new upstream contact authorized or made

## Intent and precedent

BlueZ's [Adapter API](https://bluez.readthedocs.io/en/latest/adapter-api/)
documents that discovery sessions are shared between clients. BlueZ issue
[1157](https://github.com/bluez/bluez/issues/1157) contains the same userspace
error text, but its published trace begins with a non-zero HCI advertiser and
later becomes zero in the kernel management path. Linux commit
[`eb73b5a91572`](https://github.com/torvalds/linux/commit/eb73b5a9157221f405b4fe32751da84ee46b7a25)
fixed that pending-advertisement path and is present in the running Ubuntu
kernel source.

Here, the all-zero address was already present in the controller's raw HCI LE
Extended Advertising Report. BlueZ issue
[715](https://github.com/bluez/bluez/issues/715) also records that BlueZ cannot
reconstruct an address when the HCI report itself supplies all zeroes.

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
- Privileges: journal and system-bus reads plus one bounded adapter-only power
  cycle; no package, service, firmware, or persistent Bluetooth-policy change
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
- Not demonstrated: which ChatGPT renderer/surface requested discovery, which
  radio/controller event produced the malformed address, or whether current
  upstream source still mishandles any recoverable identity.

## Evidence boundary

The retained observation is from one controller, kernel, BlueZ package, boot,
and radio environment. The D-Bus trace proves the active discovery client. The
renderer timestamp and later absence make client 45 a candidate but do not
prove which renderer requested discovery, what ended the session, the origin
of the malformed radio report, or the exact in-app surface. No second
controller, firmware comparison, transition-time renderer trace, or
current-source BlueZ build has run.

## Next step

Preserve the active ChatGPT desktop app and the now-clean adapter state. On a
future measured recurrence, capture a bounded D-Bus owner trace and renderer
inventory before changing anything. If the same exact in-app
authentication/passkey surface is visibly identifiable, close only that
surface and compare equal windows; reopen it only as an owner-present
reproduction control. Capture the discovery stop transition as well as the
start. The client-owner result belongs with ChatGPT/WebAuthn behavior; the
zero-address report still needs separate attribution to BlueZ, the
kernel/controller vendor, or a non-compliant advertiser.

## Authority

Internal research and sanitized evidence retention are authorized. No upstream
issue, comment, patch, or other external interaction has been authorized or
created. One controlled adapter-only power cycle was performed after confirming
there were no connected devices; it restored power immediately and exposed the
scan owner. Do not restart BlueZ, kill browsers, change firmware, or replace the
kernel merely to reproduce or silence the messages.
