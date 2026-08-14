# NODELETE RTLD_LOCAL -> RTLD_GLOBAL promotion A/B

Date: 2026-08-14

## Question

A process-resident guest wrapper must still obey useful loader-scope semantics.

One concrete risk is:

```text
open wrapper RTLD_LOCAL
close local handle
reopen same resident object RTLD_GLOBAL
```

If NODELETE accidentally made a locally loaded object globally visible after close, or prevented a later `RTLD_GLOBAL` reopen from promoting it into `RTLD_DEFAULT` scope, that would be an application-visible loader regression.

## Test identity

Owned FEX branch: `diagnostic/nodelete-rtld-global-promotion-20260814`.

Carrier commit: `7a8688c915d4902334f4f9868f57febdd29b700d`.

Hosted ARM64 run: `31777402276`.

Artifact: `nodelete-rtld-global-promotion-31777402276`.

Artifact digest:

```text
sha256:11c6f410edb5fa83507523fe5a85f7da0f703a9f680742e9f344f1450c8a8192
```

The A/B uses the real generated x86-64 GL guest thunk and FEX GL host thunk. Stock and NODELETE guest binaries differ only by the generic `-z,nodelete` policy.

The probe observes `glXGetProcAddress` through both a direct `dlsym(handle, ...)` and `dlsym(RTLD_DEFAULT, ...)`.

## Stock result

Initially the symbol is outside global scope:

```text
DEFAULT initial ptr=(nil)
```

A local open resolves the symbol directly but does not publish it globally:

```text
DIRECT local=0x7ffff7bb8250
DEFAULT local-open ptr=(nil)
```

After closing the local handle the stock guest wrapper is no longer resident:

```text
DEFAULT local-closed ptr=(nil)
NOLOAD after-local-close resident=0 handle=(nil)
```

A later `RTLD_GLOBAL` reopen succeeds, returns the same guest function address, and promotes the symbol into `RTLD_DEFAULT`:

```text
DIRECT global=0x7ffff7bb8250 same=1
DEFAULT global-open ptr=0x7ffff7bb8250 err=none
```

After closing that global handle, the symbol remains visible in this FEX/loader setup:

```text
DEFAULT global-closed ptr=0x7ffff7bb8250 err=none
PROMOTION_PROBE_OK mode=stock
```

## NODELETE result

The important local-scope behavior is identical before promotion:

```text
DEFAULT initial ptr=(nil)
DIRECT local=0x7ffff7bb8250
DEFAULT local-open ptr=(nil)
DEFAULT local-closed ptr=(nil)
```

NODELETE keeps the object resident after the local close, as intended:

```text
NOLOAD after-local-close resident=1 handle=0x5588173a2380
```

But residency does **not** make the symbol globally visible. `RTLD_DEFAULT` remains unable to resolve it until a real `RTLD_GLOBAL` reopen occurs.

That reopen succeeds and promotes the same resident guest symbol normally:

```text
DIRECT global=0x7ffff7bb8250 same=1
DEFAULT global-open ptr=0x7ffff7bb8250 err=none
```

After closing the global handle:

```text
DEFAULT global-closed ptr=0x7ffff7bb8250 err=none
PROMOTION_PROBE_OK mode=nodelete
```

## Meaning

This A/B eliminates two plausible NODELETE loader-scope regressions for the real GL guest wrapper:

1. **Local residency does not accidentally become global scope.** After local close, the NODELETE object is still present under `RTLD_NOLOAD`, but `RTLD_DEFAULT` cannot see `glXGetProcAddress`.
2. **A later `RTLD_GLOBAL` reopen can still promote the resident object normally.** The symbol becomes visible through `RTLD_DEFAULT` and keeps the same guest function identity.

The final `RTLD_DEFAULT` visibility after closing the global handle occurs in **both** stock and NODELETE arms. It is therefore not evidence of a NODELETE-specific scope leak in this experiment.

The bounded conclusion is:

> For the real generated GL guest thunk under this hosted FEX/glibc workload, NODELETE preserves the distinction between local residency and global symbol scope, and does not block later LOCAL -> GLOBAL promotion.

## Limits

- This is one glibc/FEX loader path and one real guest wrapper.
- It does not cover `RTLD_DEEPBIND`, audit namespaces, symbol versioning corner cases, or every `dlmopen()` interaction.
- Static NODELETE's disposable-namespace lifetime caveat remains separately documented in [`NODELETE_NAMESPACE_AND_RUNTIME_PROMOTION.md`](./NODELETE_NAMESPACE_AND_RUNTIME_PROMOTION.md).

All code and CI work described here is confined to owned repositories/forks. No upstream FEX interaction occurred.
