# glibc target map

## In simple words

glibc provides the C library and dynamic loader used by most Debian and GNU/Linux programs. Small mistakes or pathological cases can propagate into many unrelated callers, so investigations must separate the library mechanism from each caller's input and authority contract.

## Canonical source

- Project: GNU C Library
- Canonical development: Sourceware glibc Git and libc-alpha project infrastructure
- Read-only GitHub mirror used for exact source retrieval in this investigation: `bminor/glibc`
- Upstream tag: `glibc-2.41`
- Resolved tag commit: `74f59e9271cbb4071671e5a474e7d4f1622b186f`
- Relevant tag source: `posix/fnmatch_loop.c`, blob `9ec5e0edc656a774b3d1ab43c86755fe0c236672`
- Relevant test driver: `posix/tst-fnmatch.c`, blob `06343cbae5b34b58793deacc2c293e06b644df86`
- Relevant test data: `posix/tst-fnmatch.input`, blob `796683afedf9d8554c3d81a246f88a865fddbb9e`

The GitHub mirror is marked archived and its visible master history is not treated as proof of the current canonical Sourceware head. Exact release tags and retrieved blobs remain valid source identities for bounded investigations.

## Distribution boundary

First execution environment:

- Debian glibc package `2.41-12+deb13u2`;
- runtime reports `glibc 2.41`;
- runtime libc SHA-256 `adeedbc69ac402b762a3bd94759441e0546c33972cb2c0f5bc6869a2d32efed6`.

The installed Debian binary is not claimed to be byte-identical to the upstream tag build. Source mechanism and runtime behavior are recorded as related but distinct evidence.

## Relevant programmes

- `ecosystem-contributions`, LF-39 foundational-library boundary corpus;
- `services-resources` when findings concern cancellation, allocation, or process cleanup;
- `security-networking` only when a concrete authority or remotely influenceable resource boundary is demonstrated.

## Active investigations

- [`glibc-fnmatch-extmatch-complexity`](../../investigations/glibc-fnmatch-extmatch-complexity/README.md) — ambiguous extended patterns cause rapid rejection-time growth.

## High-yield source areas

- `posix/fnmatch*`, `glob*`, `wordexp*`, regex, and locale-sensitive parsing;
- `stdlib` path canonicalization, allocation, conversion, and environment APIs;
- `nptl` cancellation, fork, robust synchronization, and cleanup;
- `io` descriptor lifecycle and partial-I/O contracts;
- dynamic loader parsing and process-startup boundaries.

## Contribution boundary

Public glibc reports and patches normally require careful current-head reproduction, full source builds, project-native tests, and libc-alpha/Sourceware workflow awareness. Linux Fieldwork records and local candidates create no authority to contact the project.
