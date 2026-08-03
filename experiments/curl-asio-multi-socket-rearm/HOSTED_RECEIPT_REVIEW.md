# Hosted receipt review — curl / Asio re-arm discriminator

State: `WORKFLOW HARDENING — FRESH EXACT RECEIPT PENDING`  
Parent carrier: PR #420  
External contact: none

## Existing hosted result

Exact carrier head `a27240f35d2e08f42204d83119115d5f61cf65ee` passed:

- curl Asio re-arm workflow `30759680701`;
- Linux Fieldwork CI `30759680719`.

The hosted discriminator printed:

```text
one-shot: completed=0 timed_out=1 reads=1 body='hello '
rearm: completed=1 timed_out=0 reads=2 result=No error body='hello world!'
curl multi-socket Asio re-arm discriminator: PASS
```

Artifact:

```text
id: 8838935568
sha256:9a344ab1649b6c3135a01caf15bd7cc60ee4fcdeb3fa3fdf446bc2c67b659743
```

The run used Ubuntu 24.04.4 image `20260720.247.2`, kernel `6.17.0-1020-azure`, Boost 1.83 development headers, and the libcurl 8.5.0 development package.

## Interpretation retained

The loopback-only fixture distinguishes the integration failure class:

- a one-shot Asio readiness wait consumes the first split-response read and stalls while curl's unchanged `CURL_POLL_IN` interest remains active;
- a generation-safe wait that is re-armed receives the second response chunk and reaches completion.

The proof does not depend on DNS, TLS, HTTP/2, Ceph, or a public endpoint. Remove handling, concurrent read/write interest, deliberate cancellation, connection reuse, TLS, HTTP/2, and file-descriptor reuse remain separate gates.

## Review defects

The successful workflow did not yet provide a durable execution contract:

1. `ubuntu-latest` was moving even though the exact receipt came from Ubuntu 24.04.
2. Checkout credentials remained in Git configuration before proposed C++ compiled and executed.
3. The fixture binary and receipt were written into the tracked checkout.
4. The discriminator ran only once, so immediate rerun stability was unproved.
5. The artifact accepted a missing receipt with `if-no-files-found: warn`.
6. The artifact omitted compiler, libcurl, Boost, source, and executable identities.
7. No final step removed generated files and required a clean Git checkout.

These are workflow and evidence defects. They do not weaken the observed one-shot-versus-rearm behavior.

## Bounded repair

The stacked carrier leaves `fixture.cpp` unchanged and:

- pins `ubuntu-24.04`;
- uses read-only permissions and `persist-credentials: false`;
- validates the workflow contract before compilation;
- builds the executable below `RUNNER_TEMP`;
- records source, compiler, libcurl, Boost, runner, and executable identities;
- runs twice and requires both receipts to match the exact three-line discriminator output;
- requires a uniquely named 30-day artifact;
- removes runtime/evidence directories after upload;
- requires the checkout to be clean.

## Evidence boundary

The prior hosted run remains valid behavioral evidence. A fresh run is required before claiming exact identity, rerun parity, artifact completeness, or cleanup under the repaired workflow.

## Next step

Run the exact stacked head. On green, retain the artifact ID and digest, verify both receipts and all identity files, and move the focused workflow unit to `MERGE LOCALLY`. On red, classify the first build, behavior, artifact, or cleanup failure before modifying the fixture.
