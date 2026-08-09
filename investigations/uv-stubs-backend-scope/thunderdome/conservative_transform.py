from __future__ import annotations

import pathlib
import sys


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one source match, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: conservative_transform.py <uv init.rs>")

    path = pathlib.Path(sys.argv[1])
    text = path.read_text()

    text = replace_once(
        text,
        '''                pyproject.push_str(&pyproject_build_system(name, build_backend));''',
        '''                pyproject.push_str(&pyproject_build_system(name, build_backend, false));''',
        "bare build-system call",
    )

    text = replace_once(
        text,
        '''            Self::ApplicationWithLibrary => {
                // Since it'll be packaged, we can add a `[project.scripts]` entry
                pyproject.push('\\n');
                pyproject.push_str(&pyproject_project_scripts(name, name.as_str(), "main"));

                // Add a build system
                let build_backend = build_backend.unwrap_or(ProjectBuildBackend::Uv);
                pyproject.push('\\n');
                pyproject.push_str(&pyproject_build_system(name, build_backend));
                pyproject_build_backend_prerequisites(name, path, build_backend)?;

                // Generate `src` files with app-style `main()` in `__init__.py`
                generate_package_scripts(name, path, build_backend, false)?;
            }''',
        '''            Self::ApplicationWithLibrary => {
                let simple_stub = simple_stub_module_dir(name).is_some();
                let build_backend = build_backend.unwrap_or(ProjectBuildBackend::Uv);
                validate_simple_stub_backend(name, build_backend)?;

                // Since it'll be packaged, we can add a `[project.scripts]` entry. The inferred
                // simple stub scaffold has no generated runtime module to target.
                if !simple_stub {
                    pyproject.push('\\n');
                    pyproject.push_str(&pyproject_project_scripts(name, name.as_str(), "main"));
                }

                // Add a build system
                pyproject.push('\\n');
                pyproject.push_str(&pyproject_build_system(name, build_backend, simple_stub));
                if !simple_stub {
                    pyproject_build_backend_prerequisites(name, path, build_backend)?;
                }

                // Generate `src` files with app-style `main()` in `__init__.py`, or the inferred
                // simple stub scaffold.
                generate_package_scripts(name, path, build_backend, false)?;
            }''',
        "packaged application block",
    )

    text = replace_once(
        text,
        '''            Self::Library => {
                let build_backend = build_backend.unwrap_or(ProjectBuildBackend::Uv);
                pyproject.push('\\n');
                pyproject.push_str(&pyproject_build_system(name, build_backend));
                pyproject_build_backend_prerequisites(name, path, build_backend)?;

                // Generate `src` files
                generate_package_scripts(name, path, build_backend, true)?;
            }''',
        '''            Self::Library => {
                let simple_stub = simple_stub_module_dir(name).is_some();
                let build_backend = build_backend.unwrap_or(ProjectBuildBackend::Uv);
                validate_simple_stub_backend(name, build_backend)?;
                pyproject.push('\\n');
                pyproject.push_str(&pyproject_build_system(name, build_backend, simple_stub));
                if !simple_stub {
                    pyproject_build_backend_prerequisites(name, path, build_backend)?;
                }

                // Generate `src` files, or the inferred simple stub scaffold.
                generate_package_scripts(name, path, build_backend, true)?;
            }''',
        "library block",
    )

    text = replace_once(
        text,
        '''fn pyproject_build_system(package: &PackageName, build_backend: ProjectBuildBackend) -> String {
    let module_name = package.as_dist_info_name();''',
        '''fn pyproject_build_system(
    package: &PackageName,
    build_backend: ProjectBuildBackend,
    simple_stub: bool,
) -> String {
    let module_name = package.as_dist_info_name();
    let stub_module_dir = if simple_stub {
        simple_stub_module_dir(package)
    } else {
        None
    };''',
        "build-system signature",
    )

    text = replace_once(
        text,
        '''        ProjectBuildBackend::Hatch => indoc::indoc! {r#"
                [build-system]
                requires = ["hatchling"]
                build-backend = "hatchling.build"
            "#}
        .to_string(),''',
        '''        ProjectBuildBackend::Hatch => {
            if let Some(stub_module_dir) = stub_module_dir.as_deref() {
                indoc::formatdoc! {r#"
                    [tool.hatch.build.targets.wheel]
                    packages = ["src/{stub_module_dir}"]

                    [build-system]
                    requires = ["hatchling"]
                    build-backend = "hatchling.build"
                "#}
            } else {
                indoc::indoc! {r#"
                    [build-system]
                    requires = ["hatchling"]
                    build-backend = "hatchling.build"
                "#}
                .to_string()
            }
        },''',
        "hatch build-system arm",
    )

    text = replace_once(
        text,
        '''        ProjectBuildBackend::Flit => indoc::indoc! {r#"
                [build-system]
                requires = ["flit_core>=3.2,<4"]
                build-backend = "flit_core.buildapi"
            "#}
        .to_string(),''',
        '''        ProjectBuildBackend::Flit => {
            if simple_stub {
                indoc::indoc! {r#"
                    [build-system]
                    requires = ["flit_core>=4,<5"]
                    build-backend = "flit_core.buildapi"
                "#}
                .to_string()
            } else {
                indoc::indoc! {r#"
                    [build-system]
                    requires = ["flit_core>=3.2,<4"]
                    build-backend = "flit_core.buildapi"
                "#}
                .to_string()
            }
        },''',
        "flit build-system arm",
    )

    text = replace_once(
        text,
        '''        ProjectBuildBackend::PDM => indoc::indoc! {r#"
                [build-system]
                requires = ["pdm-backend"]
                build-backend = "pdm.backend"
            "#}
        .to_string(),''',
        '''        ProjectBuildBackend::PDM => {
            if let Some(stub_module_dir) = stub_module_dir.as_deref() {
                indoc::formatdoc! {r#"
                    [tool.pdm.build]
                    includes = ["src/{stub_module_dir}"]

                    [build-system]
                    requires = ["pdm-backend"]
                    build-backend = "pdm.backend"
                "#}
            } else {
                indoc::indoc! {r#"
                    [build-system]
                    requires = ["pdm-backend"]
                    build-backend = "pdm.backend"
                "#}
                .to_string()
            }
        },''',
        "pdm build-system arm",
    )

    text = replace_once(
        text,
        '''        ProjectBuildBackend::Setuptools => indoc::indoc! {r#"
                [build-system]
                requires = ["setuptools>=61"]
                build-backend = "setuptools.build_meta"
            "#}
        .to_string(),''',
        '''        ProjectBuildBackend::Setuptools => {
            if simple_stub {
                indoc::indoc! {r#"
                    [tool.setuptools.package-data]
                    "*" = ["*.pyi"]

                    [build-system]
                    requires = ["setuptools>=61"]
                    build-backend = "setuptools.build_meta"
                "#}
                .to_string()
            } else {
                indoc::indoc! {r#"
                    [build-system]
                    requires = ["setuptools>=61"]
                    build-backend = "setuptools.build_meta"
                "#}
                .to_string()
            }
        },''',
        "setuptools build-system arm",
    )

    text = replace_once(
        text,
        '''        ProjectBuildBackend::Poetry => indoc::indoc! {r#"
                [build-system]
                requires = ["poetry-core>=2,<3"]
                build-backend = "poetry.core.masonry.api"
            "#}
        .to_string(),''',
        '''        ProjectBuildBackend::Poetry => {
            if let Some(stub_module_dir) = stub_module_dir.as_deref() {
                indoc::formatdoc! {r#"
                    [tool.poetry]
                    packages = [{{ include = "{stub_module_dir}", from = "src" }}]

                    [build-system]
                    requires = ["poetry-core>=2,<3"]
                    build-backend = "poetry.core.masonry.api"
                "#}
            } else {
                indoc::indoc! {r#"
                    [build-system]
                    requires = ["poetry-core>=2,<3"]
                    build-backend = "poetry.core.masonry.api"
                "#}
                .to_string()
            }
        },''',
        "poetry build-system arm",
    )

    text = replace_once(
        text,
        '''}

/// Generate the `[project.scripts]` section of a `pyproject.toml`.
fn pyproject_project_scripts''',
        '''}

/// Infer UV's simple generated stub scaffold from the conventional project name.
///
/// This is a scaffold-generation heuristic, not a claim that every distribution ending in
/// `-stubs` contains only stub files. Bare initialization deliberately bypasses this inference.
fn simple_stub_module_dir(package: &PackageName) -> Option<String> {
    package
        .as_dist_info_name()
        .strip_suffix("_stubs")
        .map(|stem| format!("{stem}-stubs"))
}

fn validate_simple_stub_backend(
    package: &PackageName,
    build_backend: ProjectBuildBackend,
) -> Result<()> {
    if simple_stub_module_dir(package).is_none() {
        return Ok(());
    }

    match build_backend {
        ProjectBuildBackend::Maturin => bail!(
            "The generated simple stub scaffold for `{package}` is incompatible with the Maturin extension-module template; choose a Python build backend or use `--bare` for a custom Maturin layout"
        ),
        ProjectBuildBackend::Scikit => bail!(
            "The generated simple stub scaffold for `{package}` is incompatible with the current Scikit-build extension-module template; choose a Python build backend or use `--bare` for a custom Scikit-build layout"
        ),
        _ => Ok(()),
    }
}

/// Generate the `[project.scripts]` section of a `pyproject.toml`.
fn pyproject_project_scripts''',
        "stub helpers insertion",
    )

    text = replace_once(
        text,
        '''    let module_name = package.as_dist_info_name();

    let src_dir = path.join("src");
    let pkg_dir = src_dir.join(&*module_name);
    fs_err::create_dir_all(&pkg_dir)?;

    let pure_python_script = if is_lib {''',
        '''    let module_name = package.as_dist_info_name();
    let stub_module_dir = simple_stub_module_dir(package);

    let src_dir = path.join("src");
    let pkg_dir = src_dir.join(stub_module_dir.as_deref().unwrap_or(module_name.as_ref()));
    fs_err::create_dir_all(&pkg_dir)?;

    if stub_module_dir.is_some() {
        let init_pyi = pkg_dir.join("__init__.pyi");
        if !init_pyi.try_exists()? {
            fs_err::write(init_pyi, "")?;
        }
        return Ok(());
    }

    let pure_python_script = if is_lib {''',
        "stub source generation",
    )

    path.write_text(text)


if __name__ == "__main__":
    main()
