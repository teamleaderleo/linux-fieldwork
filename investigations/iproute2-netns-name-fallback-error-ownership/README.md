# iproute2 netns name fallback masks non-ENOENT open errors

Date: 2026-08-12

Internal tracking: `teamleaderleo/linux-fieldwork#607`

Related programme lane: `LF-29` — netlink compatibility and fallback.

## TL;DR

Current `netns_get_fd()` promises name-first lookup and then PID fallback. Its May 2026 centralization change describes the fallback as applying when the named namespace filesystem entry does not exist. The implementation instead falls through after every failed named-path `open()`.

That can change the operation owner. In a disposable user+mount namespace, `/run/netns/<PID>` was made to exist but be inaccessible to uid 65534. Opening the named path returned `EACCES`. The same caller could open `/proc/<PID>/ns/net`. Current fallback semantics therefore returned a valid fd for the PID namespace despite the named namespace having produced a real permission error.

An `ENOENT`-only classifier cleanly distinguishes the two cases in the same fixture:

```text
EACCES: current -> PID fd; candidate -> preserve EACCES
ENOENT: current -> PID fd; candidate -> PID fd
```

The smallest candidate is to return immediately after a named-path failure unless `errno == ENOENT`.

This is a wrong-target/error-ownership result. No privilege-escalation claim is made.

No upstream contact is authorized or has been made.

## Explain like I'm five

The argument can mean either a namespace name or a process number. iproute2 tries the name first.

Suppose the name is `643`. The file `/run/netns/643` really exists, but the caller is not allowed to open it. That is different from “there is no namespace named 643.”

Current code treats both failures the same. Because `643` is also a valid process number, it opens `/proc/643/ns/net` and returns that different namespace instead.

The candidate only tries the PID interpretation when the named file truly does not exist.

## Why care

A fallback should preserve the failure owner that determines which object the user requested. Name-first lookup creates a clear precedence rule: an existing named namespace wins over PID interpretation.

Treating `EACCES`, resource errors, or other named-path failures as equivalent to absence can silently switch from the named object to a process namespace. Downstream callers then receive a valid fd and can continue without knowing the first lookup failed for a materially different reason.

The practical prevalence is bounded. `ip netns add` creates the runtime directory with mode 0755, and ordinary fully privileged root workflows typically open these entries successfully. Capability-separated callers, ACL/LSM policy, or deliberately restricted runtime directories can produce the discriminator demonstrated here.

## Question

Should numeric name-to-PID fallback happen only on `ENOENT`, preserving other named-path errors?

## Source boundary

- Project: `iproute2/iproute2`
- Requested revision: current `main` observed during this pass
- Resolved commit: `7385bcedf313c1e2edfc1e17c0a3659e2f137d7d`
- Relevant file: `lib/namespace.c`
- Current helper: `netns_get_fd()`

Relevant history:

- `d6a1612bacfe2bf559325610e32a137aa0705598` centralized name/PID fallback and describes PID fallback when the named filesystem entry does not exist.
- Older `ip link` fallback already retried a parsed PID after a generic `netns_get_fd()` failure, so this investigation does not attribute initial introduction to the May 2026 commit without deeper archaeology.
- The May helper is nevertheless the current shared repair boundary and is now also used by newer callers such as RDMA netns handling.

Direct tracked source references:

- https://github.com/iproute2/iproute2/commit/d6a1612bacfe2bf559325610e32a137aa0705598
- https://github.com/iproute2/iproute2/blob/7385bcedf313c1e2edfc1e17c0a3659e2f137d7d/lib/namespace.c
- https://github.com/iproute2/iproute2/blob/7385bcedf313c1e2edfc1e17c0a3659e2f137d7d/ip/ipnetns.c

Upstream open and closed issue search for `netns EACCES permission fallback pid numeric name` returned no matching issue during this pass.

## Current source

Current `netns_get_fd()` does:

```c
fd = open(path, O_RDONLY);
if (fd >= 0)
    return fd;

/* make sure string is an integer */
if (get_integer(&pid, str, 0) < 0)
    return -1;

snprintf(pathbuf, sizeof(pathbuf), "/proc/%s/ns/net", str);
return open(pathbuf, O_RDONLY);
```

There is no test of the first `open()` errno before PID interpretation.

The change description for the centralized helper is narrower: try the name first; if the namespace filesystem entry does not exist, then try PID.

## Named namespace creation context

Current `ip netns add` creates `NETNS_RUN_DIR` with permissions equivalent to 0755 and then creates the namespace file before bind-mounting `/proc/.../ns/net` onto it.

That explains why a normal unrestricted root workflow does not naturally hit the EACCES fixture. It does not make all other named-path errors equivalent to absence.

## Reproduction

Tracked classifier helper: [`repro.py`](repro.py).

