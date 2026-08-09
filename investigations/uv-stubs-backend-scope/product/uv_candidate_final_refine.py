from __future__ import annotations

import pathlib
import sys


def replace_exact(text: str, old: str, new: str, expected: int, label: str) -> str:
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{label}: expected {expected} matches, found {count}")
    return text.replace(old, new)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: uv_candidate_final_refine.py <crates/uv/src/commands/project/init.rs>")

    path = pathlib.Path(sys.argv[1])
    text = path.read_text()

    if (
        "ProjectBuildBackend::Maturin | ProjectBuildBackend::Scikit => {" in text
        and "UV's Scikit-build template is an extension-module starter" in text
    ):
        print("Final candidate refinement is already materialized")
        return

    if "let flit_requirement = if simple_stub" not in text:
        raise SystemExit("candidate cleanup must be materialized before final refinement")

    prerequisite_block = '''                if !simple_stub {
                    pyproject_build_backend_prerequisites(name, path, build_backend)?;
                }
'''
    text = replace_exact(
        text,
        prerequisite_block,
        '''                pyproject_build_backend_prerequisites(name, path, build_backend)?;
''',
        2,
        "source-generating backend prerequisite calls",
    )

    text = replace_exact(
        text,
        '''        ProjectBuildBackend::Uv | ProjectBuildBackend::Flit | ProjectBuildBackend::Scikit => None,
        ProjectBuildBackend::Maturin => unreachable!("validated simple stub backend"),''',
        '''        ProjectBuildBackend::Uv | ProjectBuildBackend::Flit => None,
        ProjectBuildBackend::Maturin | ProjectBuildBackend::Scikit => {
            unreachable!("validated simple stub backend")
        }''',
        1,
        "stub config native backend invariant",
    )

    text = replace_exact(
        text,
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
        1,
        "native backend diagnostic precision",
    )

    path.write_text(text)


if __name__ == "__main__":
    main()
