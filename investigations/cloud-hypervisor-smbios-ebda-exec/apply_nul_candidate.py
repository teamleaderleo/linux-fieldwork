#!/usr/bin/env python3
from pathlib import Path

path = Path("arch/src/x86_64/smbios.rs")
text = path.read_text()
marker = "SMBIOS string contains an embedded NUL byte"
if marker in text:
    raise SystemExit(f"embedded-NUL candidate marker already present in {path}")
if "SMBIOS payload exceeds the reserved EBDA range" not in text:
    raise SystemExit("#600 EBDA candidate must be applied before #595 composition candidate")

old_error = '''    /// The SMBIOS payload would extend beyond the reserved EBDA into high RAM.
    #[error("SMBIOS payload exceeds the reserved EBDA range")]
    SmbiosTooLarge,
'''
new_error = old_error + '''    /// SMBIOS strings cannot contain an embedded NUL byte.
    #[error("SMBIOS string contains an embedded NUL byte")]
    StringContainsNul,
'''
if text.count(old_error) != 1:
    raise SystemExit("unexpected SmbiosTooLarge error block count")
text = text.replace(old_error, new_error, 1)

old_write_string = '''fn write_string(
    mem: &GuestMemoryMmap,
    val: &str,
    mut curptr: GuestAddress,
) -> Result<GuestAddress> {
    for c in val.as_bytes().iter() {
'''
new_write_string = '''fn write_string(
    mem: &GuestMemoryMmap,
    val: &str,
    mut curptr: GuestAddress,
) -> Result<GuestAddress> {
    if val.as_bytes().contains(&0) {
        return Err(Error::StringContainsNul);
    }
    for c in val.as_bytes().iter() {
'''
if text.count(old_write_string) != 1:
    raise SystemExit("unexpected write_string body count")
text = text.replace(old_write_string, new_write_string, 1)

anchor = '''    #[test]
    fn smbios_uuid_invalid_rejected() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected uuid test anchor count")

test = r'''    #[test]
    fn smbios_embedded_nul_string_is_rejected() {
        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(SMBIOS_START), 4096)]).unwrap();
        let smbios = SmbiosConfig {
            system: Some(SmbiosSystem {
                manufacturer: Some("maker\0shadow".to_string()),
                ..Default::default()
            }),
            ..Default::default()
        };

        let err = setup_smbios(&mem, Some(&smbios)).unwrap_err();
        assert!(matches!(err, Error::StringContainsNul));
    }

'''
text = text.replace(anchor, test + anchor, 1)
path.write_text(text)
