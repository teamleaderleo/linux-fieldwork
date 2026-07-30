# Cache files need an atomic publication boundary

## In simple words

A filename visible to readers is a claim that the object is complete. Do not create that final name while bytes are still arriving.

Write into a temporary sibling, validate the transfer, flush it, and atomically rename it into place. On failure, remove the temporary file and leave the final name absent.

## Failure pattern

This pattern publishes partial state:

```python
with final_path.open("wb") as cache:
    while chunk := response.read(65536):
        cache.write(chunk)
```

The final path exists immediately. If the network closes early, the process is interrupted, the disk fills, or the client disconnects, later code may see `exists() == True` and treat a prefix as a complete cache hit.

A fixed-length HTTP response needs an explicit count check. Reading with a requested amount can return a short prefix and then EOF without raising the exception a caller expects.

## Safer sequence

```python
with atomic_cache_writer(final_path) as cache:
    received = 0
    while chunk := response.read(65536):
        received += len(chunk)
        cache.write(chunk)
    if expected_size is not None and received != expected_size:
        raise IncompleteRead(...)
```

The writer should:

1. create the temporary file in the same directory as the final object;
2. use a unique name;
3. close and optionally `fsync()` it;
4. publish with `os.replace()` or an equivalent same-filesystem atomic rename;
5. unlink the temporary path in all failure paths.

Using the same directory matters because rename atomicity does not extend across filesystems.

## Response-state boundary

HTTP server error handling must know whether the response has started.

- Before status and headers: a normal `502` response is valid.
- After a `200` status or body bytes: appending a second status line corrupts the protocol. Close the connection and log the owning error instead.

The client may receive a truncated response, but the shared cache must not retain it as valid state.

## Old-cache copies count too

Copying from an older cache into a new generation is still a publication operation. Client disconnects and local I/O failures can interrupt that copy. Use the same temporary-and-replace boundary rather than assuming local reads are infallible.

## Validation shape

A strong regression should require:

- an origin advertising more bytes than it sends;
- the unmodified implementation leaving and later serving the short final file;
- the candidate leaving no final path and no temporary sibling after failure;
- a complete transfer being cached and served after the origin is gone;
- an exception inside the writer cleaning its temporary path;
- old-cache promotion using the same writer;
- complete cleanup of loopback servers and disposable roots.

## Source and validation

This note was derived from issue #123 and `investigations/mmdebstrap-caching-proxy-atomic-cache/README.md`. The executable regression is `tests/test_mmdebstrap_caching_proxy_atomic_cache.py`.

No upstream contact is authorized or made by this note.
