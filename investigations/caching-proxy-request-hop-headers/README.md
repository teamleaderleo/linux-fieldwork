# caching_proxy origin request-header boundary

## In simple words

The imported cache proxy sends the client's complete header mapping to the requested origin. That can expose proxy credentials and connection-only fields that belong only between the client and the local proxy.

This investigation retains a real loopback origin that records exact received headers, a baseline credential/hop-header leak, and a candidate that filters hop-by-hop fields while preserving required and repeated end-to-end fields.

## Existing work and duplicate search

- canonical issue: #127;
- response framing/hop normalization: #116 / PR #120;
- cache-root containment: #93 / PR #94;
- atomic publication: #95 / PR #96;
- no existing candidate covered request-side `Proxy-Authorization`, `Connection` tokens, or repeated safe headers.

## Question

Can the proxy contact an origin without forwarding proxy credentials or downstream connection controls, while preserving `Host`, conditional/range/content-negotiation fields, and repeated safe headers?

## Source and test map

Fresh origin requests currently use:

```python
conn.request("GET", self.path, None, dict(self.headers))
```

This has two independent consequences:

1. proxy-specific and hop-by-hop fields are sent to the origin;
2. converting the parsed HTTP message to a dictionary collapses repeated fields before forwarding.

The regression starts the real imported or temporarily patched handler, sends a raw downstream request with mixed-case proxy credentials and hop fields, and records the exact header list at a real local origin.

## Baseline negative control

The downstream request includes fake-only values:

- mixed-case `Proxy-Authorization`;
- `Proxy-Connection`;
- `Connection: close, X-Hop`;
- `Keep-Alive`, `TE`, `Trailer`, `Transfer-Encoding`, and `Upgrade`;
- token-named `X-Hop`;
- two separate `X-Safe` fields;
- `Range`, `If-None-Match`, `Accept`, `Host`, and zero `Content-Length`.

The imported proxy is required to expose the fake proxy credential, connection controls, and `X-Hop` to the local origin and to lose the complete two-value `X-Safe` representation through dictionary conversion.

## Candidate

The candidate:

- reads `Connection` values case-insensitively;
- removes standard hop-by-hop request fields;
- removes every field named by a `Connection` token;
- always removes proxy authorization and proxy connection fields;
- rejects duplicate Host fields and a Connection token that attempts to make Host hop-specific;
- iterates `raw_items()` to preserve repeated end-to-end fields;
- sends one explicit `Connection: close` to the origin;
- retains the absolute request target and existing response/cache behavior.

## Assertions

The real-origin candidate matrix requires:

- no proxy credential or blocked hop field at the origin;
- no token-named custom hop field;
- exactly one origin-hop `Connection: close`;
- one preserved Host;
- two separately preserved `X-Safe` values;
- preserved Range, conditional, and Accept fields;
- HTTP 400 and zero origin contact for duplicate Host or `Connection: Host`;
- exact patch application and no remaining `dict(self.headers)` forwarding;
- explicit shutdown and joined threads for origin and proxy.

## Evidence boundary

This candidate handles request headers for the origin hop. It does not:

- add proxy authentication;
- validate every absolute-form request-target and cache-key alias (separate containment/canonicalization work);
- normalize response framing (PR #120);
- redesign streamed error signaling (#132);
- decide a general policy for request bodies, methods other than GET, or trailer forwarding;
- prevent an origin selected by the client from receiving legitimate end-to-end authorization intended for that origin.

## Cleanup and rerun

All credentials are fake literals. Servers bind ephemeral loopback ports, cache roots are disposable temporary directories, sockets are closed, server threads are joined, and no external network, package, privilege, mount, or persistent host state is used.

## Reusable note

See `notes/security/proxies-must-separate-proxy-and-origin-credentials.md`.

## Authority

Internal Linux Fieldwork candidate only. No external issue, email, merge request, patch submission, comment, or review is authorized or included.

## Next step

Run exact-head repository CI. If the baseline leak and candidate origin-capture matrix pass, retain this as the canonical carrier for #127 and review composition with the response, atomic, length, and containment stacks.
