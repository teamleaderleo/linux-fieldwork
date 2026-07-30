# Cache files must be published atomically

## Principle

A cache filename should mean “complete object,” not “a writer has started.” Writing directly to the final path exposes partial state to concurrent readers and makes a successful cache hit indistinguishable from an in-progress fill.

Threaded services are especially vulnerable:

1. request A checks that the cache path is absent;
2. request A opens the final name with truncation and begins streaming;
3. request B sees the final name and serves its current size and bytes;
4. request B reports success with truncated content;
5. request A later completes, erasing the evidence in the final cache file.

## Safe publication pattern

For each cache fill:

1. create a unique temporary file in the destination directory;
2. stream and validate the complete object into that temporary file;
3. close the writer;
4. atomically replace the final path;
5. remove the temporary file on every exception path.

Using the same directory keeps the rename on one filesystem. `os.replace()` gives atomic final-name publication on supported local filesystems.

## What atomic publication does not solve

Two concurrent cache misses may still perform duplicate upstream downloads and race to replace the final path. When the URL is immutable or both responses are equivalent, this is inefficient but not partial publication.

A per-key lock or request coalescing is appropriate when duplicate work, changing upstream responses, or bandwidth is material. It is not required merely to ensure readers see only complete files.

Atomic rename also does not verify content integrity by itself. Checksums, expected lengths, or signed metadata remain separate validation layers.

## Failure handling

Client disconnects and upstream failures can occur after response headers were sent. The cache writer must still avoid publication and remove its temporary file. Do not leave a short final path that future requests treat as valid.

Readonly sinks such as `/dev/null` do not need publication and should keep their existing behavior.

## Regression shape

Use a synchronized upstream that:

- sends one chunk;
- blocks before the remainder;
- allows a second request for the same URL.

The negative control should prove that the second request receives the currently written partial cache file without making a second upstream request. The candidate should keep the final name absent, allow both writers to finish into unique temporary files, return complete bodies to both clients, atomically publish one complete final file, and leave no temporary files.

Also inject a writer exception and require no final path and no retained temporary file.

## mmdebstrap example

`caching_proxy.py` historically wrote both old-cache copies and fresh downloads directly to `newpath` while using `ThreadingHTTPServer`. Issue #95 records the synchronized partial-response boundary and the atomic-publication candidate.