The authoritative local experiment used a disposable user+mount namespace with a broad local uid/gid map so a root setup process could create the fixture and a uid-65534 caller could exercise permission checks.

Setup outline:

```sh
unshare -Urnm --map-users=0:0:65536 --map-groups=0:0:65536 bash
mount --make-rprivate /
mkdir -p /run/netns
mount -t tmpfs tmpfs /run/netns
chmod 0755 /run/netns

setpriv --reuid=65534 --regid=65534 --clear-groups sleep 30 &
target=$!
touch /run/netns/$target
chmod 0700 /run/netns
```

Then execute the reproducer as uid 65534:

```sh
setpriv --reuid=65534 --regid=65534 --clear-groups \
    python3 repro.py "$target"
```

For the positive fallback control, restore directory access and remove the named entry:

```sh
chmod 0755 /run/netns
rm /run/netns/$target
setpriv --reuid=65534 --regid=65534 --clear-groups \
    python3 repro.py "$target"
```

Finally terminate the helper process. Namespace exit owns the tmpfs cleanup.

## Results

### EACCES negative control

Observed:

```text
EACCES control pid=643
current pid 13 Permission denied net:[4026532190]
candidate error 13 Permission denied None
```

The first named-path error was `EACCES`. Current behavior still returned a namespace fd from the PID path. The candidate retained the permission error and did not silently select the PID object.

### ENOENT positive control

After making the runtime directory searchable and removing `/run/netns/643`:

```text
ENOENT control pid=643
current pid 2 No such file or directory net:[4026532190]
candidate pid 2 No such file or directory net:[4026532190]
```

Both classifiers fell back to the PID namespace when the named entry was genuinely absent.

### Direct two-path discriminator

Before the classifier comparison, the same fixture directly established:

```text
/run/netns/613 ERR 13 Permission denied
/proc/613/ns/net OK net:[4026532190]
```

So the current fallback has a real alternate object available after the named-object error; this is not merely error-message replacement.

## Candidate

Tracked candidate: [`candidate.patch`](candidate.patch).

```diff
 fd = open(path, O_RDONLY);
 if (fd >= 0)
     return fd;
+
+if (errno != ENOENT)
+    return -1;
 
 /* make sure string is an integer */
```

This matches the centralized helper's documented intent and preserves the original `open()` errno on the negative path.

The candidate is independent from `teamleaderleo/linux-fieldwork#605`, which changes PID path formatting to use the parsed integer. If both survive review, they can be stacked or combined after each individual discriminator remains visible.

## Cross-context pass

### Named entry exists and opens

Unchanged. Name wins immediately.

### Named entry missing (`ENOENT`)

Passing fallback control. Candidate still tries numeric PID interpretation.

### Named entry denied (`EACCES`)

Distinguishing failure. Current code can return a different PID namespace; candidate preserves the named-path error.

### Non-numeric name

No behavioral broadening. If the name lookup fails with ENOENT and integer parsing fails, the helper returns failure.

### Numeric name precedence

Candidate sharpens existing name-first semantics. A successfully opened numeric namespace name still wins; a real error from that named object is no longer treated as proof that the name is absent.

### Resource and transient errors

Not individually executed. The same ownership principle suggests errors such as `EMFILE`, `ENFILE`, `ELOOP`, or policy-generated denials should not automatically authorize a different object lookup. Each can be added as a control if review finds a compatibility reason to treat a specific errno as absence.

## Evidence boundary

Demonstrated:

- current source falls through after any named-path `open()` failure;
- the centralization description specifically describes fallback when the filesystem entry does not exist;
- a controlled named-path `EACCES` plus readable matching PID path produces a successful wrong-object fallback under current semantics;
- an ENOENT-only classifier preserves EACCES;
- the same classifier still falls back successfully on actual ENOENT;
- the fixture used distinct authority/state paths and did not contact any external system.

Not yet demonstrated:

- exact-head iproute2 binary behavior under the fixture;
- full test-suite results for the candidate;
- prevalence under common distribution policies;
- behavior for every possible non-ENOENT errno;
- a privilege escalation or security-boundary bypass.

## Cleanup

All runtime state lived in a disposable user+mount namespace. `/run/netns` was backed by a namespace-local tmpfs. The uid-65534 helper process was terminated after the controls. Namespace exit removed the mount state.

## Current disposition

- State: `EXECUTING`
- Exact current source: `iproute2/iproute2@7385bcedf313c1e2edfc1e17c0a3659e2f137d7d`
- Reproducer: `repro.py`
- Candidate: ENOENT-only name-to-PID fallback
- Negative control: EACCES preserves named error
- Positive control: ENOENT still falls back to PID
- Cleanup state: complete
- Next safe action: build both #605 and #607 independently on an owned fork or disposable exact-head checkout when available; add repository-native tests that prove object identity, not only return status
- External-contact state: no upstream interaction authorized or made
