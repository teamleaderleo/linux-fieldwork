#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/vm.rs")
text = path.read_text()
marker = "InvalidPayloadSetupSize"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

old_error = '''    #[cfg(feature = "tdx")]
    #[error("Invalid TDX payload type")]
    InvalidPayloadType,
'''
new_error = '''    #[cfg(feature = "tdx")]
    #[error("Invalid TDX payload type")]
    InvalidPayloadType,

    #[cfg(feature = "tdx")]
    #[error(
        "TDX bzImage payload size 0x{payload_size:x} is smaller than setup area 0x{setup_size:x}"
    )]
    InvalidPayloadSetupSize { payload_size: u64, setup_size: u64 },
'''
if text.count(old_error) != 1:
    raise SystemExit("unexpected InvalidPayloadType error anchor count")
text = text.replace(old_error, new_error, 1)

old_fn = '''    #[cfg(feature = "tdx")]
    fn populate_tdx_sections(
'''
new_fn = '''    #[cfg(feature = "tdx")]
    fn validate_tdx_payload_setup_size(
        payload_size: u64,
        payload_header: &bootparam::setup_header,
    ) -> Result<()> {
        let setup_sects = payload_header.setup_sects;
        let setup_sectors = if setup_sects == 0 {
            4
        } else {
            u64::from(setup_sects)
        };
        let setup_size = (setup_sectors + 1) * 512;
        if payload_size < setup_size {
            return Err(Error::InvalidPayloadSetupSize {
                payload_size,
                setup_size,
            });
        }
        Ok(())
    }

    #[cfg(feature = "tdx")]
    fn populate_tdx_sections(
'''
if text.count(old_fn) != 1:
    raise SystemExit("unexpected populate_tdx_sections anchor count")
text = text.replace(old_fn, new_fn, 1)

old_checks = '''                        if (payload_header.version < 0x0200)
                            || ((payload_header.loadflags & 0x1) == 0x0)
                        {
                            return Err(Error::InvalidPayloadType);
                        }

                        payload_file.rewind().map_err(Error::LoadPayload)?;
'''
new_checks = '''                        if (payload_header.version < 0x0200)
                            || ((payload_header.loadflags & 0x1) == 0x0)
                        {
                            return Err(Error::InvalidPayloadType);
                        }

                        Self::validate_tdx_payload_setup_size(payload_size, &payload_header)?;

                        payload_file.rewind().map_err(Error::LoadPayload)?;
'''
if text.count(old_checks) != 1:
    raise SystemExit("unexpected TDX Payload header validation anchor count")
text = text.replace(old_checks, new_checks, 1)

anchor = '''    #[cfg(feature = "tdx")]
    #[test]
    fn test_hob_memory_resources() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDX unit-test anchor count")

test = r'''    #[cfg(feature = "tdx")]
    #[test]
    fn tdx_payload_setup_size_validation() {
        let mut header = bootparam::setup_header::default();
        header.setup_sects = 0;
        let err = Vm::validate_tdx_payload_setup_size(0x212, &header).unwrap_err();
        println!("TDX_PAYLOAD_SETUP_CANDIDATE truncated_result={err:?}");
        assert!(matches!(
            err,
            Error::InvalidPayloadSetupSize {
                payload_size: 0x212,
                setup_size: 0xa00,
            }
        ));

        Vm::validate_tdx_payload_setup_size(0xa00, &header).unwrap();
        println!("TDX_PAYLOAD_SETUP_CANDIDATE default_setup_control=ok");

        header.setup_sects = 1;
        Vm::validate_tdx_payload_setup_size(0x400, &header).unwrap();
        println!("TDX_PAYLOAD_SETUP_CANDIDATE explicit_setup_control=ok");
    }

'''

path.write_text(text.replace(anchor, test + anchor, 1))
