# Deno fetch family racing versus response stalls

## TL;DR

Deno 2.9.4 already races a healthy IPv4 address after an IPv6 connection attempt is blackholed. The public reproduction instead accepts the IPv6 TCP connection and then withholds HTTP bytes. That is a response stall after connection establishment, not missing Happy Eyeballs behavior.

No Deno product change is supported by this fixture. A future response-timeout or retry proposal would need a separate contract for request idempotency, body replayability, proxies, TLS, pooling, and duplicate side effects.

## Explain like I'm five

Happy Eyeballs helps when one door will not open. The reported test opens the first door and then nobody answers. Trying a second door after that would mean sending the request twice, which can be dangerous.

## Why care

Misclassifying a response stall as address-family connection failure can lead to a retry mechanism that duplicates HTTP requests. The negative result preserves a useful boundary: connection racing belongs before one socket wins, while response retry belongs to a higher layer with method and body semantics.

## Source and evidence boundary

- Project: Deno
- Stable runtime: 2.9.4
- Controlled fork: `teamleaderleo/deno`
- Fork source head reviewed before probe: `3ee245fe9da563cacb0b6458c4280b5a2758782c`
- Probe branch head: `e209a4846a64dad59747ac71fe84eaef21714279`
- Controlled fork PR: `teamleaderleo/deno#2`
- Linux Fieldwork issue: #253
- Public report: https://github.com/denoland/deno/issues/36279
- Public contact: unauthorized and not made

The fork PR changes only a deterministic probe and its workflow. It does not change Deno product code.

## Source ownership

Current fork source constructs hyper-util's `HttpConnector` in `ext/fetch/dns.rs`. The permission wrapper resolves and validates every destination address before passing the vetted set into that connector. Address-family racing therefore belongs to the connector's connection-establishment path.

Once TCP has connected and an HTTP request has been written, a later timeout is owned by HTTP response handling. Starting another connection and replaying the same request is a different mechanism.

## Probe design

The workflow adds one deterministic dual-stack hostname with IPv6 first:

```text
::1 dualstack-fieldwork.test
127.0.0.1 dualstack-fieldwork.test
```

It then runs two cases under Deno 2.9.4 on Ubuntu 24.04.4.

### Case A — accepted connection, silent response

- IPv4 server is ready to return `200 ipv4-ok`.
- IPv6 listener accepts TCP and sends no HTTP bytes.
- `fetch()` has a 1500 ms abort timeout.

This models the public reproduction.

### Case B — connection blackhole

- IPv4 server is ready to return `200 ipv4-ok`.
- An ip6tables rule drops outbound IPv6 SYN packets for the test port.
- No IPv6 connection can complete.
- `fetch()` has a 2000 ms abort timeout.

This models the RFC 8305 connection-racing condition.

## Exact hosted result

Workflow run: `30593513414`  
Job: `91040734511`  
Conclusion: success  
Artifact: `fetch-family-racing-results`  
Artifact ID: `8780271006`  
Artifact ZIP SHA-256: `02f792c8277cca7795418a13cf18331daa1a58e53b92e77aa3953a6c2cb0be5c`

Observed JSON values:

```text
response-stall:
  elapsedMs: 1502
  status: null
  errorName: TimeoutError
  errorMessage: The operation was aborted due to timeout
  ipv4Requests: 0
  ipv6Accepts: 1

connect-race:
  elapsedMs: 305
  status: 200
  body: ipv4-ok
  errorName: null
  ipv4Requests: 1
  ipv6Accepts: 0
```

## Interpretation

The connection-race case succeeds at about the expected family-attempt delay. Stable `fetch()` therefore already has the behavior the public issue asks for at the connection-establishment layer.

The response-stall case proves only that Deno does not replay a request through IPv4 after IPv6 TCP has already connected. That is the conservative behavior for an ordinary HTTP client because the server may have received and acted on the request before withholding a response.

## Compatibility and negative ramifications

A response retry mechanism would need to answer at least:

- which methods are retryable;
- whether request bodies are buffered and replayable;
- whether the first server may already have applied a side effect;
- how redirects, authentication, proxies, TLS, and connection pools interact;
- how the losing or timed-out socket is cancelled;
- which timeout starts before headers, between body chunks, or around the whole request;
- how callers opt in or observe retries.

These questions are broader than Happy Eyeballs and should not be hidden inside the connector.

## Cleanup and rerun boundary

The workflow installs the IPv6 drop rule only for Case B and removes it through an EXIT trap. Both test servers shut down in the probe. The hosted runner is disposable. The run retained only the two JSON files.

The exact run demonstrates Deno 2.9.4 behavior on one Linux resolver order and loopback transport. It does not prove every platform, DNS backend, proxy path, or current-source build.

## Disposition

Retain as a negative product-fix result. Close the Happy Eyeballs investigation after the tracked record is merged. A separately scoped response-header timeout or safe-retry investigation may be opened only with an explicit replay contract.