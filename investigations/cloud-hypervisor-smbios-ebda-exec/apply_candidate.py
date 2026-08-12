#!/usr/bin/env python3
from pathlib import Path

path = Path("arch/src/x86_64/smbios.rs")
text = path.read_text()
marker = "SMBIOS payload exceeds the reserved EBDA range"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

old_import = "use crate::layout::SMBIOS_START;\n"
new_import = "use crate::layout::{HIGH_RAM_START, SMBIOS_START};\n"
if text.count(old_import) != 1:
    raise SystemExit("unexpected SMBIOS_START import count")
text = text.replace(old_import, new_import, 1)

old_error = '''    /// SMBIOS string index overflow (u8 limit reached).
    #[error("SMBIOS string index overflow (u8 limit reached: {})", u8::MAX)]
    TooManyStrings,
'''
new_error = old_error + '''    /// The SMBIOS payload would extend beyond the reserved EBDA into high RAM.
    #[error("SMBIOS payload exceeds the reserved EBDA range")]
    SmbiosTooLarge,
'''
if text.count(old_error) != 1:
    raise SystemExit("unexpected TooManyStrings error block count")
text = text.replace(old_error, new_error, 1)

old_write = '''fn write_and_incr<T: ByteValued>(
    mem: &GuestMemoryMmap,
    val: T,
    mut curptr: GuestAddress,
) -> Result<GuestAddress> {
    mem.write_obj(val, curptr).map_err(Error::WriteData)?;
    curptr = curptr
        .checked_add(size_of::<T>() as u64)
        .ok_or(Error::NotEnoughMemory)?;
    Ok(curptr)
}
'''
new_write = '''fn write_and_incr<T: ByteValued>(
    mem: &GuestMemoryMmap,
    val: T,
    mut curptr: GuestAddress,
) -> Result<GuestAddress> {
    let end = curptr
        .checked_add(size_of::<T>() as u64)
        .ok_or(Error::NotEnoughMemory)?;
    if end > HIGH_RAM_START {
        return Err(Error::SmbiosTooLarge);
    }
    mem.write_obj(val, curptr).map_err(Error::WriteData)?;
    curptr = end;
    Ok(curptr)
}
'''
if text.count(old_write) != 1:
    raise SystemExit("unexpected write_and_incr body count")
text = text.replace(old_write, new_write, 1)

anchor = '''    #[test]
    fn smbios_uuid_invalid_rejected() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected uuid test anchor count")

test = r'''    #[test]
    fn smbios_payload_cannot_cross_into_high_ram() {
        const SENTINEL_LEN: usize = 64;
        let ebda_tail = HIGH_RAM_START.raw_value() - SMBIOS_START;
        let mem = GuestMemoryMmap::from_ranges(&[(
            GuestAddress(SMBIOS_START),
            ebda_tail as usize + 0x20_000,
        )])
        .unwrap();
        mem.write_slice(&[0xFE; SENTINEL_LEN], HIGH_RAM_START)
            .unwrap();

        let smbios = SmbiosConfig {
            system: Some(SmbiosSystem {
                manufacturer: Some("A".repeat(70 * 1024)),
                ..Default::default()
            }),
            ..Default::default()
        };

        let err = setup_smbios(&mem, Some(&smbios)).unwrap_err();
        assert!(matches!(err, Error::SmbiosTooLarge));

        let mut sentinel = [0u8; SENTINEL_LEN];
        mem.read_slice(&mut sentinel, HIGH_RAM_START).unwrap();
        assert_eq!(sentinel, [0xFE; SENTINEL_LEN]);
    }

'''
text = text.replace(anchor, test + anchor, 1)
path.write_text(text)
