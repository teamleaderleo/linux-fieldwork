# iproute2 devlink tc-bw parser silently narrows overflowing values

Date: 2026-08-12

Internal tracking: `teamleaderleo/linux-fieldwork#608`

Related programme lane: `LF-29` — netlink compatibility and fallback.

## TL;DR

Current `devlink port function rate ... tc-bw` parsing uses raw `strtoul()` for both the traffic-class index and bandwidth value, then assigns the result into narrower `int` and `uint32_t` objects without checking overflow or width.

On a 64-bit build this can transform invalid text into a different valid value before the existing range checks or netlink encoding see it. For example:

```text
4294967296 -> index 0
4294967297 -> index 1
4294967296 -> bandwidth 0
4294967297 -> bandwidth 1
```

The project already provides checked numeric helpers. The candidate replaces the raw conversions with `get_integer(..., 10)` for the index and `get_u32(..., 10)` for bandwidth.

No upstream contact is authorized or has been made.

## Source boundary

- Project: `iproute2/iproute2`
- Exact source head reviewed: `7385bcedf313c1e2edfc1e17c0a3659e2f137d7d`
- Parser: `devlink/devlink.c::parse_tc_bw_arg()`
- Introduction: `c83d1477f8b2a26f666e9925469a50a1197183f3`
- UAPI: `DEVLINK_RATE_TC_ATTR_INDEX` is u8; `DEVLINK_RATE_TC_ATTR_BW` is u32
- Documented traffic-class index range: 0..7

The introduction commit added the same raw `strtoul()` conversions that remain in current source.

## Current behavior

The relevant current operations are equivalent to:

```c
*tc_index = strtoul(index, &endptr, 10);
...
*tc_bw = strtoul(value, &endptr, 10);
```

Only trailing characters are checked. The code does not reject a value that is valid as `unsigned long` but too wide for the destination type.

The later index check:

```c
if (index < 0 || index >= DEVLINK_RATE_TCS_MAX)
    ...
```

cannot catch values that have already narrowed into the valid 0..7 range.

## Reproduction

Tracked fixture: [`repro.c`](repro.c).

Compile and run:

```sh
cc -Wall -Wextra -Werror -O2 repro.c -o /tmp/iproute2-tcbw-repro
/tmp/iproute2-tcbw-repro
```

One executed run on the current environment produced:

```text
idx=0 bw=20 | current idx=0 bw=20 | candidate idx=0 bw=20
idx=4294967296 bw=20 | current idx=0 bw=20 | candidate idx=ERR bw=20
idx=4294967297 bw=20 | current idx=1 bw=20 | candidate idx=ERR bw=20
idx=0 bw=4294967296 | current idx=0 bw=0 | candidate idx=0 bw=ERR
idx=0 bw=4294967297 | current idx=0 bw=1 | candidate idx=0 bw=ERR
idx=-4294967296 bw=20 | current idx=0 bw=20 | candidate idx=ERR bw=20
```

This fixture models the exact conversion/narrowing boundary. It does not require devlink-capable hardware.

## Candidate

Tracked candidate: [`candidate.patch`](candidate.patch).

The repair keeps the existing semantic split:

- index text is parsed as a checked integer and still passes through the existing 0..7 range check;
- bandwidth text is parsed as a checked u32;
- no new bandwidth policy or sum constraint is added.

This is deliberately narrower than changing the data model or kernel-side validation.

## Test boundary

A parser-level test is the cleanest regression test because the defect occurs before any netlink request is sent.

Useful controls:

- accept normal values such as `0:20`;
- reject index `4294967296` and `4294967297` instead of aliasing them to 0/1;
- reject bandwidth `4294967296` and `4294967297` instead of aliasing them to 0/1;
- reject large negative strings that `strtoul()` can otherwise map into an unsigned value which narrows back into range.

The repository's existing testsuite does not expose an obvious devlink parser-only slot from the current search. Do not require special hardware merely to prove this conversion bug.

## Evidence boundary

Demonstrated:

- exact current source uses unchecked `strtoul()` followed by narrowing;
- the behavior dates to the tc-bw introduction commit;
- current UAPI widths are u8/u32 and the man page documents index 0..7;
- local C execution reproduces invalid-to-valid narrowing on the current 64-bit ABI;
- existing iproute2 checked conversion helpers reject the same inputs;
- upstream open/closed issue search for this tc-bw overflow/truncation pattern returned no match.

Not yet demonstrated:

- exact-head full iproute2 build with the candidate applied;
- a repository-native integration test accepted by upstream conventions;
- a specific device/driver accepting a post-truncation bandwidth value.

The parser defect does not depend on the last item: changing user input before netlink validation is itself the value-integrity failure being tracked.

## Cleanup

The local reproducer creates only a temporary binary/source file and removes both. No network device, namespace, or persistent system state is changed.

## Current disposition

- State: `EXECUTING`
- Reproducer: present
- Candidate: present
- Exact current source: `iproute2/iproute2@7385bcedf313c1e2edfc1e17c0a3659e2f137d7d`
- Cleanup state: complete
- Next safe action: if an owned iproute2 fork becomes available, build the exact candidate and add a parser-level regression test; otherwise continue adjacent recent devlink parsing boundaries
- External-contact state: no upstream interaction authorized or made
