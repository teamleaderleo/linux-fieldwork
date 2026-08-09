from __future__ import annotations

import pathlib
import sys


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: uv_explicit_app_integration.py <lib.rs> <commands/project/init.rs> <tests/project/init.rs>"
        )

    lib_path = pathlib.Path(sys.argv[1])
    init_path = pathlib.Path(sys.argv[2])
    tests_path = pathlib.Path(sys.argv[3])

    lib = lib_path.read_text()
    init = init_path.read_text()
    tests = tests_path.read_text()

    if "let explicit_app = args.app;" in lib:
        print("Explicit-app precedence is already materialized")
        return

    lib = replace_once(
        lib,
        '''        ProjectCommand::Init(args) => {
            // Resolve the settings from the command-line arguments and workspace configuration.
            let args = settings::InitSettings::resolve(args, filesystem, environment)?;''',
        '''        ProjectCommand::Init(args) => {
            // Preserve explicit application intent before settings resolution collapses it into
            // the packaged-application project kind.
            let explicit_app = args.app;

            // Resolve the settings from the command-line arguments and workspace configuration.
            let args = settings::InitSettings::resolve(args, filesystem, environment)?;''',
        "capture explicit --app provenance",
    )
    lib = replace_once(
        lib,
        '''                args.name,
                args.kind,
                args.bare,''',
        '''                args.name,
                args.kind,
                explicit_app,
                args.bare,''',
        "thread explicit --app from command dispatch",
    )

    init = replace_once(
        init,
        '''    name: Option<PackageName>,
    init_kind: InitKind,
    bare: bool,''',
        '''    name: Option<PackageName>,
    init_kind: InitKind,
    explicit_app: bool,
    bare: bool,''',
        "commands::init explicit_app parameter",
    )
    init = replace_once(
        init,
        '''                &name,
                project_kind,
                bare,''',
        '''                &name,
                project_kind,
                explicit_app,
                bare,''',
        "thread explicit_app into init_project",
    )
    init = replace_once(
        init,
        '''    name: &PackageName,
    project_kind: InitProjectKind,
    bare: bool,''',
        '''    name: &PackageName,
    project_kind: InitProjectKind,
    explicit_app: bool,
    bare: bool,''',
        "init_project explicit_app parameter",
    )
    init = replace_once(
        init,
        '''        name,
        path,
        &requires_python,
        description.as_deref(),''',
        '''        name,
        path,
        &requires_python,
        explicit_app,
        description.as_deref(),''',
        "thread explicit_app into project-kind generation",
    )
    init = replace_once(
        init,
        '''        name: &PackageName,
        path: &Path,
        requires_python: &RequiresPython,
        description: Option<&str>,''',
        '''        name: &PackageName,
        path: &Path,
        requires_python: &RequiresPython,
        explicit_app: bool,
        description: Option<&str>,''',
        "InitProjectKind explicit_app parameter",
    )
    init = replace_once(
        init,
        '''        let simple_stub = matches!(self, Self::ApplicationWithLibrary | Self::Library)
            && is_simple_stub_project(name);''',
        '''        let simple_stub = !explicit_app
            && matches!(self, Self::ApplicationWithLibrary | Self::Library)
            && is_simple_stub_project(name);''',
        "explicit app precedence in stub inference",
    )

    init = replace_once(
        init,
        '''fn validate_simple_stub_backend(
    package: &PackageName,
    build_backend: ProjectBuildBackend,
) -> Result<()> {
    let backend = match build_backend {
        ProjectBuildBackend::Maturin => "Maturin",
        ProjectBuildBackend::Scikit => "Scikit-build",
        _ => return Ok(()),
    };
    bail!(
        "The {backend} backend does not support the generated simple stub scaffold for `{package}`; choose a supported Python build backend or use `--bare` for a custom layout"
    )
}''',
        '''fn validate_simple_stub_backend(
    package: &PackageName,
    build_backend: ProjectBuildBackend,
) -> Result<()> {
    match build_backend {
        ProjectBuildBackend::Maturin => bail!(
            "The Maturin backend does not support the generated simple stub scaffold for `{package}`; choose a supported Python build backend or use `--bare` for a custom layout"
        ),
        ProjectBuildBackend::Scikit => bail!(
            "UV's Scikit-build template is an extension-module starter and cannot generate the simple stub scaffold for `{package}`; choose a supported Python build backend or use `--bare` for a custom Scikit-build layout"
        ),
        _ => Ok(()),
    }
}''',
        "precise native backend diagnostics",
    )

    marker = '''#[test]
fn init_bare_lib() {'''
    compact_test = r'''#[test]
fn init_simple_stub_explicit_app_precedence() -> Result<()> {
    let context = uv_test::test_context!("3.12");

    let app = context.temp_dir.child("runtime-app-stubs-name");
    app.create_dir_all()?;
    context
        .init()
        .current_dir(&app)
        .arg("--app")
        .arg("--name")
        .arg("foo-stubs")
        .assert()
        .success();
    app.child("src/foo_stubs/__init__.py")
        .assert(predicate::path::is_file());
    app.child("src/foo-stubs/__init__.pyi")
        .assert(predicate::path::missing());
    let pyproject = fs_err::read_to_string(app.join("pyproject.toml"))?;
    assert!(pyproject.contains("[project.scripts]"));
    assert!(pyproject.contains("foo-stubs = \"foo_stubs:main\""));

    for (backend, expected_files) in [
        (
            "scikit",
            ["CMakeLists.txt", "src/main.cpp", "src/foo_stubs/_core.pyi"],
        ),
        (
            "maturin",
            ["Cargo.toml", "src/lib.rs", "src/foo_stubs/_core.pyi"],
        ),
    ] {
        let child = context.temp_dir.child(format!("runtime-app-stubs-{backend}"));
        child.create_dir_all()?;
        context
            .init()
            .current_dir(&child)
            .arg("--app")
            .arg("--name")
            .arg("foo-stubs")
            .arg("--build-backend")
            .arg(backend)
            .assert()
            .success();
        for file in expected_files {
            child.child(file).assert(predicate::path::is_file());
        }
        child
            .child("src/foo-stubs/__init__.pyi")
            .assert(predicate::path::missing());
        let pyproject = fs_err::read_to_string(child.join("pyproject.toml"))?;
        assert!(pyproject.contains("[project.scripts]"));
    }

    Ok(())
}

'''
    if marker not in tests:
        raise SystemExit("explicit-app test insertion marker not found")
    tests = tests.replace(marker, compact_test + marker, 1)

    lib_path.write_text(lib)
    init_path.write_text(init)
    tests_path.write_text(tests)


if __name__ == "__main__":
    main()
