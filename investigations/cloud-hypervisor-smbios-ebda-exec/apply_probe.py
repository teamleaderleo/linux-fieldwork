#!/usr/bin/env python3
from pathlib import Path

path = Path("arch/src/x86_64/smbios.rs")
text = path.read_text()
marker = "smbios_large_payload_overwrites_high_ram_baseline"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = "#[cfg(test)]\nmod unit_tests {"
if text.count(anchor) != 1:
    raise SystemExit(f"expected exactly one SMBIOS unit-test anchor in {path}")

probe = r'''#[cfg(test)]
mod ebda_boundary_tests {
    use vm_memory::{Address, Bytes, GuestAddress};

    use crate::GuestMemoryMmap;
    use crate::layout::{HIGH_RAM_START, SMBIOS_START};

    use super::{SmbiosConfig, SmbiosSystem, setup_smbios};

    const SENTINEL_LEN: usize = 64;
    const HIGH_RAM_EXTRA: usize = 0x20_000;

    fn test_memory() -> GuestMemoryMmap {
        let ebda_tail = HIGH_RAM_START.raw_value() - SMBIOS_START;
        GuestMemoryMmap::from_ranges(&[(
            GuestAddress(SMBIOS_START),
            ebda_tail as usize + HIGH_RAM_EXTRA,
        )])
        .unwrap()
    }

    fn sentinel(mem: &GuestMemoryMmap) -> [u8; SENTINEL_LEN] {
        let mut bytes = [0u8; SENTINEL_LEN];
        mem.read_slice(&mut bytes, HIGH_RAM_START).unwrap();
        bytes
    }

    fn long_smbios() -> SmbiosConfig {
        SmbiosConfig {
            system: Some(SmbiosSystem {
                manufacturer: Some("A".repeat(70 * 1024)),
                ..Default::default()
            }),
            ..Default::default()
        }
    }

    #[test]
    #[ignore]
    fn smbios_large_payload_overwrites_high_ram_baseline() {
        let mem = test_memory();
        mem.write_slice(&[0xFE; SENTINEL_LEN], HIGH_RAM_START)
            .unwrap();

        let encoded_size = setup_smbios(&mem, Some(&long_smbios())).unwrap();
        let observed = sentinel(&mem);
        let ebda_tail = HIGH_RAM_START.raw_value() - SMBIOS_START;

        println!(
            "SMBIOS_EBDA_BASELINE encoded_size={encoded_size} ebda_tail={ebda_tail} high_ram_prefix={:02x?}",
            &observed[..16]
        );
        assert!(encoded_size > ebda_tail);
        assert_ne!(observed, [0xFE; SENTINEL_LEN]);
    }

    #[test]
    fn smbios_large_payload_keeps_high_ram_unchanged() {
        let mem = test_memory();
        mem.write_slice(&[0xFE; SENTINEL_LEN], HIGH_RAM_START)
            .unwrap();

        let result = setup_smbios(&mem, Some(&long_smbios()));
        let observed = sentinel(&mem);
        println!(
            "SMBIOS_EBDA_INVARIANT result={result:?} high_ram_prefix={:02x?}",
            &observed[..16]
        );

        assert!(result.is_err(), "oversized SMBIOS payload must be rejected");
        assert_eq!(observed, [0xFE; SENTINEL_LEN]);
    }

    #[test]
    fn smbios_small_payload_stays_below_high_ram() {
        let mem = test_memory();
        mem.write_slice(&[0xFE; SENTINEL_LEN], HIGH_RAM_START)
            .unwrap();
        let smbios = SmbiosConfig {
            system: Some(SmbiosSystem {
                manufacturer: Some("Acme".to_string()),
                ..Default::default()
            }),
            ..Default::default()
        };

        let encoded_size = setup_smbios(&mem, Some(&smbios)).unwrap();
        let observed = sentinel(&mem);
        let ebda_tail = HIGH_RAM_START.raw_value() - SMBIOS_START;

        println!(
            "SMBIOS_EBDA_CONTROL encoded_size={encoded_size} ebda_tail={ebda_tail}"
        );
        assert!(encoded_size < ebda_tail);
        assert_eq!(observed, [0xFE; SENTINEL_LEN]);
    }
}

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
