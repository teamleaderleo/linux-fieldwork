# iproute2 devlink rate show ignores selector parse errors

Date: 2026-08-12

Internal tracking: `teamleaderleo/linux-fieldwork#610`

Related programme lane: `LF-29` — netlink compatibility and fallback.

## TL;DR

Current `cmd_port_fn_rate_show()` calls `dl_argv_parse_with_selector()` but does not check its return value before building and serializing a `DEVLINK_CMD_RATE_GET` request.

The original 2021 rate-show implementation returned immediately on argument-parse failure. The regression was introduced by the 2023 dump-selector conversion (`70faecdca8f5187d2bc5ee95e4b6a01a50a2c916`). In that same conversion, neighboring show commands all gained `if (err) return err;`; rate-show uniquely omitted it.

In a single command this can turn a parser error into a later netlink error. In batch mode the state/ownership consequence is more serious: the shared `struct dl` can retain presence bits and string pointers from the prior successful command while `dl_argv_parse()` frees the allocation those strings pointed into. Ignoring the next parse error then lets `dl_opts_put()` dereference stale pointers.

A reduced AddressSanitizer model of that exact ownership transition reports heap-use-after-free.

The repair is the missing two-line error check.

No upstream contact is authorized or has been made.

## Source boundary

- Project: `iproute2/iproute2`
- Exact current source: `7385bcedf313c1e2edfc1e17c0a3659e2f137d7d`
- Current function: `devlink/devlink.c::cmd_port_fn_rate_show()`
- Parser: `dl_argv_parse_with_selector()` / `dl_argv_parse()`
- Serializer: `dl_opts_put()`
- Original rate support: `6c70aca76ef25d01b8bdf85101040610fb96b6ae`
- Regression introduction: `70faecdca8f5187d2bc5ee95e4b6a01a50a2c916`

## Correct baseline

The 2021 rate-show implementation did this when a handle was supplied:

```c
err = dl_argv_parse_put(...);
if (err)
    return err;
```

So invalid arguments stopped before request transmission.

## Regression

The 2023 dump-selector conversion replaced that logic with:

```c
err = dl_argv_parse_with_selector(...);

nlh = mnlu_gen_socket_cmd_prepare(...);
dl_opts_put(nlh, dl);
```

without checking `err`.

The same introducing commit adds the missing check immediately after selector parsing in the other converted show commands. This makes the rate-show omission a narrow, high-confidence regression rather than a broad design ambiguity.

Current source still lacks the check.

## Batch ownership path

`dl_argv_parse()` starts by consuming the next handle argument and, when present:

```c
str = strdup(str);
...
free(dl->handle_argv);
dl->handle_argv = str;
```

Parsed handle fields such as `opts->bus_name`, `opts->dev_name`, and `opts->rate_node_name` point into that duplicated buffer.

On a successful parse, `opts->present` is updated near the end of the function.

On a later parse that fails early while interpreting the new handle, the function returns before updating `opts->present`. By then the old `handle_argv` allocation has already been freed, so stale presence bits can coexist with stale pointers into freed memory.

`dl_opts_put()` trusts `opts->present` and passes those pointers to `mnl_attr_put_strz()`.

Normally the parse error would prevent this. `cmd_port_fn_rate_show()` is the missing boundary.

## Reproduction

Tracked fixture: [`repro.c`](repro.c).

Build with AddressSanitizer:

```sh
cc -Wall -Wextra -Werror -O1 -g -fsanitize=address \
   -fno-omit-frame-pointer repro.c -o /tmp/devlink-rate-show-uaf
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 /tmp/devlink-rate-show-uaf
```

The reduced model performs:

1. valid first handle parse, storing pointers into `handle_argv` and a handle presence bit;
2. invalid second parse, which frees/replaces `handle_argv` and returns early;
3. current rate-show behavior, which ignores the error and serializes stale options.

One executed run observed:

```text
ERROR: AddressSanitizer: heap-use-after-free
READ ... in printf_common
freed by ... parse_invalid
previously allocated by ... parse_valid
asan_status=1
```

The fixture uses `printf()` as a reduced serializer. The source-side consumer in iproute2 is `mnl_attr_put_strz()`, which likewise needs to read the stale NUL-terminated string.

## Candidate

Tracked candidate: [`candidate.patch`](candidate.patch).

```diff
 err = dl_argv_parse_with_selector(...);
+if (err)
+    return err;
```

This restores the pre-selector error boundary and matches the neighboring show-command conversions in the regression-introducing commit.

## Evidence boundary

Demonstrated:

- current rate-show ignores the selector parser return;
- current parser frees/replaces `handle_argv` before handle validation can fail;
- parsed option string pointers are stored inside that allocation;
- `opts->present` is only replaced after successful progression to the end of parsing, so an early failure can leave stale presence state;
- request serialization dereferences option strings according to those presence bits;
- the original rate-show code returned on parse failure;
- the 2023 selector conversion introduced the missing check and neighboring conversions contain the check;
- a reduced ASan ownership model reports heap-use-after-free for valid-command -> invalid-rate-show batch state;
- upstream open/closed issue search for this pattern returned no match.

Not yet demonstrated:

- an exact-head devlink binary ASan run through the real batch parser;
- a devlink-capable kernel/device fixture in the current execution environment;
- any privilege-escalation boundary.

The local installed devlink cannot reach command parsing because the environment does not expose the devlink generic-netlink family, so the exact integration path remains an evidence boundary rather than being approximated.

## Cleanup

The reduced ASan source and binary were removed from `/tmp` after execution. No network state was created.

## Current disposition

- State: `EXECUTING`
- Reproducer: present
- Candidate: present
- Exact current source: `iproute2/iproute2@7385bcedf313c1e2edfc1e17c0a3659e2f137d7d`
- Cleanup state: complete
- Next safe action: if an owned iproute2 fork or devlink-capable disposable environment becomes available, run the real batch sequence under ASan; otherwise continue sibling selector-caller auditing
- External-contact state: no upstream interaction authorized or made
