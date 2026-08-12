# iproute2 netns PID fallback loses parsed numeric form

Date: 2026-08-12

Internal tracking: `teamleaderleo/linux-fieldwork#605`

Related programme lane: `LF-29` — netlink compatibility and fallback.

## TL;DR

A May 2026 iproute2 refactor centralized network-namespace name/PID fallback in `netns_get_fd()`. The new helper still validates PID input with `get_integer(..., 0)`, so C-style hexadecimal and octal integer spellings are accepted by the parser. However, it ignores the parsed integer when building the procfs path and instead uses the original string:

```c
snprintf(pathbuf, sizeof(pathbuf), "/proc/%s/ns/net", str);
```

That changes behavior from the pre-refactor `ip link` path, which formatted the parsed PID with `%d`:

```c
snprintf(path, sizeof(path), "/proc/%d/ns/net", pid);
```

A reduced local probe against the caller's own PID demonstrates the difference. Decimal succeeds in both variants. Equivalent hexadecimal and octal spellings succeed in the pre-refactor form and fail with `ENOENT` in the current form because procfs process-directory names are decimal.

The smallest candidate is one line: format the already parsed `pid` instead of the input string.

No upstream contact is authorized or has been made.

## Explain like I'm five

The command accepts a process number. Its number parser understands several ways to write the same number, such as decimal `563`, hexadecimal `0x233`, or octal `01063`.

Before May, iproute2 converted those spellings into the actual number and then opened `/proc/563/ns/net`.

After the refactor, iproute2 checks that `0x233` is a valid number, but then tries to open `/proc/0x233/ns/net`. Procfs does not name process directories that way, so the lookup fails even though the parser accepted the PID and the process exists.

## Why care

`ip link ... netns PID` is an existing interface for moving links into another process's network namespace. The refactor was intended to centralize name/PID handling without changing caller behavior. For `ip link`, the source diff shows that the prior fallback accepted base-0 integer input and normalized it to decimal before procfs lookup.

This is a compatibility regression with a narrow repair boundary. It does not require changing how numeric namespace names are prioritized, how FDs are passed through netlink, or how namespace files are created.

## Question

Does current `netns_get_fd()` preserve the numeric PID input forms accepted by the pre-centralization `ip link` fallback?

## Source boundary

- Project: `iproute2/iproute2`
- Requested revision: current `main` observed during this pass
- Resolved commit: `7385bcedf313c1e2edfc1e17c0a3659e2f137d7d`
- Relevant current file: `lib/namespace.c`
- Integer parser: `lib/utils.c`
- Proven pre-refactor caller: `ip/iplink.c`

History boundary:

- `d6a1612bacfe2bf559325610e32a137aa0705598` — centralized name/PID fallback in `netns_get_fd()`
- `22061a6354c08002254003d4e6f7d9e1129371b6` — removed the now-duplicate `iplink_parse()` PID fallback

Repository files may carry direct source links:

- https://github.com/iproute2/iproute2/commit/d6a1612bacfe2bf559325610e32a137aa0705598
- https://github.com/iproute2/iproute2/commit/22061a6354c08002254003d4e6f7d9e1129371b6
- https://github.com/iproute2/iproute2/blob/7385bcedf313c1e2edfc1e17c0a3659e2f137d7d/lib/namespace.c

Upstream open and closed issue search for `netns pid hex octal netns_get_fd` returned no matching issue during this pass.

## Baseline before centralization

Immediately before `22061a6354c08002254003d4e6f7d9e1129371b6`, `iplink_parse()` handled `netns` like this after a named namespace lookup failed:

```c
int pid;

...
netns = netns_get_fd(*argv);
if (netns < 0 && get_integer(&pid, *argv, 0) == 0) {
    char path[PATH_MAX];

    snprintf(path, sizeof(path), "/proc/%d/ns/net", pid);
    netns = open(path, O_RDONLY);
}
```

Two details form the compatibility contract actually executed by this code:

1. `get_integer(..., 0)` uses `strtol()` with base zero;
2. the parsed integer is formatted back to canonical decimal with `%d`.

The current `get_integer()` implementation retains the same base-zero semantics when called with `base == 0`.

## Current behavior

Current `netns_get_fd()` first tries a named namespace path. If that fails, it does:

```c
if (get_integer(&pid, str, 0) < 0)
    return -1;

snprintf(pathbuf, sizeof(pathbuf), "/proc/%s/ns/net", str);
return open(pathbuf, O_RDONLY);
```

The local `pid` proves the string parsed successfully, but is not used after validation.

For ordinary decimal input this happens to be equivalent. For another base-zero spelling of the same integer it is not.

## Reproduction

Tracked fixture: [`repro.c`](repro.c).

Compile and run:

```sh
cc -Wall -Wextra -Werror -O2 repro.c -o /tmp/iproute2-netns-pid-repro
/tmp/iproute2-netns-pid-repro
```

The fixture uses its own PID, so no external namespace or process is touched. For each spelling it compares:

