#!/usr/bin/env python3
from pathlib import Path

path = Path("vmm/src/migration/transport.rs")
text = path.read_text()
anchor = "#[cfg(test)]\nmod tests {"
if text.count(anchor) != 1:
    raise SystemExit("unexpected transport test module anchor count")
if "complete_request_reaches_receiver_before_ack_loss_error" in text:
    raise SystemExit("baseline probe already present")

probe = r'''#[cfg(test)]
mod commit_point_baseline_tests {
    use std::os::unix::net::UnixStream;
    use std::thread;

    use anyhow::anyhow;
    use vm_migration::MigratableError;
    use vm_migration::protocol::{Command, Request};

    use super::{SocketStream, send_request_expect_ok};

    #[test]
    fn complete_request_reaches_receiver_before_ack_loss_error() {
        let (source, receiver) = UnixStream::pair().unwrap();
        let mut source = SocketStream::Unix(source);
        let mut receiver = SocketStream::Unix(receiver);

        let receiver_thread = thread::spawn(move || {
            let request = Request::read_from(&mut receiver).unwrap();
            assert_eq!(request.command(), Command::Complete);
            // Simulate the receiver committing the request and then losing the ACK path.
            drop(receiver);
        });

        let result = send_request_expect_ok(
            &mut source,
            Request::complete(),
            MigratableError::MigrateSend(anyhow!("Error completing migration")),
        );
        receiver_thread.join().unwrap();
        result.unwrap_err();
    }
}

'''
path.write_text(text.replace(anchor, probe + anchor, 1))
