#!/usr/bin/env python3
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text()
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one match, found {text.count(old)} for {old[:80]!r}")
    p.write_text(text.replace(old, new, 1))


worker = Path("vmm/src/migration/worker.rs")
worker_text = worker.read_text()
if "pub(crate) enum MigrationCommitState" in worker_text:
    raise SystemExit("commit-state candidate already present")

worker_anchor = '''#[derive(Clone, Debug)]
pub struct MigrationSeccompFilters {
'''
worker_enum = '''#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum MigrationCommitState {
    /// Complete has not been successfully written; source rollback is safe.
    RollbackSafe,
    /// Complete was written, but its acknowledgement was not received.
    CommitUnknown,
    /// The receiver acknowledged Complete.
    Committed,
}

impl MigrationCommitState {
    pub(crate) fn rollback_safe(self) -> bool {
        self == Self::RollbackSafe
    }
}

#[derive(Clone, Debug)]
pub struct MigrationSeccompFilters {
'''
if worker_text.count(worker_anchor) != 1:
    raise SystemExit("worker enum anchor mismatch")
worker_text = worker_text.replace(worker_anchor, worker_enum, 1)

old_run = '''        // We can't propagate errors early because of the complex return type,
        // therefore we chain the results together.
        let migration_result = seccomp_res
            .and_then(|()| {
                event!("vm", "migration-started");
                Vmm::send_migration(
                    &mut vm,
                    #[cfg(all(feature = "kvm", target_arch = "x86_64"))]
                    self.hypervisor.as_ref(),
                    &self.config,
                    self.initial_vm_state,
                    &self.seccomp_filters,
                )
            })
'''
new_run = '''        let mut migration_commit_state = MigrationCommitState::RollbackSafe;

        // We can't propagate errors early because of the complex return type,
        // therefore we chain the results together.
        let migration_result = seccomp_res
            .and_then(|()| {
                event!("vm", "migration-started");
                Vmm::send_migration(
                    &mut vm,
                    #[cfg(all(feature = "kvm", target_arch = "x86_64"))]
                    self.hypervisor.as_ref(),
                    &self.config,
                    self.initial_vm_state,
                    &self.seccomp_filters,
                    &mut migration_commit_state,
                )
            })
'''
if worker_text.count(old_run) != 1:
    raise SystemExit("worker run block mismatch")
worker_text = worker_text.replace(old_run, new_run, 1)

old_result = '''        MigrationWorkerResult {
            vm,
            migration_result,
            initial_vm_state: self.initial_vm_state,
            preserve_source: self.config.preserve_source,
        }
'''
new_result = '''        MigrationWorkerResult {
            vm,
            migration_result,
            migration_commit_state,
            initial_vm_state: self.initial_vm_state,
            preserve_source: self.config.preserve_source,
        }
'''
if worker_text.count(old_result) != 1:
    raise SystemExit("worker result construction mismatch")
worker_text = worker_text.replace(old_result, new_result, 1)

old_struct = '''    /// The result of [`Vmm::send_migration`].
    pub migration_result: Result<(), MigratableError>,
    pub initial_vm_state: VmState,
'''
new_struct = '''    /// The result of [`Vmm::send_migration`].
    pub migration_result: Result<(), MigratableError>,
    /// Whether the source still knows it can roll back without racing a committed receiver.
    pub(crate) migration_commit_state: MigrationCommitState,
    pub initial_vm_state: VmState,
'''
if worker_text.count(old_struct) != 1:
    raise SystemExit("worker result struct mismatch")
worker_text = worker_text.replace(old_struct, new_struct, 1)
worker.write_text(worker_text)

lib = Path("vmm/src/lib.rs")
lib_text = lib.read_text()

old_import = '''use crate::migration::worker::{
    MigrationSeccompFilters, MigrationWorker, MigrationWorkerHandle, MigrationWorkerResult,
};
'''
new_import = '''use crate::migration::worker::{
    MigrationCommitState, MigrationSeccompFilters, MigrationWorker, MigrationWorkerHandle,
    MigrationWorkerResult,
};
'''
if lib_text.count(old_import) != 1:
    raise SystemExit("lib worker import mismatch")
lib_text = lib_text.replace(old_import, new_import, 1)

sig_old = '''        send_data_migration: &VmSendMigrationData,
        initial_vm_state: VmState,
        seccomp_filters: &MigrationSeccompFilters,
    ) -> result::Result<(), MigratableError> {
'''
sig_new = '''        send_data_migration: &VmSendMigrationData,
        initial_vm_state: VmState,
        seccomp_filters: &MigrationSeccompFilters,
        migration_commit_state: &mut MigrationCommitState,
    ) -> result::Result<(), MigratableError> {
'''
if lib_text.count(sig_old) != 1:
    raise SystemExit("send_migration signature mismatch")
lib_text = lib_text.replace(sig_old, sig_new, 1)

helper_anchor = '''    /// Performs a migration.
    ///
    /// Runs after-migration cleanup only on success. Callers must handle failed
    /// migrations.
    fn send_migration(
'''
helper = '''    fn send_complete_request(
        socket: &mut SocketStream,
        request: Request,
        migration_commit_state: &mut MigrationCommitState,
    ) -> result::Result<Duration, MigratableError> {
        let begin = Instant::now();
        request.write_to(socket)?;
        *migration_commit_state = MigrationCommitState::CommitUnknown;
        transport::expect_ok_response(
            socket,
            MigratableError::MigrateSend(anyhow!("Error completing migration")),
        )?;
        *migration_commit_state = MigrationCommitState::Committed;
        Ok(begin.elapsed())
    }

    /// Performs a migration.
    ///
    /// Runs after-migration cleanup only on success. Callers must handle failed
    /// migrations.
    fn send_migration(
'''
if lib_text.count(helper_anchor) != 1:
    raise SystemExit("send_complete helper anchor mismatch")
