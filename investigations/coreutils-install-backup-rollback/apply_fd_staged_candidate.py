#!/usr/bin/env python3
"""Apply the race-safe backup rollback model to one exact fd-bound source tree.

This is execution-carrier machinery. Every replacement is exact and single-site so
source drift fails before Rust compilation. The transformed source must not be
promoted by this script or its workflow.
"""

from __future__ import annotations

from pathlib import Path
import sys


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one replacement site, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_fd_staged_candidate.py COREUTILS_ROOT")

    root = Path(sys.argv[1]).resolve()
    install_toml = root / "src/uu/install/Cargo.toml"
    install_rs = root / "src/uu/install/src/install.rs"
    en_us = root / "src/uu/install/locales/en-US.ftl"
    fr_fr = root / "src/uu/install/locales/fr-FR.ftl"
    tests = root / "tests/by-util/test_install.rs"

    replace_once(
        install_toml,
        "fluent = { workspace = true }\n",
        "fluent = { workspace = true }\n"
        "tempfile = { workspace = true }\n",
    )

    replace_once(
        install_rs,
        "use thiserror::Error;\n",
        "use tempfile::{Builder as TempfileBuilder, NamedTempFile};\n"
        "use thiserror::Error;\n",
    )

    replace_once(
        install_rs,
        '''    #[error("{}", translate!("install-error-backup-failed", "from" => .0.quote(), "to" => .1.quote()))]
    BackupFailed(PathBuf, PathBuf, #[source] std::io::Error),

''',
        '''    #[error("{}", translate!("install-error-backup-failed", "from" => .0.quote(), "to" => .1.quote()))]
    BackupFailed(PathBuf, PathBuf, #[source] std::io::Error),

    #[error("{}", translate!("install-error-publish-staged-failed", "staged" => .0.quote(), "to" => .1.quote(), "error" => .2.clone()))]
    PublishStagedFailed(PathBuf, PathBuf, String),

    #[error("{}", translate!("install-error-restore-backup-failed", "backup" => .0.quote(), "to" => .1.quote(), "error" => .2.clone()))]
    RestoreBackupFailed(PathBuf, PathBuf, String),

''',
    )

    perform_backup = '''fn perform_backup(to: &Path, b: &Behavior) -> UResult<Option<PathBuf>> {
    if to.exists() {
        if b.verbose {
            writeln!(
                stdout(),
                "{}",
                translate!("install-verbose-removed", "path" => to.quote())
            )?;
        }
        let backup_path = backup_control::get_backup_path(b.backup_mode, to, &b.suffix);
        if let Some(ref backup_path) = backup_path {
            fs::rename(to, backup_path).map_err(|err| {
                InstallError::BackupFailed(to.to_path_buf(), backup_path.clone(), err)
            })?;
        }
        Ok(backup_path)
    } else {
        Ok(None)
    }
}

'''
    replace_once(
        install_rs,
        perform_backup,
        perform_backup
        + '''#[cfg(unix)]
fn restore_backup_noclobber(backup_path: &Path, to: &Path) -> UResult<()> {
    fs::hard_link(backup_path, to).map_err(|error| {
        InstallError::RestoreBackupFailed(
            backup_path.to_path_buf(),
            to.to_path_buf(),
            error.to_string(),
        )
    })?;

    fs::remove_file(backup_path).map_err(|error| {
        InstallError::RestoreBackupFailed(
            backup_path.to_path_buf(),
            to.to_path_buf(),
            error.to_string(),
        )
    })?;

    Ok(())
}

#[cfg(unix)]
fn copy_with_staged_backup(
    from: &Path,
    to: &Path,
    b: &Behavior,
    backup_path: &Path,
) -> UResult<()> {
    let parent = to.parent().unwrap_or_else(|| Path::new("."));
    let mut staged = TempfileBuilder::new()
        .prefix(".install-staging-")
        .tempfile_in(parent)
        .map_err(|error| {
            InstallError::InstallFailed(
                from.to_path_buf(),
                to.to_path_buf(),
                error.to_string(),
            )
        })?;
    let mut source = File::open(from)?;

    if let Err(error) = copy_stream(&mut source, staged.as_file_mut()) {
        let copy_error = InstallError::InstallFailed(
            from.to_path_buf(),
            to.to_path_buf(),
            error.to_string(),
        );
        if let Err(cleanup_error) = staged.close() {
            show_error!("failed to remove private install staging file: {cleanup_error}");
        }
        if let Err(restore_error) = restore_backup_noclobber(backup_path, to) {
            show!(copy_error);
            return Err(restore_error);
        }
        return Err(copy_error.into());
    }

    let dest = match staged.persist_noclobber(to) {
        Ok(file) => file,
        Err(error) => {
            let tempfile::PersistError { error, file } = error;
            let staged_path = file.path().to_path_buf();
            let message = error.to_string();
            if let Err(cleanup_error) = file.close() {
                show_error!("failed to remove private install staging file: {cleanup_error}");
            }
            return Err(InstallError::PublishStagedFailed(
                staged_path,
                to.to_path_buf(),
                message,
            )
            .into());
        }
    };

    finalize_installed_file(from, to, b, Some(backup_path.to_path_buf()), &dest)
}

#[cfg(all(test, unix))]
mod backup_transaction_tests {
    use super::restore_backup_noclobber;
    use std::fs;
    use tempfile::tempdir;

    #[test]
    fn restore_backup_noclobber_restores_absent_destination() {
        let directory = tempdir().unwrap();
        let backup = directory.path().join("file~");
        let destination = directory.path().join("file");
        fs::write(&backup, "original").unwrap();

        restore_backup_noclobber(&backup, &destination).unwrap();

        assert_eq!(fs::read_to_string(&destination).unwrap(), "original");
        assert!(!backup.exists());
    }

    #[test]
    fn restore_backup_noclobber_preserves_occupied_destination() {
        let directory = tempdir().unwrap();
        let backup = directory.path().join("file~");
        let destination = directory.path().join("file");
        fs::write(&backup, "original").unwrap();
        fs::write(&destination, "replacement").unwrap();

        assert!(restore_backup_noclobber(&backup, &destination).is_err());

        assert_eq!(fs::read_to_string(&backup).unwrap(), "original");
        assert_eq!(fs::read_to_string(&destination).unwrap(), "replacement");
    }
}

''',
    )

    replace_once(
        install_rs,
        '''    // Declare the path here as we may need it for the verbose output below.
    let backup_path = perform_backup(to, b)?;

    let dest = copy_file(from, to)?;

    #[cfg(unix)]
    {
        finalize_installed_file(from, to, b, backup_path, &dest)
    }
''',
        '''    // Declare the path here as we may need it for the verbose output below.
    let backup_path = perform_backup(to, b)?;

    #[cfg(unix)]
    if let Some(ref backup_path) = backup_path
        && backup_path.as_path() != to
    {
        return copy_with_staged_backup(from, to, b, backup_path);
    }

    let dest = copy_file(from, to)?;

    #[cfg(unix)]
    {
        finalize_installed_file(from, to, b, backup_path, &dest)
    }
''',
    )

    replace_once(
        en_us,
        "install-error-backup-failed = cannot backup { $from } to { $to }\n",
        "install-error-backup-failed = cannot backup { $from } to { $to }\n"
        "install-error-publish-staged-failed = cannot publish staged file { $staged } to { $to }: { $error }\n"
        "install-error-restore-backup-failed = cannot restore backup { $backup } to { $to }: { $error }\n",
    )
    replace_once(
        fr_fr,
        "install-error-backup-failed = impossible de sauvegarder { $from } vers { $to }\n",
        "install-error-backup-failed = impossible de sauvegarder { $from } vers { $to }\n"
        "install-error-publish-staged-failed = impossible de publier le fichier temporaire { $staged } vers { $to } : { $error }\n"
        "install-error-restore-backup-failed = impossible de restaurer la sauvegarde { $backup } vers { $to } : { $error }\n",
    )

    insertion = '''#[test]
#[cfg(target_os = "linux")]
fn test_install_restores_destination_after_copy_error_with_backup() {
    for mode in ["simple", "existing", "numbered"] {
        let scene = TestScenario::new(util_name!());
        let at = &scene.fixtures;

        at.mkdir_all("source");
        at.mkdir("dest");
        std::os::unix::fs::symlink("/proc/self/mem", at.plus("source/file")).unwrap();
        at.write("dest/file", "original");

        scene
            .ucmd()
            .arg(format!("--backup={mode}"))
            .arg("source/file")
            .arg("dest/file")
            .fails()
            .stderr_contains("Input/output error");

        assert_eq!(at.read("dest/file"), "original");
        assert!(!at.file_exists("dest/file~"));
        assert!(!at.file_exists("dest/file.~1~"));
    }
}

#[test]
#[cfg(target_os = "linux")]
fn test_install_copy_error_rollback_preserves_original_backup_for_later_source() {
    let scene = TestScenario::new(util_name!());
    let at = &scene.fixtures;

    at.mkdir_all("source1");
    at.mkdir_all("source2");
    at.mkdir("dest");
    std::os::unix::fs::symlink("/proc/self/mem", at.plus("source1/file")).unwrap();
    at.write("source2/file", "second");
    at.write("dest/file", "original");

    scene
        .ucmd()
        .arg("--backup=simple")
        .arg("-t")
        .arg("dest")
        .arg("source1/file")
        .arg("source2/file")
        .fails()
        .stderr_contains("Input/output error");

    assert_eq!(at.read("dest/file"), "second");
    assert_eq!(at.read("dest/file~"), "original");
}

#[test]
#[cfg(target_os = "linux")]
fn test_install_copy_error_rollback_preserves_existing_numbered_backup() {
    let scene = TestScenario::new(util_name!());
    let at = &scene.fixtures;

    at.mkdir_all("source");
    at.mkdir("dest");
    std::os::unix::fs::symlink("/proc/self/mem", at.plus("source/file")).unwrap();
    at.write("dest/file", "original");
    at.write("dest/file.~1~", "older");

    scene
        .ucmd()
        .arg("--backup=existing")
        .arg("source/file")
        .arg("dest/file")
        .fails()
        .stderr_contains("Input/output error");

    assert_eq!(at.read("dest/file"), "original");
    assert_eq!(at.read("dest/file.~1~"), "older");
    assert!(!at.file_exists("dest/file.~2~"));
}

#[test]
#[cfg(unix)]
fn test_install_staged_publication_does_not_clobber_replacement() {
    use std::fs::OpenOptions;
    use std::io::Write;
    use std::thread;
    use std::time::{Duration, Instant};

    let source = "source-pipe";
    let destination = "target";
    let backup = "target~";
    let scene = TestScenario::new(util_name!());
    let at = &scene.fixtures;
    at.mkfifo(source);
    at.write(destination, "original");

    let child = scene
        .ucmd()
        .arg("--backup=simple")
        .arg(source)
        .arg(destination)
        .run_no_wait();

    let deadline = Instant::now() + Duration::from_secs(10);
    while !at.file_exists(backup) {
        assert!(
            Instant::now() < deadline,
            "install did not create the backup before the race deadline"
        );
        thread::sleep(Duration::from_millis(10));
    }
    assert!(!at.file_exists(destination));
    at.write(destination, "replacement");

    let pipe_path = at.plus(source);
    let writer = thread::spawn(move || {
        let mut pipe = OpenOptions::new().write(true).open(pipe_path).unwrap();
        pipe.write_all(b"new-data").unwrap();
    });

    let result = child.wait().unwrap();
    writer.join().unwrap();

    result
        .failure()
        .stderr_contains("cannot publish staged file");
    assert_eq!(at.read(destination), "replacement");
    assert_eq!(at.read(backup), "original");
    let leaked_staging = fs::read_dir(at.plus("."))
        .unwrap()
        .flatten()
        .any(|entry| {
            entry
                .file_name()
                .to_string_lossy()
                .starts_with(".install-staging-")
        });
    assert!(!leaked_staging);
}

'''
    marker = '''#[test]
#[cfg(unix)]
fn test_install_from_fifo() {
'''
    replace_once(tests, marker, insertion + marker)

    print("applied fd-staged backup rollback candidate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
