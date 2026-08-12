#!/usr/bin/env python3
from pathlib import Path

path = Path("block/src/formats/qcow/metadata.rs")
text = path.read_text()
marker = "failed_metadata_sync_keeps_dirty_bit_set"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

end = text.rfind("\n}")
if end == -1:
    raise SystemExit(f"could not find final metadata unit-test module close in {path}")

probe = r'''

    fn shutdown_probe_raw_dirty_bit(file: &std::fs::File) -> bool {
        use std::os::unix::fs::FileExt;

        let mut buf = [0u8; 8];
        file.read_exact_at(
            &mut buf,
            super::super::header::V2_BARE_HEADER_SIZE as u64,
        )
        .unwrap();
        u64::from_be_bytes(buf) & super::super::header::IncompatFeatures::DIRTY.bits() != 0
    }

    #[test]
    fn failed_metadata_sync_keeps_dirty_bit_set() {
        let cluster_size: u64 = 1 << 16;
        let temp = super::super::QcowTempDisk::new(4 * cluster_size, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let inspect = temp.as_file().try_clone().unwrap();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (mut inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert!(shutdown_probe_raw_dirty_bit(&inspect));

        let invalid_l2 = inner
            .refcounts
            .max_valid_cluster_offset()
            .checked_add(cluster_size)
            .unwrap();
        inner.l1_table[0] = invalid_l2;
        let sync_err = inner
            .sync_caches()
            .expect_err("out-of-horizon L1 target must make metadata synchronization fail");
        eprintln!(
            "QCOW_INTEGRATION_SYNC_FAIL sync_error kind={:?} raw={:?} dirty_before_drop={}",
            sync_err.kind(),
            sync_err.raw_os_error(),
            shutdown_probe_raw_dirty_bit(&inspect)
        );
        assert!(shutdown_probe_raw_dirty_bit(&inspect));

        drop(super::QcowMetadata::new(inner));
        let dirty_after_failed_drop = shutdown_probe_raw_dirty_bit(&inspect);
        eprintln!("QCOW_INTEGRATION_SYNC_FAIL post_failed_drop dirty={dirty_after_failed_drop}");
        assert!(dirty_after_failed_drop);

        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (reopened, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert!(shutdown_probe_raw_dirty_bit(&inspect));
        drop(super::QcowMetadata::new(reopened));
        let dirty_after_recovery_close = shutdown_probe_raw_dirty_bit(&inspect);
        eprintln!("QCOW_INTEGRATION_SYNC_FAIL recovery_close dirty={dirty_after_recovery_close}");
        assert!(!dirty_after_recovery_close);
    }

    #[test]
    fn successful_metadata_sync_clears_dirty_bit() {
        let cluster_size: u64 = 1 << 16;
        let temp = super::super::QcowTempDisk::new(4 * cluster_size, None, false, true, false)
            .unwrap()
            .into_tempfile();
        let inspect = temp.as_file().try_clone().unwrap();
        let raw = crate::AlignedFile::new(temp.as_file().try_clone().unwrap(), false);
        let (inner, _backing, _sparse) =
            super::super::parser::parse_qcow(raw, 0, true).unwrap();
        assert!(shutdown_probe_raw_dirty_bit(&inspect));

        drop(super::QcowMetadata::new(inner));
        let dirty_after_drop = shutdown_probe_raw_dirty_bit(&inspect);
        eprintln!("QCOW_INTEGRATION_CLEAN_CLOSE post_drop dirty={dirty_after_drop}");
        assert!(!dirty_after_drop);
    }
'''

path.write_text(text[:end] + probe + text[end:])
