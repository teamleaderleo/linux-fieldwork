#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/vm.rs")
text = path.read_text()
marker = "tdvf_missing_hob_panics_baseline"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = '''    #[cfg(feature = "tdx")]
    #[test]
    fn test_hob_memory_resources() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDX HOB unit-test anchor count")

probe = r'''    #[cfg(feature = "tdx")]
    fn current_tdvf_hob_offset(sections: &[arch::x86_64::tdx::TdvfSection]) -> u64 {
        let mut hob_offset = None;
        for section in sections {
            if matches!(section.r#type, arch::x86_64::tdx::TdvfSectionType::TdHob) {
                hob_offset = Some(section.address);
            }
        }
        hob_offset.unwrap()
    }

    #[cfg(feature = "tdx")]
    fn fixture_without_tdhob() -> Vec<arch::x86_64::tdx::TdvfSection> {
        vec![arch::x86_64::tdx::TdvfSection {
            r#type: arch::x86_64::tdx::TdvfSectionType::Bfv,
            ..Default::default()
        }]
    }

    #[cfg(feature = "tdx")]
    #[test]
    #[ignore]
    fn tdvf_missing_hob_panics_baseline() {
        let sections = fixture_without_tdhob();
        let result = std::panic::catch_unwind(|| current_tdvf_hob_offset(&sections));
        println!(
            "TDVF_HOB_BASELINE sections={} panicked={}",
            sections.len(),
            result.is_err()
        );
        assert!(result.is_err());
    }

    #[cfg(feature = "tdx")]
    #[test]
    fn tdvf_missing_hob_should_not_panic() {
        let sections = fixture_without_tdhob();
        let result = std::panic::catch_unwind(|| current_tdvf_hob_offset(&sections));
        println!(
            "TDVF_HOB_INVARIANT sections={} panicked={}",
            sections.len(),
            result.is_err()
        );
        assert!(result.is_ok(), "missing TdHob must not panic the VMM");
    }

    #[cfg(feature = "tdx")]
    #[test]
    fn tdvf_present_hob_control() {
        let sections = vec![
            arch::x86_64::tdx::TdvfSection {
                r#type: arch::x86_64::tdx::TdvfSectionType::Bfv,
                ..Default::default()
            },
            arch::x86_64::tdx::TdvfSection {
                address: 0x4000,
                r#type: arch::x86_64::tdx::TdvfSectionType::TdHob,
                ..Default::default()
            },
        ];
        let offset = current_tdvf_hob_offset(&sections);
        println!("TDVF_HOB_CONTROL offset=0x{offset:x}");
        assert_eq!(offset, 0x4000);
    }

'''

path.write_text(text.replace(anchor, probe + anchor, 1))
