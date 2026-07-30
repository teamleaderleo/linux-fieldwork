# Green patches need a composed source gate

## In simple words

Two fixes can each pass every test alone and still fail when combined. If they edit the same function, one patch may no longer apply, one mechanism may overwrite another, or their assumptions may conflict even after the code is merged by hand.

## Stable lesson

Treat a set of retained patches as a dependency graph, not a folder of independent successes.

For every multi-fix source area:

1. name the canonical patch order or generate one combined source state;
2. apply it to the exact baseline in CI;
3. run inherited behavior from every constituent repair against that one state;
4. assert that every required repair is present;
5. make overlapping semantic assumptions explicit;
6. regenerate any upstream packet from the composed state, not by concatenating stale diffs.

## Why isolated CI is insufficient

An isolated regression proves only:

```text
baseline + patch A
```

or:

```text
baseline + patch B
```

It does not prove:

```text
baseline + A + B
```

The missing proof matters when:

- both patches add helpers at the same anchor;
- both rewrite the same loop;
- one branch was based on an older version of another repair;
- one repair changes the representation that another validates;
- patch fuzz silently chooses a different context.

## caching_proxy example

The atomic-publication repair, downstream-framing repair, and declared-length repair all touch the fresh response path.

The framing repair accepts a chunked upstream message, removes `Transfer-Encoding`, and suppresses conflicting `Content-Length` after `http.client` decodes the chunks. The isolated declared-length repair reads `Content-Length` unconditionally and compares it to decoded bytes.

A mechanical combination would reject the framing candidate's chunked control. The composed source must validate `Content-Length` only when the upstream response is not chunked.

That conflict appears only when the fixes are executed together.

## Useful gate shape

A useful integration gate should include:

- an exact baseline source boundary;
- a manifest of mandatory repairs;
- source-anchor or patch-contract checks that fail on drift;
- one shared candidate file;
- representative dynamic behavior from each repair;
- a case that crosses the repair boundary;
- cleanup and rerun assertions.

## Limits

A composed gate is not a substitute for upstream review or the full project suite. It proves that the repository's own canonical fixes form one coherent source state under the tested environment.

## Related record

- `investigations/caching-proxy-composed-stack/README.md`
- Integration issue #145
