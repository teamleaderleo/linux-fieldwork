from pathlib import Path
import sys

p = Path(sys.argv[1])
text = p.read_text()

old_worker = '''            receive_memory_ranges(guest_memory, &req, socket)?;\n            Response::ok().write_to(socket)?;\n'''
new_worker = '''            if !receive_memory_ranges_abortable(guest_memory, &req, socket, Some(kill_evt))? {\n                debug!("Got signal to tear down connection while receiving memory payload.");\n                return Ok(());\n            }\n            Response::ok().write_to(socket)?;\n'''
if text.count(old_worker) != 1:
    raise SystemExit(f'worker call anchor count={text.count(old_worker)}')
text = text.replace(old_worker, new_worker, 1)

old_sig = '''pub(crate) fn receive_memory_ranges(\n    guest_memory: &GuestMemoryAtomic<GuestMemoryMmap>,\n    req: &Request,\n    socket: &mut SocketStream,\n) -> Result<(), MigratableError> {\n    debug_assert_eq!(req.command(), Command::Memory);\n'''
new_sig = '''pub(crate) fn receive_memory_ranges(\n    guest_memory: &GuestMemoryAtomic<GuestMemoryMmap>,\n    req: &Request,\n    socket: &mut SocketStream,\n) -> Result<(), MigratableError> {\n    receive_memory_ranges_abortable(guest_memory, req, socket, None).map(|_| ())\n}\n\nfn receive_memory_ranges_abortable(\n    guest_memory: &GuestMemoryAtomic<GuestMemoryMmap>,\n    req: &Request,\n    socket: &mut SocketStream,\n    kill_evt: Option<&EventFd>,\n) -> Result<bool, MigratableError> {\n    debug_assert_eq!(req.command(), Command::Memory);\n'''
if text.count(old_sig) != 1:
    raise SystemExit(f'receive signature anchor count={text.count(old_sig)}')
text = text.replace(old_sig, new_sig, 1)

old_read = '''        loop {\n            let bytes_read = mem\n                .read_volatile_from(\n'''
new_read = '''        loop {\n            if let Some(kill_evt) = kill_evt {\n                if !wait_for_readable(socket, kill_evt)\n                    .context("Failed to poll memory payload fds")\n                    .map_err(MigratableError::MigrateReceive)?\n                {\n                    return Ok(false);\n                }\n            }\n\n            let bytes_read = mem\n                .read_volatile_from(\n'''
if text.count(old_read) != 1:
    raise SystemExit(f'payload read anchor count={text.count(old_read)}')
text = text.replace(old_read, new_read, 1)

# Replace only the terminal Ok(()) of receive_memory_ranges_abortable, using the exact tail.
old_tail = '''    Ok(())\n}\n\n#[cfg(test)]\nmod tests {\n'''
new_tail = '''    Ok(true)\n}\n\n#[cfg(test)]\nmod tests {\n'''
if text.count(old_tail) != 1:
    raise SystemExit(f'receive tail anchor count={text.count(old_tail)}')
text = text.replace(old_tail, new_tail, 1)

p.write_text(text)
