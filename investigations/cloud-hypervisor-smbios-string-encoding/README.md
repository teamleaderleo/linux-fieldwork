# Cloud Hypervisor SMBIOS embedded-NUL encoding

Updated: 2026-08-11

Fieldwork issue: `teamleaderleo/linux-fieldwork#595`
Canonical source: `cloud-hypervisor/cloud-hypervisor` `main` @ `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Primary owner: `arch/src/x86_64/smbios.rs`
Current state: **source-confirmed encoding defect candidate; byte-level fixture pending**
Upstream-contact state: **disabled / no contact performed**

## TL;DR

Cloud Hypervisor writes SMBIOS strings by copying every byte in a Rust `str` and then appending a NUL terminator. Rust strings may contain `\0`, and JSON can represent that byte with `\u0000`.

SMBIOS uses NUL as record syntax: each trailing string is NUL-terminated and the complete string-set ends with an extra NUL. Allowing a configured NUL through `write_string()` therefore changes the number and boundaries of SMBIOS strings after fixed-field indices have already been assigned.

Concrete Type 1 example:

```text
configured manufacturer = "maker\0shadow"
configured product      = "product"

fixed fields:
manufacturer index = 1
product index      = 2

bytes written:
maker \0 shadow \0 product \0 ...

actual trailing strings:
1 = maker
2 = shadow
3 = product
```

The guest resolves Product Name index 2 as `shadow`, not `product`.

The leading repair is central validation in `write_string()` that rejects an embedded NUL before any bytes from that value are published.

## Explain like I'm five

SMBIOS uses zero bytes as commas between strings.

Cloud Hypervisor currently lets a user put a zero byte inside a string. That lets one configured value secretly contain an extra comma.

The table numbers its strings before writing them, so every value after that comma can point at the wrong text.

## Why care

This produces firmware metadata different from the accepted VM configuration while returning success. It can affect manufacturer/product identity and OEM strings consumed by guest software.

This is a local configuration/API correctness defect. No remote or privilege-boundary claim is made.

## Exact source evidence

Current writer:

```rust
fn write_string(
    mem: &GuestMemoryMmap,
    val: &str,
    mut curptr: GuestAddress,
) -> Result<GuestAddress> {
    for c in val.as_bytes().iter() {
        curptr = write_and_incr(mem, *c, curptr)?;
    }
    curptr = write_and_incr(mem, 0u8, curptr)?;
    Ok(curptr)
}
```

There is no NUL check before raw bytes are copied.

Type 1 separately allocates indices from the presence of logical fields, then writes the corresponding values in order. It does not derive indices from the byte-level string-set after serialization.

`PlatformConfig` carries its system identity and OEM values as ordinary Rust `String` / boxed string lists. No nearby validation was found that excludes `\0`.

## Primary discriminator

### Control

Configure:

```text
manufacturer = "maker"
product      = "product"
```

Expected fixed indices and parsed strings:

```text
manufacturer index = 1
product index = 2
strings = ["maker", "product"]
```

### Interior-NUL baseline

Configure:

```text
manufacturer = "maker\0shadow"
product      = "product"
```

Current source predicts:

```text
manufacturer index = 1
product index = 2
strings = ["maker", "shadow", "product"]
```

Resolve the fixed fields through the parsed string-set:

```text
manufacturer -> maker
product      -> shadow
```

The important proof is the semantic mismatch, not merely presence of a zero byte.

### Trailing-NUL adjacent case

Configure manufacturer as `"maker\0"`.

`write_string()` emits the configured trailing NUL and then its own terminator. That creates a double-NUL immediately after `maker`, ending the SMBIOS string-set before the writer emits later Type 1 strings.

Use this as a second discriminator after the interior-NUL case. It may produce a stronger table-walk failure and should remain separate from the first simple identity-shift proof.

## Type 11 neighbor

An OEM string containing `\0` has the same encoding conflict. Type 11 stores a one-byte string count and then emits the list. One configured OEM value can become several encoded strings, so the fixed count can disagree with the byte-level string-set even with fewer than 256 list items.

The separate `cloud-hypervisor-smbios-oem-count` investigation owns list-count truncation. This lane owns byte content.

## Candidate repair boundary

Leading candidate inside the common encoder:

```rust
if val.as_bytes().contains(&0) {
    return Err(Error::StringContainsNull);
}
```

Place this before the first guest-memory write for the value.

Why the encoder leads:

- every Type 1, Type 3, and Type 11 string passes through `write_string()` or `write_opt_string()`;
- JSON/API, CLI, tests, and future callers then share one rule;
- the encoder owns the NUL syntax contract;
- the error occurs before partial publication of that logical string.

A later config-level validation can improve API error classification, but it should not replace the encoder invariant.

## Negative controls

1. ordinary ASCII values preserve exact bytes and indices;
2. empty Rust strings remain a separate semantic question and should keep current behavior unless execution shows another defect;
3. UTF-8 without NUL stays accepted by this candidate;
4. invalid UUID remains `ParseUuid`;
5. the 255 OEM-list control from #593 remains accepted after the NUL fix.

## Evidence boundary

Established:

- `write_string()` copies embedded zero bytes unchanged;
- SMBIOS trailing strings use NUL delimiters;
- Type 1 allocates fixed indices independently before serialization;
- API/config values are represented as Rust strings and no nearby NUL rejection was found;
- no matching upstream or Fieldwork issue surfaced before #595 was created.

Pending:

- executable Type 1 control/interior-NUL byte proof;
- trailing-NUL table-walk observation;
- focused candidate test;
- product/quality gates;
- API-level error mapping decision.

## Stop condition

Select the encoder repair when:

1. the ordinary control resolves manufacturer/product exactly;
2. current interior-NUL input demonstrably retargets the later fixed index;
3. candidate input returns a typed error before the offending value is written;
4. ordinary and UTF-8-without-NUL controls remain unchanged;
5. Type 11 count tests from #593 still pass at their valid boundary.

## Next safe action

Extend the controlled-fork SMBIOS evidence workflow to inject a Type 1 interior-NUL test alongside the 255/256 Type 11 fixture. Preserve the current baseline result, then test one central `write_string()` rejection candidate in a separate carrier.
