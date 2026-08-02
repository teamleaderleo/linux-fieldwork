# Downstream context — PipeWire loop selection

## Purpose

Sample one real `FNM_EXTMATCH` consumer and identify which side supplies the pattern, which side supplies the candidate string, and what remains unknown before discussing practical severity.

This is a boundary map, not a PipeWire vulnerability report.

## Exact source

- Project: PipeWire
- Read commit: `7dc83ab5a282996721f285336199807413357989`
- Source owner: `src/pipewire/context.c`
- Node caller: `src/pipewire/impl-node.c`

## Operation

`pw_context_acquire_loop()` reads:

```text
node.loop.name
node.loop.class
```

from the supplied property dictionary. It passes those values as the first argument to `fnmatch`, which makes them the patterns:

```c
fnmatch(name, configured_loop_name, FNM_EXTMATCH)
fnmatch(klass, configured_loop_class, FNM_EXTMATCH)
```

`acquire_data_loop()` repeats the class match across configured classes for each data loop.

The node implementation calls:

```c
this->data_loop = pw_context_acquire_loop(context, &properties->dict);
```

while constructing a node. Several modules also call the same API with their module property dictionaries.

## Argument ownership

### Pattern

The pattern is the requesting node or module property:

- `node.loop.name`;
- `node.loop.class`.

PipeWire documents these as node properties used to place a node on a specific loop name or class. Application and module construction paths can populate node properties.

### Candidate string

The candidate is the server-side data-loop identity:

- the loop implementation name;
- one of the configured loop classes;
- the fixed string `main` for the main-loop special case.

`context.data-loops` and `loop.class` are server configuration surfaces. Typical candidate strings are short, such as `data-loop.0`, `data.rt`, or `main`.

## Consequence for the glibc finding

The first glibc reproducer uses a long candidate string and a short ambiguous pattern. PipeWire's ordinary configured loop names/classes appear short, so the exact demonstrated 38-byte candidate family does not directly establish a large default PipeWire delay.

The argument direction still matters:

- a node property can carry the ambiguous extglob pattern;
- the server calls libc matching synchronously during loop acquisition;
- it may evaluate the pattern against several configured loops and classes.

A separate experiment is required to determine whether a compact configured candidate can combine with a longer or nested pattern to create meaningful cost.

## Unresolved authority boundary

Source review has not yet established:

- which remote-client factories accept arbitrary `node.loop.name` or `node.loop.class` values;
- whether server access modules or policy managers rewrite, reject, or bound them;
- whether ordinary application clients can trigger repeated node creation with such values;
- default maximum property length;
- whether the call occurs on a latency-sensitive or serialized server thread in each path.

Those questions determine whether this is only an administrator-controlled configuration cost, a local same-user denial-of-service surface, or an irrelevant caller example.

## Current conclusion

PipeWire confirms production use of `FNM_EXTMATCH` and establishes mixed ownership: requester properties are patterns; server loop configuration supplies candidate strings. It does not yet establish an attacker-controlled, high-cost invocation.

## Stop rule

Do not widen the glibc investigation into a PipeWire issue unless a synthetic local PipeWire fixture demonstrates:

1. an accepted low-trust property path;
2. a measurable synchronous delay;
3. a clear process or service consequence;
4. clean teardown and rerun.