```text
old form: parse integer -> /proc/%d/ns/net
new form: parse integer -> /proc/%s/ns/net
```

## Results

One executed run observed:

```text
pid=563
old 563          -> /proc/563/ns/net         : OK
new 563          -> /proc/563/ns/net         : OK
old 0x233        -> /proc/563/ns/net         : OK
new 0x233        -> /proc/0x233/ns/net       : No such file or directory
old 01063        -> /proc/563/ns/net         : OK
new 01063        -> /proc/01063/ns/net       : No such file or directory
```

A separate direct procfs control on PID 547 likewise observed:

```text
/proc/547/ns/net    -> OK
/proc/0x223/ns/net  -> ENOENT
/proc/01043/ns/net  -> ENOENT
```

### Interpretation

The parser and procfs disagree only because the parsed integer is discarded before path construction.

The pre-refactor behavior survives the alternate spelling because `%d` canonicalizes the value. Current behavior passes the spelling through to a filesystem whose process directories use decimal names.

## Cross-context pass

### Decimal PID

Passing control. Both old and current forms address the same `/proc/<decimal>/ns/net` path.

### Hexadecimal PID

Distinguishing failure. Base-zero parsing accepts the value, old formatting canonicalizes it, current path construction does not.

### Octal PID

Distinguishing failure. Same mechanism as hexadecimal.

### Numeric named namespace

Name-first semantics are unchanged by the candidate. `netns_get_fd()` tries the named namespace before parsing a PID, so a successfully opened numeric namespace name still wins.

### devlink

Do not widen the regression claim to devlink. The fallback removed by `1ffc5715b9a7e140d6b44935531912a4cab79d86` used `dl_argv_uint32_t()`, whose current implementation calls `get_u32(..., 10)`. Its historical accepted input boundary therefore differs from `ip link`'s proven base-zero path.

The centralized helper can still be used by devlink; this investigation only claims a compatibility regression where the pre-refactor caller demonstrably accepted the alternate spelling.

### Named-entry open errors

A separate review concern exists: the centralization commit describes PID fallback when the namespace filesystem entry does not exist, while current code falls back after any `open()` error. That changes failure ownership for errors such as permission or resource failures.

This is intentionally excluded from the current one-line candidate. It needs its own discriminator because changing the fallback errno set could affect callers that have come to rely on current behavior.

## Candidate

Tracked candidate: [`candidate.patch`](candidate.patch).

```diff
- snprintf(pathbuf, sizeof(pathbuf), "/proc/%s/ns/net", str);
+ snprintf(pathbuf, sizeof(pathbuf), "/proc/%d/ns/net", pid);
```

This restores the proven pre-centralization `ip link` behavior and also removes the current dead-use smell where `pid` is populated only as a validation side effect.

## Test design

The smallest regression test should avoid requiring another long-lived process or a named namespace.

A test can:

1. obtain its own shell/test process PID;
2. express that PID in hexadecimal and octal;
3. call a path that reaches `netns_get_fd()` and only needs the namespace fd to be valid;
4. verify current source rejects the alternate form and the candidate accepts it;
5. keep a decimal control.

For a direct helper-level test, the fixture can compare the returned fd's namespace inode against `/proc/self/ns/net` with `fstat()`.

For an `ip link` integration test, use a disposable network namespace/link fixture and a short-lived helper process whose PID is known. The candidate must move the link to the same namespace for decimal, hexadecimal, and octal spellings under otherwise identical conditions.

The helper-level test is preferable if iproute2's test conventions provide an easy library unit surface; otherwise the integration path proves the user-visible regression directly.

## Evidence boundary

Demonstrated:

- exact current source parses PID fallback with base zero and then ignores the parsed integer during procfs path construction;
- the pre-centralization `ip link` fallback used the parsed integer with `%d`;
- current `get_integer()` delegates to `strtol()` with the supplied base;
- equivalent hexadecimal and octal PID spellings reproduce old-success/current-ENOENT against live procfs;
- decimal remains a passing control;
- the one-line candidate restores the identity normalization performed by the old code.

Not yet demonstrated:

- a build of current iproute2 from the exact reviewed head with the candidate applied;
- the repository's full test suite;
- a user-visible `ip link` move executed with the exact current binary;
- behavior on non-procfs compatibility layers;
- the separate fallback-on-non-ENOENT concern.

## Cleanup

The local reproduction opens only namespace file descriptors for its own process and closes them. It creates no network namespace, link, mount, or persistent state.

## Current disposition

- State: `EXECUTING`
- Exact current source: `iproute2/iproute2@7385bcedf313c1e2edfc1e17c0a3659e2f137d7d`
- History boundary: May 2026 fallback centralization
- Reproducer: `repro.c`
- Candidate: one-line parsed-PID path fix
- Cleanup state: complete
- Next safe action: build/test the candidate on an owned fork or disposable exact-head checkout if available; otherwise map a repository-native regression test and continue the adjacent errno-fallback question separately
- External-contact state: no upstream interaction authorized or made
