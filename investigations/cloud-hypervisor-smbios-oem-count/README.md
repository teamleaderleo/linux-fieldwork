# Cloud Hypervisor SMBIOS Type 11 OEM-string count

Updated: 2026-08-11

Fieldwork issue: `teamleaderleo/linux-fieldwork#593`

Canonical source: `cloud-hypervisor/cloud-hypervisor` `main` @ `1af93ac7035cda77cd87b0c18b1134ebb0928052`
Controlled fork: `teamleaderleo/cloud-hypervisor`
Primary owner: `arch/src/x86_64/smbios.rs`
Current state: **source-confirmed representation mismatch; executable boundary fixture next**
Upstream-contact state: **disabled / no contact performed**

## TL;DR

SMBIOS Type 11 carries its OEM-string count in one byte. Cloud Hypervisor models that field as `u8`, matching EDK2's canonical `SMBIOS_TABLE_TYPE11.StringCount`, but currently fills it with:

```rust
count: oem_strings.len() as u8,
```

and then writes every OEM string in the supplied list.

`PlatformConfig.oem_strings` accepts a boxed list with no nearby item-count limit. At 256 entries, the serialized Type 11 count therefore becomes `0` while all 256 strings are still appended before the double-NUL terminator. At 257 entries, the advertised count becomes `1` while 257 strings are present.

The smallest correct boundary is to reject a Type 11 list that cannot be represented by the one-byte count before writing any Type 11 bytes.

## Explain like I'm five

The record says how many strings it contains using a counter that can hold 0 through 255.

Cloud Hypervisor currently takes a bigger number and chops it down to fit:

```text
255 strings -> says 255
256 strings -> says 0
257 strings -> says 1
```

It still writes all the strings. The number on the box and the contents of the box disagree.

## Why care

SMBIOS consumers use the fixed fields and trailing string area together. A count that disagrees with the emitted payload creates malformed firmware metadata from an otherwise accepted VM configuration.

This boundary also affects the AArch64 SMBIOS handoff investigation: any fixed VMM-to-firmware buffer needs an explicit producer maximum. Correctly bounding Type 11 removes one unbounded dimension before a permanent handoff size is chosen.

## Exact source evidence

### Cloud Hypervisor writer

Current `SmbiosOemStrings`:

```rust
#[repr(C, packed)]
#[derive(Default, Copy, Clone)]
struct SmbiosOemStrings {
    r#type: u8,
    length: u8,
    handle: u16,
    count: u8,
}
```

Current Type 11 construction:

```rust
let smbios_oemstrings = SmbiosOemStrings {
    r#type: OEM_STRINGS,
    length: size_of::<SmbiosOemStrings>() as u8,
    handle,
    count: oem_strings.len() as u8,
};

curptr = write_and_incr(mem, smbios_oemstrings, curptr)?;

for s in oem_strings {
    curptr = write_string(mem, s, curptr)?;
}
```

The count conversion truncates before the full list is emitted.

### Configuration boundary

`PlatformConfig` exposes:

```rust
pub oem_strings: Option<Box<[String]>>
```

No architecture gate or nearby list-count validation applies to this field in the current source pass.

### Independent representation check

Cloud Hypervisor's EDK2 fork defines the standard Type 11 record as:

```c
typedef struct {
  SMBIOS_STRUCTURE    Hdr;
  UINT8               StringCount;
} SMBIOS_TABLE_TYPE11;
```

So 255 is the largest directly representable list count.

## Predicted boundary behavior

The source arithmetic is deterministic:

| input OEM strings | encoded `count` today | strings written today | disposition |
|---:|---:|---:|---|
| 0 | no Type 11 record | 0 | valid current behavior |
| 1 | 1 | 1 | valid |
| 255 | 255 | 255 | representable upper control |
| 256 | 0 | 256 | malformed mismatch |
| 257 | 1 | 257 | malformed mismatch |

Execution still needs to prove the exact bytes on the controlled fork and protect the boundary with a regression test.

## First executable fixture

Add a unit test beside the existing SMBIOS layout tests.

### Control: 255 strings

1. allocate enough synthetic guest memory at `SMBIOS_START`;
2. generate 255 short OEM strings;
3. call `setup_smbios()`;
4. walk Type 0 and Type 1 to Type 11;
5. assert Type 11 `count == 255`;
6. independently parse the trailing string-set and assert 255 strings.

### Baseline defect: 256 strings

With current product code:

1. generate 256 short OEM strings;
2. call `setup_smbios()`;
3. assert the current Type 11 fixed field reads `count == 0`;
4. independently parse the trailing string-set and assert 256 strings.

That proves the mismatch without depending on a guest OS parser.

### Candidate behavior

After the smallest repair, the 256-item case should return a typed error before Type 11 publication.

## Candidate repair boundary

Leading candidate:

```rust
let count = u8::try_from(oem_strings.len()).map_err(|_| Error::TooManyOemStrings)?;
```

and use `count` in the fixed record.

A dedicated error is clearer than reusing the current `TooManyStrings` variant because that variant describes string-index allocation inside Type 1/Type 3 records. Type 11 has a different one-byte field: the list count itself.

Keep the product change inside the SMBIOS encoder unless execution shows the CLI/API should reject earlier for a stronger user-facing contract.

## Adjacent checks

### Empty Type 11

Current code omits Type 11 when the list is empty. Preserve that behavior.

### 255-item success

This is the essential negative control. A repair that rejects 255 would waste one valid count value.

### Per-string byte length

Individual strings are another possible encoder bound, but this investigation does not widen into that question without a separate spec/source discriminator. The current proven defect is the list count truncation.

### Other `as u8` conversions

Do a bounded scan of SMBIOS serialization for variable-length values converted with `as u8`. Promote only another conversion whose source value can exceed the target representation through supported configuration.

## Evidence boundary

Established:

- Type 11 count is one byte in both Cloud Hypervisor and EDK2's SMBIOS definition;
- Cloud Hypervisor currently truncates `oem_strings.len()` with `as u8`;
- Cloud Hypervisor writes the entire list after storing the truncated count;
- current platform configuration exposes an unbounded OEM-string list;
- no matching upstream issue surfaced in the search performed for this round.

Pending:

- executable 255/256 byte-level fixture;
- focused test result on the controlled fork;
- selected error name/location;
- Clippy/rustfmt result for a candidate;
- any upstream review or submission decision.

## Stop condition

This lane is ready for a candidate when:

1. 255 serializes with count 255 and 255 parsed strings;
2. current 256 serializes with a wrapped count and 256 parsed strings;
3. candidate 256 returns a typed error before Type 11 publication;
4. existing SMBIOS layout tests remain unchanged;
5. no broader parser/config change is required to enforce the one-byte representation.

## Next safe action

Create a fork branch from the controlled `teamleaderleo/cloud-hypervisor` main, add the compact 255/256 unit fixture first, and use the current writer unchanged to capture the baseline defect. Then add the minimal checked conversion on the same exact base and run the focused SMBIOS tests if the fork's Actions workflow permits it.
