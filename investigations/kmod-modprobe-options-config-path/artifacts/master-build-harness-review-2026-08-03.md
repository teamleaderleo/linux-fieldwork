# kmod exact-master build harness review — 2026-08-03

State: `HARNESS REPAIR — FRESH GCC/CLANG MATRIX PENDING`  
Parent carrier: PR #412  
External contact: none

## Existing package-level result

The retained Debian package probe establishes the recursive configuration identity loss:

```text
no-space path: parent/nested marker counts 1/1
spaced path:   parent/nested marker counts 1/0
```

That result remains package-level evidence. It does not by itself establish behavior in current kmod master.

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

## Failure owner

Ubuntu 24.04 provides mbedTLS 2.28.8. Exact kmod master declares:

- `mbedtls` as an independently selectable feature, enabled by default;
- mbedx509 >=3.6.0 when that feature is enabled;
- `openssl` as a separate enabled signature backend requiring libcrypto >=3.0.0.

The recursive `modprobe -C` discriminator does not exercise module-signature parsing. Selecting the available OpenSSL backend and disabling the unavailable optional mbedTLS backend preserves all relevant modprobe/tool code.

This is a source-build harness/dependency-selection failure. No current-master recursive configuration result exists yet.

## Bounded repair

The stacked carrier:

- removes Ubuntu's incompatible `libmbedtls-dev` package from the focused job;
- configures exact master with `-Dmbedtls=disabled` and `-Dopenssl=enabled`;
- preserves exact source SHA, GCC/Clang, ASan/UBSan, tools, and the two-run discriminator;
- records source, compiler, Meson, Ninja, and OpenSSL identities;
- captures `meson-setup.log` and `build.log` before any possible failure;
- always uploads the compiler-specific receipt directory;
- keeps source and temporary-state cleanup checks.

A focused workflow-contract test encodes the exact feature selection and required receipts.

## Evidence boundary

Disabling mbedTLS is appropriate for this argument-serialization discriminator, not a general recommendation for how distributions should build kmod. Signature-backend parity remains outside this investigation.

The earlier package result remains valid. A fresh exact-master run is required before claiming master reproduces or fixes the recursive configuration loss.

## Next step

Run both compiler jobs. If configuration and compilation pass, execute the exact discriminator twice and compare byte-identical JSON. If either compiler fails, use the newly retained setup/build logs to classify the first failure before changing source or product assumptions.
