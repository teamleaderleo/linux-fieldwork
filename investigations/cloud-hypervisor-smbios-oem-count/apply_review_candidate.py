#!/usr/bin/env python3
from pathlib import Path

path = Path("arch/src/x86_64/smbios.rs")
text = path.read_text()

err_old = '''    /// SMBIOS string index overflow (u8 limit reached).\n    #[error("SMBIOS string index overflow (u8 limit reached: {})", u8::MAX)]\n    TooManyStrings,\n}\n'''
err_new = '''    /// SMBIOS string index overflow (u8 limit reached).\n    #[error("SMBIOS string index overflow (u8 limit reached: {})", u8::MAX)]\n    TooManyStrings,\n    /// SMBIOS Type 11 OEM string count overflow (u8 limit reached).\n    #[error("SMBIOS OEM string count exceeds {}", u8::MAX)]\n    TooManyOemStrings,\n}\n'''
if err_old not in text:
    raise SystemExit("error enum anchor missing")
text = text.replace(err_old, err_new, 1)

oem_old = '''    if !oem_strings.is_empty() {\n        handle += 1;\n\n        let smbios_oemstrings = SmbiosOemStrings {\n            r#type: OEM_STRINGS,\n            length: size_of::<SmbiosOemStrings>() as u8,\n            handle,\n            count: oem_strings.len() as u8,\n        };\n'''
oem_new = '''    if !oem_strings.is_empty() {\n        handle += 1;\n        let count = u8::try_from(oem_strings.len()).map_err(|_| Error::TooManyOemStrings)?;\n\n        let smbios_oemstrings = SmbiosOemStrings {\n            r#type: OEM_STRINGS,\n            length: size_of::<SmbiosOemStrings>() as u8,\n            handle,\n            count,\n        };\n'''
if oem_old not in text:
    raise SystemExit("OEM Type 11 anchor missing")
text = text.replace(oem_old, oem_new, 1)

test_anchor = '''    #[test]\n    fn smbios_uuid_invalid_rejected() {\n'''
tests = r'''    fn oem_record(mem: &GuestMemoryMmap) -> SmbiosOemStrings {
        let smbios_ep: Smbios30Entrypoint = mem.read_obj(GuestAddress(SMBIOS_START)).unwrap();
        let mut cur = GuestAddress(smbios_ep.physptr);

        let bios: SmbiosBiosInfo = mem.read_obj(cur).unwrap();
        cur = cur.checked_add(bios.length as u64).unwrap();
        let (_, next) = read_string_set(mem, cur);
        cur = next;

        let sys: SmbiosSysInfo = mem.read_obj(cur).unwrap();
        cur = cur.checked_add(sys.length as u64).unwrap();
        let (_, next) = read_string_set(mem, cur);
        cur = next;

        mem.read_obj(cur).unwrap()
    }

    #[test]
    fn smbios_oem_string_count_255_is_accepted() {
        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(SMBIOS_START), 4096)]).unwrap();
        let smbios = SmbiosConfig {
            oem_strings: (0..255).map(|_| "x".to_string()).collect(),
            ..Default::default()
        };

        setup_smbios(&mem, Some(&smbios)).unwrap();
        let oem = oem_record(&mem);
        assert_eq!(oem.r#type, OEM_STRINGS);
        assert_eq!(oem.count, 255);
    }

    #[test]
    fn smbios_oem_string_count_256_is_rejected() {
        let mem = GuestMemoryMmap::from_ranges(&[(GuestAddress(SMBIOS_START), 4096)]).unwrap();
        let smbios = SmbiosConfig {
            oem_strings: (0..256).map(|_| "x".to_string()).collect(),
            ..Default::default()
        };

        let err = setup_smbios(&mem, Some(&smbios)).unwrap_err();
        assert!(matches!(err, Error::TooManyOemStrings));
    }

'''
if test_anchor not in text:
    raise SystemExit("unit-test anchor missing")
text = text.replace(test_anchor, tests + test_anchor, 1)

path.write_text(text)
