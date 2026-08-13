#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/vm.rs")
text = path.read_text()
marker = "LoadPayloadHeader"
if marker in text:
    raise SystemExit(f"candidate marker already present in {path}")

old_error = '''    #[cfg(feature = "tdx")]
    #[error("Error performing I/O on the TDX payload file")]
    LoadPayload(#[source] io::Error),
'''
new_error = '''    #[cfg(feature = "tdx")]
    #[error("Error performing I/O on the TDX payload file")]
    LoadPayload(#[source] io::Error),

    #[cfg(feature = "tdx")]
    #[error("Error reading the TDX payload setup header")]
    LoadPayloadHeader(#[source] vm_memory::VolatileMemoryError),
'''
if text.count(old_error) != 1:
    raise SystemExit("unexpected LoadPayload error anchor count")
text = text.replace(old_error, new_error, 1)

old_fn = '''    #[cfg(feature = "tdx")]
    fn populate_tdx_sections(
'''
new_fn = '''    #[cfg(feature = "tdx")]
    fn read_tdx_payload_header(payload_file: &mut File) -> Result<bootparam::setup_header> {
        payload_file
            .seek(SeekFrom::Start(0x1f1))
            .map_err(Error::LoadPayload)?;

        let mut payload_header = bootparam::setup_header::default();
        payload_file
            .read_volatile(&mut payload_header.as_bytes())
            .map_err(Error::LoadPayloadHeader)?;
        Ok(payload_header)
    }

    #[cfg(feature = "tdx")]
    fn populate_tdx_sections(
'''
if text.count(old_fn) != 1:
    raise SystemExit("unexpected populate_tdx_sections anchor count")
text = text.replace(old_fn, new_fn, 1)

old_read = '''                        payload_file
                            .seek(SeekFrom::Start(0x1f1))
                            .map_err(Error::LoadPayload)?;

                        let mut payload_header = bootparam::setup_header::default();
                        payload_file
                            .read_volatile(&mut payload_header.as_bytes())
                            .unwrap();
'''
new_read = '''                        let payload_header = Self::read_tdx_payload_header(payload_file)?;
'''
if text.count(old_read) != 1:
    raise SystemExit("unexpected TDX Payload header read boundary count")
text = text.replace(old_read, new_read, 1)

anchor = '''    #[cfg(feature = "tdx")]
    #[test]
    fn test_hob_memory_resources() {
'''
if text.count(anchor) != 1:
    raise SystemExit("unexpected TDX unit-test anchor count")

test = r'''    #[cfg(feature = "tdx")]
    #[test]
    fn tdx_payload_header_read_propagates_error() {
        use std::env::temp_dir;
        use std::fs::{File, OpenOptions, create_dir, remove_dir, remove_file, write};
        use std::mem::size_of;
        use std::process::id;

        let dir = temp_dir().join(format!("cloud-hypervisor-tdx-payload-header-candidate-{}", id()));
        create_dir(&dir).unwrap();
        let mut file = File::open(&dir).unwrap();
        let err = Vm::read_tdx_payload_header(&mut file).unwrap_err();
        remove_dir(dir).unwrap();
        println!("TDX_PAYLOAD_HEADER_CANDIDATE directory_result={err:?}");
        assert!(matches!(err, Error::LoadPayloadHeader(_)));

        let len = 0x1f1 + size_of::<bootparam::setup_header>() + 16;
        let path = temp_dir().join(format!("cloud-hypervisor-tdx-payload-header-control-{}.bin", id()));
        write(&path, vec![0u8; len]).unwrap();
        let mut file = OpenOptions::new().read(true).open(&path).unwrap();
        remove_file(path).unwrap();
        Vm::read_tdx_payload_header(&mut file).unwrap();
        println!("TDX_PAYLOAD_HEADER_CANDIDATE regular_file_read=ok");
    }

'''

path.write_text(text.replace(anchor, test + anchor, 1))
