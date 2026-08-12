# iproute2 fallback scout — 2026-08-12

## TL;DR

A focused compatibility/fallback pass against current iproute2 promoted two network-namespace findings and closed one devlink/libmnl lead as a bounded negative.

Promoted:

- `teamleaderleo/linux-fieldwork#605` — centralized netns PID fallback parses base-0 input but constructs the procfs path from the original spelling, regressing hexadecimal/octal PID spellings previously normalized by `ip link`.
- `teamleaderleo/linux-fieldwork#607` — numeric name-to-PID fallback occurs after any named-path `open()` error, allowing a real named-namespace `EACCES` to be replaced by a successful PID namespace fd. An ENOENT-only classifier preserves the failure owner while keeping the intended absence fallback.

Closed for now:

- `mnl_attr_get_uint()` fallback used for `DEVLINK_ATTR_INDEX`. The reviewed kernel contract uses a `uint` netlink attribute for an unsigned-integer devlink index, and iproute2's compatibility getter handles the valid 1/2/4/8-byte unsigned payload widths. No width-truncation defect was promoted from this pass.

Exact iproute2 source head reviewed: `7385bcedf313c1e2edfc1e17c0a3659e2f137d7d`.

No upstream contact is authorized or has been made.

## Why this pass

The `LF-29` lane asks whether compatibility and fallback logic preserves identity, error ownership, and older/newer netlink contracts. Recent iproute2 commits provided three compact seams: a libmnl API compatibility shim, centralized network-namespace name/PID lookup, and callers simplified around that shared lookup.

The netns seam produced the distinguishing results.

## Source orientation

Primary upstream repository:

- https://github.com/iproute2/iproute2

Relevant current files:

- `lib/namespace.c`
- `lib/utils.c`
- `ip/iplink.c`
- `devlink/devlink.c`
- `rdma/dev.c`

Relevant recent commits:

- https://github.com/iproute2/iproute2/commit/d6a1612bacfe2bf559325610e32a137aa0705598 — centralize name/PID fallback in `netns_get_fd()`
- https://github.com/iproute2/iproute2/commit/22061a6354c08002254003d4e6f7d9e1129371b6 — remove duplicate `ip link` PID fallback
- https://github.com/iproute2/iproute2/commit/1ffc5715b9a7e140d6b44935531912a4cab79d86 — remove duplicate devlink PID fallback
- https://github.com/iproute2/iproute2/commit/2a8b53446ff5636b0f412eb3665f83378d1cb5b2 — add RDMA PID support through shared helper
- https://github.com/iproute2/iproute2/commit/bef61beb2edf354e87130a92d72246a78ac9dbf2 — add libmnl `mnl_attr_get_uint()` compatibility implementation

## Finding A — parsed PID discarded before procfs lookup

See [`investigations/iproute2-netns-pid-numeric-canonicalization/`](../../investigations/iproute2-netns-pid-numeric-canonicalization/).

The old `ip link` fallback did:

```text
get_integer(..., base 0) -> parsed pid -> /proc/%d/ns/net
```

The shared helper does:

```text
get_integer(..., base 0) -> parsed pid -> /proc/%s/ns/net using original input
```

Executed reduced result:

```text
pid=563
old 563          -> /proc/563/ns/net         : OK
new 563          -> /proc/563/ns/net         : OK
old 0x233        -> /proc/563/ns/net         : OK
new 0x233        -> /proc/0x233/ns/net       : ENOENT
old 01063        -> /proc/563/ns/net         : OK
new 01063        -> /proc/01063/ns/net       : ENOENT
```

Promotion signal: a behavior accepted by the prior caller is rejected solely because the normalized integer is discarded.

## Finding B — name error can become a different namespace

See [`investigations/iproute2-netns-name-fallback-error-ownership/`](../../investigations/iproute2-netns-name-fallback-error-ownership/).

A disposable user+mount namespace created a numeric named entry that existed but was inaccessible to uid 65534, plus a same-UID target process whose `/proc/<pid>/ns/net` remained readable.

Direct discriminator:

```text
/run/netns/613 -> EACCES
/proc/613/ns/net -> success
```

Classifier comparison:

```text
EACCES:
  current -> PID fd
  ENOENT-only candidate -> preserve EACCES

ENOENT:
  current -> PID fd
  ENOENT-only candidate -> PID fd
```

Promotion signal: fallback changes the selected object after a failure that does not mean the named object is absent.

## Negative — devlink uint compatibility shim

The first scout lead was the fallback implementation of `mnl_attr_get_uint()` added for builds against older libmnl.

The helper dispatches by payload size:

```text
1 byte -> u8
2 bytes -> u16
4 bytes -> u32
8 bytes -> u64
other   -> UINT64_MAX
```

The source cross-check did not support a width defect claim for `DEVLINK_ATTR_INDEX`: the kernel index is an unsigned integer, the netlink spec intentionally uses `uint`, kernel lookup bounds an index to `U32_MAX`, and the compatibility getter handles the standard unsigned payload widths. Malformed non-standard payload lengths remain a robustness question, but no current defect was promoted from kernel-generated messages.

## Reusable lesson

When a fallback accepts multiple identifier forms, preserve two things independently:

1. canonicalized identity — use the parsed identifier, not the original spelling, when the next subsystem has a stricter textual representation;
2. failure ownership — only switch identifier classes on the exact failure that means the first class is unavailable.

The netns helper violated each rule in a separate way, producing two small and independently testable candidates.

## Cleanup

- PID-format probe opened only the caller's own namespace fds and closed them.
- Error-ownership probe used a disposable user+mount namespace and namespace-local tmpfs at `/run/netns`; the helper process was terminated and namespace exit owned cleanup.
- No external target or upstream interaction occurred.

## Next directions

- Build #605 and #607 independently against an exact current iproute2 checkout when an owned fork or disposable source checkout is available.
- Add repository-native identity tests, with decimal positive controls and alternate PID/error-class negative controls.
- If returning to `LF-29`, prefer another fallback where the first failure class changes object identity or protocol generation rather than extending the closed devlink-uint lead.
