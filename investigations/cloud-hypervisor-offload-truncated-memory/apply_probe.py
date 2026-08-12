#!/usr/bin/env python3
from pathlib import Path

path = Path("offload_daemon/src/main.rs")
text = path.read_text()
marker = "truncated_snapshot_memory_is_silently_zero_filled"
if marker in text:
    raise SystemExit("probe already applied")

anchor = "    #[test]\n    fn test_memory_slot_filename() {\n"
probe = r'''    #[test]
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
if text.count(anchor) != 1:
    raise SystemExit("test anchor missing")
path.write_text(text.replace(anchor, probe + anchor, 1))
