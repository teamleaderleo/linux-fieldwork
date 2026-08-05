# kmod exact-master build harness review — 2026-08-03

State: `HARNESS REPAIR — CLANG RUNTIME FOLLOW-UP PENDING`  
Parent carrier: PR #412  
Stacked carrier: PR #429  
External contact: none

## Existing package-level result

The retained package probe establishes the recursive configuration identity loss:

```text
no-space path: parent/nested marker counts 1/1
spaced path:   parent/nested marker counts 1/0
```

That result remains package-level evidence. It did not by itself establish behavior in current kmod master.

## First exact-master attempt

Carrier head `396e9c8a8ee76fade43ba27f4e0bc960cd87eaec` passed Linux Fieldwork CI `30759642200`.

Dedicated source workflow `30759642216` checked out exact kmod master:

```text
5086df53090b2fe9fa1c31351c05a78a12a4ba71
```

Both GCC and Clang jobs verified clean source identity and stopped during Meson configuration before compiling `modprobe` or running the discriminator.

Exact failure:

```text
Dependency mbedx509 found: NO found 2.28.8 but need: '>= 3.6.0'
kmod/meson.build:290:8: ERROR: Dependency lookup for mbedx509 ... failed
```

Artifacts:

```text
GCC:
  id: 8838866650
  sha256:2cc5004799dbfd3a71c32856d33267985e1a5ef1951dc0b44e3f9c90e9a6cfee
Clang:
  id: 8838867422
  sha256:2b3f4e47a8166cf73442fd52d6772a8d514d0763282a25eebd8122bd8fae86b3
```

The artifacts retained only final source status, not the Meson failure log. The console log is therefore required to classify this attempt.

## First repair and exact-master result

Head `6931c2b28219e4a963c8baaf3a782de26dfb0dc0` disabled only the unavailable optional mbedTLS backend and retained OpenSSL, tools, GCC/Clang, ASan/UBSan, exact source identity, two discriminator runs, and failure-time logs.

Run `30796598220` produced a split result.

### GCC — complete success

The GCC job configured, compiled, ran exact-master `modprobe` twice, compared byte-identical JSON, verified cleanup, and uploaded artifact:

```text
id: 8851583964
sha256:b293b4cb444603d777ceaba6545adc569b6dccc041e7ebf2fede2c98a62eaa65
```

Exact result on current master:

```text
no-space path: parent/nested marker counts 1/1
spaced path:   parent/nested marker counts 1/0
outer and nested statuses: 0/0
quoted environment control marker count: 1
```

The immediate rerun was byte-identical. This establishes that exact master `5086df5...` still reproduces recursive `-C` configuration-identity loss in the GCC sanitizer lane.

### Clang — compiled, loader failed before discriminator

The Clang job configured and compiled `modprobe`, but the first executable identity check failed:

```text
error while loading shared libraries: libclang_rt.asan-x86_64.so:
cannot open shared object file: No such file or directory
```

Artifact:

```text
id: 8851578854
sha256:3492890b4bf368cbfe6048049a7a2a256a3cd43799b5f6b1846c45c170abe0eb
```

This is a Clang sanitizer-runtime loader failure. It is not a kmod product failure and does not contradict the complete GCC current-master result.

## Failure ownership

Two independent optional/runtime boundaries were exposed:

1. Ubuntu 24.04's mbedTLS 2.28.8 cannot satisfy exact master’s optional mbedx509 >=3.6 requirement. Disabling that backend is valid for this argument-serialization discriminator, which does not exercise signature parsing.
2. kmod intentionally uses Clang’s shared sanitizer runtime for sanitized builds. Ubuntu’s `clang` package alone did not make `libclang_rt.asan-x86_64.so` loadable in the hosted job.

## Current bounded repair

The stacked carrier now:

- installs Ubuntu’s `libclang-rt-dev` runtime package;
- resolves the exact ASan shared object with `clang --print-file-name`;
- requires the runtime file to exist and records its SHA-256;
- exports only its directory through `GITHUB_ENV` for subsequent build/probe steps;
- records `ldd` output and rejects any unresolved shared library;
- preserves `-Dmbedtls=disabled`, `-Dopenssl=enabled`, GCC/Clang, ASan/UBSan, exact master, two-run comparison, explicit typed result failures, failure artifacts, and cleanup.

The focused workflow contract now contains seven checks and forbids regression of either dependency boundary.

## Evidence boundary

- Exact current master is proven to reproduce the recursive configuration loss under GCC with ASan/UBSan.
- Clang behavior remains pending only because the prior compiled executable could not load its sanitizer runtime.
- Disabling mbedTLS is a focused harness choice, not a general distribution-build recommendation.
- Signature backend parity and a source repair remain separate work.

## Next step

Run the exact current head in both compiler lanes. On Clang green, compare its normalized JSON and SHA identities with the GCC result. On red, use the retained sanitizer-runtime, `ldd`, Meson, and build receipts to classify the first failure before changing source assumptions.
