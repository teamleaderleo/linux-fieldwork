#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/migration/transport.rs")
text = path.read_text()
marker = "receive_memory_ranges_rejects_truncated_payload"
if marker in text:
    raise SystemExit(f"probe marker already present in {path}")

anchor = "#[cfg(test)]\nmod tests {"
if text.count(anchor) != 1:
    raise SystemExit(f"expected exactly one existing test module anchor in {path}")

probe = r'''#[cfg(test)]
mod truncated_payload_tests {
    use std::io::Write as _;
    use std::os::unix::net::UnixStream;

    use vm_migration::protocol::{MemoryRange, MemoryRangeTable, Request};

    use super::{
        GuestAddress, GuestMemoryAtomic, GuestMemoryMmap, MigratableError, SocketStream,
        receive_memory_ranges,
    };

    #[test]
    fn receive_memory_ranges_rejects_truncated_payload() {
        let memory = GuestMemoryAtomic::new(
            GuestMemoryMmap::from_ranges(&[(GuestAddress(0), 0x1000)]).unwrap(),
        );

        let mut ranges = MemoryRangeTable::default();
        ranges.push(MemoryRange {
            gpa: 0,
            length: 0x100,
        });
        let req = Request::memory(ranges.length());

        let (mut peer, local) = UnixStream::pair().unwrap();
        ranges.write_to(&mut peer).unwrap();
        peer.write_all(&[0x5a; 32]).unwrap();
        drop(peer);

        let mut socket = SocketStream::Unix(local);
        let err = receive_memory_ranges(&memory, &req, &mut socket).unwrap_err();

        assert!(matches!(
            err,
            MigratableError::MigrateSocket(_) | MigratableError::MigrateReceive(_)
        ));
    }
}

'''

path.write_text(text.replace(anchor, probe + anchor, 1))