lib_text = lib_text.replace(helper_anchor, helper, 1)

complete_old = '''        let (_, complete_duration) = measure_ok(|| {
            transport::send_request_expect_ok(
                &mut socket,
                complete_req,
                MigratableError::MigrateSend(anyhow!("Error completing migration")),
            )
        })?;
'''
complete_new = '''        let complete_duration = Self::send_complete_request(
            &mut socket,
            complete_req,
            migration_commit_state,
        )?;
'''
if lib_text.count(complete_old) != 1:
    raise SystemExit("complete request block mismatch")
lib_text = lib_text.replace(complete_old, complete_new, 1)

result_old = '''        let MigrationWorkerResult {
            vm,
            migration_result: migration_res,
            initial_vm_state,
            preserve_source,
        } = migration_worker_handle.join();
'''
result_new = '''        let MigrationWorkerResult {
            vm,
            migration_result: migration_res,
            migration_commit_state,
            initial_vm_state,
            preserve_source,
        } = migration_worker_handle.join();
'''
if lib_text.count(result_old) != 1:
    raise SystemExit("check_migration result destructure mismatch")
lib_text = lib_text.replace(result_old, result_new, 1)

error_old = '''            Err(e) => {
                error!(
                    "Migration failed: {}",
                    util::flatten_error_chain_to_string(&e)
                );
                try_resume_vm_after_failed_migration(vm);
            }
'''
error_new = '''            Err(e) if migration_commit_state.rollback_safe() => {
                error!(
                    "Migration failed before the remote commit boundary: {}",
                    util::flatten_error_chain_to_string(&e)
                );
                try_resume_vm_after_failed_migration(vm);
            }
            Err(e) => {
                error!(
                    "Migration failed after Complete may have reached the receiver ({migration_commit_state:?}); source will not be resumed automatically: {}",
                    util::flatten_error_chain_to_string(&e)
                );
                let mut vm = vm;
                if preserve_source {
                    let _ = vm.stop_dirty_log().inspect_err(|stop_err| {
                        warn!("Failed stopping dirty log on preserved source after commit-risk migration failure: {stop_err}");
                    });
                    self.vm = VmOwnership::Owned(vm);
                } else {
                    self.vm = VmOwnership::None;
                    if let Err(shutdown_err) = vm.shutdown() {
                        error!("Failed shutting down source after commit-risk migration failure: {shutdown_err}");
                    }
                    if let Err(exit_err) = self.exit_evt.write(1) {
                        error!("Failed exiting VMM after commit-risk migration failure: {exit_err}");
                    }
                }
            }
'''
if lib_text.count(error_old) != 1:
    raise SystemExit("check_migration error arm mismatch")
lib_text = lib_text.replace(error_old, error_new, 1)

# Add focused protocol-state tests to the existing unit test module.
test_anchor = '''    fn create_dummy_vmm() -> Vmm {
'''
tests = r'''    #[test]
    fn complete_ack_loss_is_commit_unknown() {
        let (source, receiver) = UnixStream::pair().unwrap();
        let mut source = SocketStream::Unix(source);
        let mut receiver = SocketStream::Unix(receiver);
        let receiver_thread = thread::spawn(move || {
            let request = Request::read_from(&mut receiver).unwrap();
            assert_eq!(request.command(), Command::Complete);
            drop(receiver);
        });
        let mut state = MigrationCommitState::RollbackSafe;
        Vmm::send_complete_request(&mut source, Request::complete(), &mut state).unwrap_err();
        receiver_thread.join().unwrap();
        assert_eq!(state, MigrationCommitState::CommitUnknown);
        assert!(!state.rollback_safe());
    }

    #[test]
    fn complete_ok_is_committed() {
        let (source, receiver) = UnixStream::pair().unwrap();
        let mut source = SocketStream::Unix(source);
        let mut receiver = SocketStream::Unix(receiver);
        let receiver_thread = thread::spawn(move || {
            let request = Request::read_from(&mut receiver).unwrap();
            assert_eq!(request.command(), Command::Complete);
            Response::ok().write_to(&mut receiver).unwrap();
        });
        let mut state = MigrationCommitState::RollbackSafe;
        Vmm::send_complete_request(&mut source, Request::complete(), &mut state).unwrap();
        receiver_thread.join().unwrap();
        assert_eq!(state, MigrationCommitState::Committed);
        assert!(!state.rollback_safe());
    }

    #[test]
    fn complete_write_failure_remains_rollback_safe() {
        let (source, receiver) = UnixStream::pair().unwrap();
        drop(receiver);
        let mut source = SocketStream::Unix(source);
        let mut state = MigrationCommitState::RollbackSafe;
        Vmm::send_complete_request(&mut source, Request::complete(), &mut state).unwrap_err();
        assert_eq!(state, MigrationCommitState::RollbackSafe);
        assert!(state.rollback_safe());
    }

    fn create_dummy_vmm() -> Vmm {
'''
if lib_text.count(test_anchor) != 1:
    raise SystemExit("unit test anchor mismatch")
lib_text = lib_text.replace(test_anchor, tests, 1)

# Unit tests need UnixStream in scope.
unit_import_old = '''mod unit_tests {
    use std::path::PathBuf;
'''
unit_import_new = '''mod unit_tests {
    use std::os::unix::net::UnixStream;
    use std::path::PathBuf;
'''
if lib_text.count(unit_import_old) != 1:
    raise SystemExit("unit test import anchor mismatch")
lib_text = lib_text.replace(unit_import_old, unit_import_new, 1)

lib.write_text(lib_text)
