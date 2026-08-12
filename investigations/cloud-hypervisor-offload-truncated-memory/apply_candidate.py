#!/usr/bin/env python3
from pathlib import Path

path = Path("offload_daemon/src/main.rs")
text = path.read_text()
if "SnapshotMemoryTooShort" in text:
    raise SystemExit("candidate already applied")

old = '''    #[error("Reading a snapshot artifact")]\n    ReadFile(#[source] io::Error),\n'''
new = '''    #[error("Reading a snapshot artifact")]\n    ReadFile(#[source] io::Error),\n    #[error("Snapshot memory artifact {path:?} is too short: {actual} bytes, need at least {required}")]\n    SnapshotMemoryTooShort {\n        path: PathBuf,\n        actual: u64,\n        required: u64,\n    },\n'''
if text.count(old) != 1:
    raise SystemExit("error anchor missing")
text = text.replace(old, new, 1)

old = '''fn create_memfd_with_contents(\n    src_path: &Path,\n    file_offset: u64,\n    size: u64,\n    name: &str,\n) -> Result<File> {\n    // Size the memfd to cover the range CH maps at `file_offset`.\n    let memfd = create_empty_memfd(file_offset + size, name)?;\n    let src = File::open(src_path).map_err(Error::ReadFile)?;\n    // Copy sparsely so the memfd keeps the snapshot's holes.\n    copy_region(&src, 0, &memfd, file_offset, size).map_err(Error::CopyMemory)?;\n    Ok(memfd)\n}\n'''
new = '''fn open_snapshot_memory(path: &Path, required: u64) -> Result<File> {\n    let file = File::open(path).map_err(Error::ReadFile)?;\n    let actual = file.metadata().map_err(Error::ReadFile)?.len();\n    if actual < required {\n        return Err(Error::SnapshotMemoryTooShort {\n            path: path.to_path_buf(),\n            actual,\n            required,\n        });\n    }\n    Ok(file)\n}\n\nfn create_memfd_with_contents(\n    src_path: &Path,\n    file_offset: u64,\n    size: u64,\n    name: &str,\n) -> Result<File> {\n    // Size the memfd to cover the range CH maps at `file_offset`.\n    let memfd = create_empty_memfd(file_offset + size, name)?;\n    let src = open_snapshot_memory(src_path, size)?;\n    // Copy sparsely so the memfd keeps the snapshot's holes.\n    copy_region(&src, 0, &memfd, file_offset, size).map_err(Error::CopyMemory)?;\n    Ok(memfd)\n}\n'''
if text.count(old) != 1:
    raise SystemExit("create_memfd anchor missing")
text = text.replace(old, new, 1)

old = '''        let disk = File::open(disk_path).map_err(Error::ReadFile)?;\n        Ok(Self { region, disk })\n'''
new = '''        let disk = open_snapshot_memory(disk_path, size)?;\n        Ok(Self { region, disk })\n'''
if text.count(old) != 1:
    raise SystemExit("ondemand disk anchor missing")
text = text.replace(old, new, 1)

old = r'''    #[test]
    fn truncated_snapshot_memory_is_silently_zero_filled() {
        use std::env::temp_dir;
        use std::fs::OpenOptions;
        use std::os::unix::fs::FileExt;
        use std::process::id;
        use std::time::{SystemTime, UNIX_EPOCH};

        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = temp_dir().join(format!("ch-offload-short-memory-{}-{nonce}", id()));
        let src = OpenOptions::new()
            .create_new(true)
            .read(true)
            .write(true)
            .open(&path)
            .unwrap();
        src.set_len(4096).unwrap();
        src.write_all_at(&vec![0xa5; 4096], 0).unwrap();
        drop(src);

        let memfd = create_memfd_with_contents(&path, 0, 8192, "offload-short-probe").unwrap();
        let mut head = [0u8; 16];
        let mut tail = [0xffu8; 16];
        memfd.read_exact_at(&mut head, 0).unwrap();
        memfd.read_exact_at(&mut tail, 4096).unwrap();
        eprintln!(
            "OFFLOAD_SHORT_BASELINE source_len=4096 configured=8192 head={head:02x?} tail={tail:02x?}"
        );
        assert_eq!(head, [0xa5; 16]);
        assert_eq!(tail, [0; 16]);

        std::fs::remove_file(path).unwrap();
    }
'''
new = r'''    #[test]
    fn truncated_snapshot_memory_is_rejected() {
        use std::env::temp_dir;
        use std::fs::OpenOptions;
        use std::process::id;
        use std::time::{SystemTime, UNIX_EPOCH};

        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = temp_dir().join(format!("ch-offload-short-memory-{}-{nonce}", id()));
        let src = OpenOptions::new()
            .create_new(true)
            .read(true)
            .write(true)
            .open(&path)
            .unwrap();
        src.set_len(4096).unwrap();
        drop(src);

        let err = create_memfd_with_contents(&path, 0, 8192, "offload-short-probe").unwrap_err();
        eprintln!("OFFLOAD_SHORT_CANDIDATE {err}");
        assert!(matches!(
            err,
            Error::SnapshotMemoryTooShort {
                actual: 4096,
                required: 8192,
                ..
            }
        ));

        std::fs::remove_file(path).unwrap();
    }

    #[test]
    fn full_length_sparse_snapshot_memory_is_accepted() {
        use std::env::temp_dir;
        use std::fs::OpenOptions;
        use std::process::id;
        use std::time::{SystemTime, UNIX_EPOCH};

        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = temp_dir().join(format!("ch-offload-sparse-memory-{}-{nonce}", id()));
        let src = OpenOptions::new()
            .create_new(true)
            .read(true)
            .write(true)
            .open(&path)
            .unwrap();
        src.set_len(8192).unwrap();
        drop(src);

        create_memfd_with_contents(&path, 0, 8192, "offload-sparse-control").unwrap();
        std::fs::remove_file(path).unwrap();
    }
'''
if text.count(old) != 1:
    raise SystemExit("probe test anchor missing")
text = text.replace(old, new, 1)

path.write_text(text)
