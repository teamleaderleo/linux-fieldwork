#!/usr/bin/env python3
"""Apply exact post-transform repairs to the fd-staged rollback candidate."""

from __future__ import annotations

from pathlib import Path
import sys


def replace_exact(text: str, old: str, new: str, label: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{label}: expected {expected} replacement site(s), found {count}")
    return text.replace(old, new, expected)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: finalize_fd_staged_candidate.py COREUTILS_ROOT")

    root = Path(sys.argv[1]).resolve()
    install_path = root / "src/uu/install/src/install.rs"
    tests_path = root / "tests/by-util/test_install.rs"

    install = install_path.read_text(encoding="utf-8")
    tests = tests_path.read_text(encoding="utf-8")

    install = replace_exact(
        install,
        "use tempfile::{Builder as TempfileBuilder, NamedTempFile};\n",
        "#[cfg(unix)]\nuse tempfile::{Builder as TempfileBuilder, NamedTempFile};\n",
        "tempfile import",
    )

    marker = '''#[cfg(unix)]
fn copy_with_staged_backup(
'''
    helpers = '''#[cfg(unix)]
fn strip_staged_file(staged: &NamedTempFile, b: &Behavior) -> UResult<()> {
    match process::Command::new(&b.strip_program)
        .arg(staged.path())
        .status()
    {
        Ok(status) if status.success() => Ok(()),
        Ok(status) => Err(InstallError::StripProgramFailed(
            translate!("install-error-strip-abnormal", "code" => status.code().unwrap()),
        )
        .into()),
        Err(error) => Err(InstallError::StripProgramFailed(error.to_string()).into()),
    }
}

#[cfg(unix)]
fn publish_staged_noclobber(staged: NamedTempFile, to: &Path) -> UResult<File> {
    let staged_path = staged.path().to_path_buf();
    let dest = File::open(&staged_path).map_err(|error| {
        InstallError::PublishStagedFailed(
            staged_path.clone(),
            to.to_path_buf(),
            error.to_string(),
        )
    })?;

    if let Err(error) = fs::hard_link(&staged_path, to) {
        let message = error.to_string();
        if let Err(cleanup_error) = staged.close() {
            eprintln!("failed to remove private install staging file: {cleanup_error}");
        }
        return Err(InstallError::PublishStagedFailed(
            staged_path,
            to.to_path_buf(),
            message,
        )
        .into());
    }

    // The hard link publishes the exact inode opened above without replacing an
    // occupied destination. Removing the private name leaves the published link
    // and the open descriptor as the remaining operation-owned references.
    let _ = staged.close();
    Ok(dest)
}

'''
    install = replace_exact(install, marker, helpers + marker, "staging helpers")

    old_publish = '''    let dest = match staged.persist_noclobber(to) {
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
'''
    new_publish = '''    // GNU strip and compatible tools create a sibling temporary file and rename
    // it over their input. Give the strip program only the private same-directory
    // staging pathname; the public destination remains absent until publication.
    if b.strip
        && let Err(error) = strip_staged_file(&staged, b)
    {
        let _ = staged.close();
        return Err(error);
    }

    let dest = publish_staged_noclobber(staged, to)?;
    finalize_installed_file(
        from,
        to,
        b,
        Some(backup_path.to_path_buf()),
        &dest,
        true,
    )
'''
    install = replace_exact(install, old_publish, new_publish, "staged publication")

    old_signature = '''    file: &File,
) -> UResult<()> {
    if b.strip {
'''
    new_signature = '''    file: &File,
    strip_already_done: bool,
) -> UResult<()> {
    if b.strip && !strip_already_done {
'''
    install = replace_exact(install, old_signature, new_signature, "unix finalizer signature")

    install = replace_exact(
        install,
        "finalize_installed_file(source, &target, b, backup_path, &dest)\n",
        "finalize_installed_file(source, &target, b, backup_path, &dest, false)\n",
        "safe-copy finalizer call",
    )
    install = replace_exact(
        install,
        "finalize_installed_file(from, to, b, backup_path, &dest)\n",
        "finalize_installed_file(from, to, b, backup_path, &dest, false)\n",
        "ordinary-copy finalizer call",
    )

    tests = replace_exact(
        tests,
        '''fn test_install_staged_publication_does_not_clobber_replacement() {
    use std::fs::OpenOptions;
    use std::io::Write;
    use std::thread;
    use std::time::{Duration, Instant};
''',
        '''fn test_install_staged_publication_does_not_clobber_replacement() {
    use std::fs::OpenOptions;
    use std::io::Write;
    use std::thread::{self, sleep};
    use std::time::{Duration, Instant};
''',
        "publication test imports",
    )
    tests = replace_exact(
        tests,
        "        thread::sleep(Duration::from_millis(10));\n",
        "        sleep(Duration::from_millis(10));\n",
        "publication wait",
    )

    install_path.write_text(install, encoding="utf-8")
    tests_path.write_text(tests, encoding="utf-8")
    print("finalized fd-staged candidate with path-safe strip and fd-bound metadata")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
