# Draft upstream issue: recursive modprobe can lose custom configuration identity

## Proposed title

`modprobe: recursive invocation can lose -C configuration path identity`

## Summary

A `modprobe` process invoked with `-C <path>` can use the requested configuration correctly in the parent, but an `install` command that invokes another `modprobe` can cause the child to use a different configuration when the path contains whitespace.

The current implementation appends `-C` and the raw pathname to the single `MODPROBE_OPTIONS` environment string. The nested `modprobe` reparses that flattened string, so a pathname containing whitespace can become multiple arguments.

The operation can still return success, which makes the configuration-policy change silent.

## Minimal behavior

Observed on current upstream source as well as Debian `kmod 34.2-2`:

```text
no-space custom config:
  parent sees marker: yes
  nested child sees marker: yes

space-bearing custom config:
  parent sees marker: yes
  nested child sees marker: no
  parent exit status: 0
  nested exit status: 0
```

A directly quoted `MODPROBE_OPTIONS` value is a passing control. Other parser-sensitive whitespace cases also show that the environment string is not a lossless argv transport.

## Why this matters

This is primarily a configuration-integrity and correctness problem. A caller can reasonably expect an explicit custom configuration to remain in effect for recursive `modprobe` operations, while the nested process may silently evaluate aliases, options, install/remove commands, dependencies, and related policy from a different configuration set.

No standalone privilege-escalation or arbitrary-code-execution claim is being made. Module operations normally already require appropriate privilege, and `install` rules are themselves command-capable configuration.

## Current source

The behavior was rechecked on upstream master through `dae6c02ffed2e8d16da8dba16d974fc955eebb1f`. The relevant `MODPROBE_OPTIONS` flatten/reparse mechanism remains present.

GCC and Clang ASan/UBSan executions reproduce the recursive configuration split without sanitizer findings.

## Fix direction

A simple quoting-only change is probably not sufficient because the environment value also has legacy parsing behavior that should not be changed accidentally.

The preferred direction is to preserve legacy `MODPROBE_OPTIONS` compatibility while transporting values generated internally by kmod without losing argv boundaries. Any patch should also avoid recursive option-list growth and preserve inherited private options and install-script mutations that current kmod accepts.

## Reproducer / tests

A compact reproducer and a target-native paired control/discriminator are available. The paired native test uses a dependency-free install-command fixture and performs no real module insertion.

## Scope

This issue is intentionally limited to recursive configuration identity. A separate explicitly-empty `MODPROBE_OPTIONS` allocation bug has been isolated independently and should not be mixed into this report.
