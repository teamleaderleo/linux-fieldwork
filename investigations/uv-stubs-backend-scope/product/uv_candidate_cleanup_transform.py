from __future__ import annotations

import pathlib
import sys


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def replace_exact(text: str, old: str, new: str, expected: int, label: str) -> str:
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{label}: expected {expected} matches, found {count}")
    return text.replace(old, new)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: uv_candidate_cleanup_transform.py <crates/uv/src/commands/project/init.rs>")

    path = pathlib.Path(sys.argv[1])
    text = path.read_text()

    if "let flit_requirement = if simple_stub" in text:
        print("Candidate cleanup is already materialized")
        return

    text = replace_once(
        text,
        '''        let mut pyproject = pyproject_project(
            name,
            requires_python,
            author.as_ref(),
            description,
            no_description,
            no_readme || bare,
        );

        match self {''',
        '''        let mut pyproject = pyproject_project(
            name,
            requires_python,
            author.as_ref(),
            description,
            no_description,
            no_readme || bare,
        );

        if simple_stub {
            if let Some(config) = pyproject_simple_stub_config(name, build_backend) {
                pyproject.push('\\n');
                pyproject.push_str(&config);
            }
        }

        match self {''',
        "shared stub config insertion",
    )

    duplicate_config = '''                if let Some(config) = pyproject_simple_stub_config(name, build_backend, simple_stub)
                {
                    pyproject.push('\\n');
                    pyproject.push_str(&config);
                }

'''
    text = replace_exact(
        text,
        duplicate_config,
        "",
        2,
        "duplicate package/library stub config",
    )

    text = replace_once(
        text,
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
        '''        ProjectBuildBackend::Flit => {
            let flit_requirement = if simple_stub {
                "flit_core>=4,<5"
            } else {
                "flit_core>=3.2,<4"
            };
            indoc::formatdoc! {r#"
                [build-system]
                requires = ["{flit_requirement}"]
                build-backend = "flit_core.buildapi"
            "#}
        },''',
        "Flit requirement factoring",
    )

    text = replace_once(
        text,
        '''fn validate_simple_stub_backend(
    package: &PackageName,
    build_backend: ProjectBuildBackend,
) -> Result<()> {
    match build_backend {
        ProjectBuildBackend::Maturin => bail!(
            "The generated simple stub scaffold for `{package}` is incompatible with the Maturin extension-module template; choose a Python build backend or use `--bare` for a custom Maturin layout"
        ),
        ProjectBuildBackend::Scikit => bail!(
            "The generated simple stub scaffold for `{package}` is incompatible with the current Scikit-build extension-module template; choose a Python build backend or use `--bare` for a custom Scikit-build layout"
        ),
        _ => Ok(()),
    }
}''',
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
        "native backend diagnostic factoring",
    )

    text = replace_once(
        text,
        '''fn pyproject_simple_stub_config(
    package: &PackageName,
    build_backend: ProjectBuildBackend,
    simple_stub: bool,
) -> Option<String> {
    if !simple_stub {
        return None;
    }

    let package = package.as_str();''',
        '''fn pyproject_simple_stub_config(
    package: &PackageName,
    build_backend: ProjectBuildBackend,
) -> Option<String> {
    let package = package.as_str();''',
        "stub config signature factoring",
    )

    path.write_text(text)


if __name__ == "__main__":
    main()
