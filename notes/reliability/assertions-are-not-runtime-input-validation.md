# Assertions are not runtime input validation

## In simple words

Python can remove every `assert` statement when code runs with `-O` or `PYTHONOPTIMIZE`. An assertion is useful for internal invariants during development; it is not a reliable guard for network, file, archive, command-line, or environment input.

## Stable rule

Use explicit control flow for conditions that must hold in production:

```python
if response.status != 200:
    raise ProtocolError(...)
```

Do not use:

```python
assert response.status == 200
```

when continuing would change files, publish cache entries, authorize an operation, or accept external data.

## Why tests often miss this

Normal test execution keeps assertions enabled. A negative control can therefore look correct while optimized execution removes the entire guard.

For security, integrity, or lifecycle boundaries, run at least one real optimized-interpreter case:

```sh
python3 -O probe.py
PYTHONOPTIMIZE=1 python3 probe.py
```

Static source checks are useful but do not replace execution under stripped bytecode.

## Failure shape

An assertion used for protocol validation can turn:

```text
origin: 404 + error body
```

into:

```text
proxy: 200 + cached error body
```

when optimization is enabled. The bug is not that the assertion message changes; the validation disappears entirely.

## Review checklist

- Is the asserted value influenced by a caller, network peer, archive, file, environment variable, or subprocess?
- Can execution after the assertion mutate state or produce externally visible success?
- Does the regression run with assertions disabled?
- Is the check validating a protocol field or only documenting an impossible internal state?
- Does the exception type feed the intended error/cleanup path?

## Related record

- `investigations/caching-proxy-origin-status/README.md`
- Issue #168
- Request-side optimized validation issue #150
