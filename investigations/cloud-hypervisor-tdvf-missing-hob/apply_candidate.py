#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/vm.rs")
text = path.read_text()
marker = "TDX firmware missing TD HOB section"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

old_error = '''    #[cfg(feature = "tdx")]
    #[error("TDX firmware missing")]
    TdxFirmwareMissing,
'''
new_error = old_error + '''
    #[cfg(feature = "tdx")]
    #[error("TDX firmware missing TD HOB section")]
    TdxHobMissing,
'''
if text.count(old_error) != 1:
    raise SystemExit("unexpected TdxFirmwareMissing error anchor count")
text = text.replace(old_error, new_error, 1)

old_fn = '''    #[cfg(feature = "tdx")]
    fn populate_tdx_sections(
'''
new_fn = '''    #[cfg(feature = "tdx")]
    fn required_tdx_hob_offset(hob_offset: Option<u64>) -> Result<u64> {
        hob_offset.ok_or(Error::TdxHobMissing)
    }

    #[cfg(feature = "tdx")]
    fn populate_tdx_sections(
'''
if text.count(old_fn) != 1:
    raise SystemExit("unexpected populate_tdx_sections anchor count")
text = text.replace(old_fn, new_fn, 1)

old_boundary = '''        // Generate HOB
        let mut hob = TdHob::start(hob_offset.unwrap());
'''
new_boundary = '''        // Generate HOB
        let hob_offset = Self::required_tdx_hob_offset(hob_offset)?;
        let mut hob = TdHob::start(hob_offset);
'''
if text.count(old_boundary) != 1:
    raise SystemExit("unexpected TD HOB unwrap boundary count")
text = text.replace(old_boundary, new_boundary, 1)

anchor = '''    #[cfg(feature = "tdx")]
    #[test]
    fn test_hob_memory_resources() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDX HOB unit-test anchor count")

test = r'''    #[cfg(feature = "tdx")]
    #[test]
    fn required_tdx_hob_offset_is_typed() {
        let err = Vm::required_tdx_hob_offset(None).unwrap_err();
        println!("TDVF_HOB_CANDIDATE missing_result={err:?}");
        assert!(matches!(err, Error::TdxHobMissing));

        let offset = Vm::required_tdx_hob_offset(Some(0x4000)).unwrap();
        println!("TDVF_HOB_CANDIDATE control_offset=0x{offset:x}");
        assert_eq!(offset, 0x4000);
    }

'''
text = text.replace(anchor, test + anchor, 1)

path.write_text(text)
