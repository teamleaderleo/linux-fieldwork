# BlueZ zero-address HCI advertisement

## In simple words

During one long Bluetooth discovery session, the controller on `big-red`
reported advertisers whose address was `00:00:00:00:00:00`. BlueZ then emitted
6,550 paired object/interface errors because address type participates in its
device lookup while the D-Bus object path is derived from the address alone.

This is not yet a demonstrated BlueZ defect. The raw HCI report already
contained the zero address, so the earlier kernel regression discussed in
[BlueZ issue 1157](https://github.com/bluez/bluez/issues/1157) does not explain
this observation. The next useful result is to distinguish a non-compliant
nearby advertiser from a controller/firmware parsing edge and to identify which
client owns the discovery session.

## Current state

- State: `HOLD`
- Exact working head: Linux Fieldwork base `6f52e7166bbeb05814c94ab546ec1771d6fc5d0c`
- Latest authoritative gate or artifact: current-boot journal summary plus an
  earlier bounded raw `btmon` trace on `big-red`
- First incomplete step: capture a short sanitized raw-HCI trace during a
  measured recurrence and identify the discovery owner
- Cleanup state: discovery stopped without intervention; no diagnostic process
  or changed Bluetooth state remains
- Next safe action: reopen only after recurrence, then collect equal-window
  error counts and bounded D-Bus/HCI traces
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
- Host context: physical Redmi Book Pro 15 (2025), named `big-red`
- Privileges: journal and system-bus reads; no package, service, firmware, or
  Bluetooth-state mutation in this investigation
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
browser/passkey surface is a plausible discovery trigger. That timing does not
identify the producer of the malformed advertisement. A later 20-second
system-bus trace saw no new adapter method call while the already-active scan
continued.

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
- Not demonstrated: which client began discovery, which radio/controller event
  produced the malformed address, or whether current upstream source still
  mishandles any recoverable identity.

## Evidence boundary

The retained observation is from one controller, kernel, BlueZ package, boot,
and radio environment. The short D-Bus trace began after discovery was already
active. No controlled recurrence, second controller, firmware comparison, or
current-source BlueZ build has run. Browser timing is correlation only.

## Next step

Keep this investigation on hold while the system is quiet. Reopen on recurrence,
identify the scan owner, capture one bounded HCI window with an ordinary-device
negative control, and decide whether the evidence belongs with BlueZ, the
kernel/controller vendor, or a non-compliant advertiser.

## Authority

Internal research and sanitized evidence retention are authorized. No upstream
issue, comment, patch, or other external interaction has been authorized or
created. Do not restart BlueZ, toggle Bluetooth, kill browsers, change firmware,
or replace the kernel merely to reproduce or silence the messages.
