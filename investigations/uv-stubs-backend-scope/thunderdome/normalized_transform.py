from __future__ import annotations

import pathlib
import sys


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one source match, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in {"reject", "support"}:
        raise SystemExit("usage: normalized_transform.py <reject|support> <uv init.rs>")

    scikit_policy = sys.argv[1]
    path = pathlib.Path(sys.argv[2])
    text = path.read_text()

    old_init = '''    fn init(
        self,
        name: &PackageName,
        path: &Path,
        requires_python: &RequiresPython,
        description: Option<&str>,
        no_description: bool,
        bare: bool,
        vcs: Option<VersionControlSystem>,
        build_backend: Option<ProjectBuildBackend>,
        author_from: Option<AuthorFrom>,
        no_readme: bool,
    ) -> Result<()> {
        fs_err::create_dir_all(path)?;

        // Initialize the version control system first so that Git configuration can properly
        // read conditional includes that depend on the repository path.
        init_vcs(path, vcs)?;

        // Do not fill in `authors` for non-packaged applications unless explicitly requested.
        let author_from = author_from.unwrap_or_else(|| match self {
            Self::ApplicationWithLibrary | Self::Library | Self::BareWithBuildSystem => {
                AuthorFrom::default()
            }
            Self::Application | Self::Bare => AuthorFrom::None,
        });
        let author = get_author_info(path, author_from);

        // Create the `pyproject.toml`
        let mut pyproject = pyproject_project(
            name,
            requires_python,
            author.as_ref(),
            description,
            no_description,
            no_readme || bare,
        );

        match self {
            // Create only the most barebones `pyproject.toml`, no build system
            Self::Bare => {}
            // Create only a barebones `pyproject.toml`, but with a build system table
            Self::BareWithBuildSystem => {
                // Add a build system
                let build_backend = build_backend.unwrap_or(ProjectBuildBackend::Uv);
                pyproject.push('\\n');
                pyproject.push_str(&pyproject_build_system(name, build_backend));
            }
            Self::ApplicationWithLibrary => {
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
            }
            Self::Application => {
                let main_contents = indoc::formatdoc! {r#"
                    def main():
                        print("Hello from {name}!")


                    if __name__ == "__main__":
                        main()
                "#};

                // Create `main.py` if it doesn't exist
                // (This isn't intended to be a particularly special or magical filename, just nice)
                // TODO(zanieb): Only create `main.py` if there are no other Python files?
                let main_py = path.join("main.py");
                if !main_py.try_exists()? && !bare {
                    fs_err::write(path.join("main.py"), main_contents)?;
                }
            }
            Self::Library => {
                let build_backend = build_backend.unwrap_or(ProjectBuildBackend::Uv);
                pyproject.push('\\n');
                pyproject.push_str(&pyproject_build_system(name, build_backend));
                pyproject_build_backend_prerequisites(name, path, build_backend)?;

                // Generate `src` files
                generate_package_scripts(name, path, build_backend, true)?;
            }
        }
        fs_err::write(path.join("pyproject.toml"), pyproject)?;
        Ok(())
    }'''

    new_init = '''    fn init(
        self,
        name: &PackageName,
        path: &Path,
        requires_python: &RequiresPython,
        description: Option<&str>,
        no_description: bool,
        bare: bool,
        vcs: Option<VersionControlSystem>,
        build_backend: Option<ProjectBuildBackend>,
        author_from: Option<AuthorFrom>,
        no_readme: bool,
    ) -> Result<()> {
        let build_backend = build_backend.unwrap_or(ProjectBuildBackend::Uv);
        let simple_stub = matches!(self, Self::ApplicationWithLibrary | Self::Library)
            && is_simple_stub_project(name);
        if simple_stub {
            validate_simple_stub_backend(name, build_backend)?;
        }

        fs_err::create_dir_all(path)?;

        // Initialize the version control system first so that Git configuration can properly
        // read conditional includes that depend on the repository path.
        init_vcs(path, vcs)?;

        // Do not fill in `authors` for non-packaged applications unless explicitly requested.
        let author_from = author_from.unwrap_or_else(|| match self {
            Self::ApplicationWithLibrary | Self::Library | Self::BareWithBuildSystem => {
                AuthorFrom::default()
            }
            Self::Application | Self::Bare => AuthorFrom::None,
        });
        let author = get_author_info(path, author_from);

        // Create the `pyproject.toml`
        let mut pyproject = pyproject_project(
            name,
            requires_python,
            author.as_ref(),
            description,
            no_description,
            no_readme || bare,
        );

        match self {
            // Create only the most barebones `pyproject.toml`, no build system
            Self::Bare => {}
            // Create only a barebones `pyproject.toml`, but with a build system table
            Self::BareWithBuildSystem => {
                // Bare initialization deliberately leaves source-layout decisions to the user.
                pyproject.push('\\n');
                pyproject.push_str(&pyproject_build_system(name, build_backend, false));
            }
            Self::ApplicationWithLibrary => {
                // The inferred simple stub scaffold has no generated runtime module to target.
                if !simple_stub {
                    pyproject.push('\\n');
                    pyproject.push_str(&pyproject_project_scripts(name, name.as_str(), "main"));
                }

                if let Some(config) = pyproject_simple_stub_config(name, build_backend, simple_stub) {
                    pyproject.push('\\n');
                    pyproject.push_str(&config);
                }

                pyproject.push('\\n');
                pyproject.push_str(&pyproject_build_system(name, build_backend, simple_stub));
                if !simple_stub {
                    pyproject_build_backend_prerequisites(name, path, build_backend)?;
                }

                generate_package_scripts(name, path, build_backend, simple_stub, false)?;
            }
            Self::Application => {
                let main_contents = indoc::formatdoc! {r#"
                    def main():
                        print("Hello from {name}!")


                    if __name__ == "__main__":
                        main()
                "#};

                // Create `main.py` if it doesn't exist
                // (This isn't intended to be a particularly special or magical filename, just nice)
                // TODO(zanieb): Only create `main.py` if there are no other Python files?
                let main_py = path.join("main.py");
                if !main_py.try_exists()? && !bare {
                    fs_err::write(path.join("main.py"), main_contents)?;
                }
            }
            Self::Library => {
                if let Some(config) = pyproject_simple_stub_config(name, build_backend, simple_stub) {
                    pyproject.push('\\n');
                    pyproject.push_str(&config);
                }

                pyproject.push('\\n');
                pyproject.push_str(&pyproject_build_system(name, build_backend, simple_stub));
                if !simple_stub {
                    pyproject_build_backend_prerequisites(name, path, build_backend)?;
                }

                generate_package_scripts(name, path, build_backend, simple_stub, true)?;
            }
        }
        fs_err::write(path.join("pyproject.toml"), pyproject)?;
        Ok(())
    }'''

    text = replace_once(text, old_init, new_init, "project init implementation")

    old_build_system = '''fn pyproject_build_system(package: &PackageName, build_backend: ProjectBuildBackend) -> String {
    let module_name = package.as_dist_info_name();
    match build_backend {
        ProjectBuildBackend::Uv => {
            // Limit to the stable version range.
            let min_version = Version::from_str(uv_version::version()).unwrap();
            debug_assert!(
                min_version.release()[0] == 0,
                "migrate to major version bumps"
            );
            let max_version = Version::new(
                [0, min_version.release()[1] + 1]
                    .into_iter()
                    // Add trailing zeroes to match the version length, to use the same style
                    // as `--bounds`.
                    .chain(iter::repeat_n(0, min_version.release().len() - 2)),
            );
            indoc::formatdoc! {r#"
                [build-system]
                requires = ["uv_build>={min_version},<{max_version}"]
                build-backend = "uv_build"
            "#}
        },
        // Pure-python backends
        ProjectBuildBackend::Hatch => indoc::indoc! {r#"
                [build-system]
                requires = ["hatchling"]
                build-backend = "hatchling.build"
            "#}
        .to_string(),
        ProjectBuildBackend::Flit => indoc::indoc! {r#"
                [build-system]
                requires = ["flit_core>=3.2,<4"]
                build-backend = "flit_core.buildapi"
            "#}
        .to_string(),
        ProjectBuildBackend::PDM => indoc::indoc! {r#"
                [build-system]
                requires = ["pdm-backend"]
                build-backend = "pdm.backend"
            "#}
        .to_string(),
        ProjectBuildBackend::Setuptools => indoc::indoc! {r#"
                [build-system]
                requires = ["setuptools>=61"]
                build-backend = "setuptools.build_meta"
            "#}
        .to_string(),
        ProjectBuildBackend::Poetry => indoc::indoc! {r#"
                [build-system]
                requires = ["poetry-core>=2,<3"]
                build-backend = "poetry.core.masonry.api"
            "#}
        .to_string(),
        // Binary build backends
        ProjectBuildBackend::Maturin => indoc::formatdoc! {r#"
                [tool.maturin]
                module-name = "{module_name}._core"
                python-packages = ["{module_name}"]
                python-source = "src"

                [tool.uv]
                cache-keys = [{{ file = "pyproject.toml" }}, {{ file = "src/**/*.rs" }}, {{ file = "Cargo.toml" }}, {{ file = "Cargo.lock" }}]

                [build-system]
                requires = ["maturin>=1.0,<2.0"]
                build-backend = "maturin"
            "#},
        ProjectBuildBackend::Scikit => indoc::indoc! {r#"
                [tool.scikit-build]
                minimum-version = "build-system.requires"
                build-dir = "build/{wheel_tag}"

                [tool.uv]
                cache-keys = [{ file = "pyproject.toml" }, { file = "src/**/*.{h,c,hpp,cpp}" }, { file = "CMakeLists.txt" }]

                [build-system]
                requires = ["scikit-build-core>=0.12", "pybind11>=3"]
                build-backend = "scikit_build_core.build"
            "#}
        .to_string(),
    }
}'''

    if scikit_policy == "support":
        scikit_arm = '''        ProjectBuildBackend::Scikit => {
            if simple_stub {
                indoc::formatdoc! {r#"
                    [tool.scikit-build]
                    minimum-version = "build-system.requires"
                    wheel.cmake = false
                    wheel.packages = ["src/{}"]

                    [build-system]
                    requires = ["scikit-build-core>=0.12", "pybind11>=3"]
                    build-backend = "scikit_build_core.build"
                "#, package.as_str()}
            } else {
                indoc::indoc! {r#"
                    [tool.scikit-build]
                    minimum-version = "build-system.requires"
                    build-dir = "build/{wheel_tag}"

                    [tool.uv]
                    cache-keys = [{ file = "pyproject.toml" }, { file = "src/**/*.{h,c,hpp,cpp}" }, { file = "CMakeLists.txt" }]

                    [build-system]
                    requires = ["scikit-build-core>=0.12", "pybind11>=3"]
                    build-backend = "scikit_build_core.build"
                "#}
                .to_string()
            }
        },'''
    else:
        scikit_arm = '''        ProjectBuildBackend::Scikit => indoc::indoc! {r#"
                [tool.scikit-build]
                minimum-version = "build-system.requires"
                build-dir = "build/{wheel_tag}"

                [tool.uv]
                cache-keys = [{ file = "pyproject.toml" }, { file = "src/**/*.{h,c,hpp,cpp}" }, { file = "CMakeLists.txt" }]

                [build-system]
                requires = ["scikit-build-core>=0.12", "pybind11>=3"]
                build-backend = "scikit_build_core.build"
            "#}
        .to_string(),'''

    new_build_system = '''fn pyproject_build_system(
    package: &PackageName,
    build_backend: ProjectBuildBackend,
    simple_stub: bool,
) -> String {
    let module_name = package.as_dist_info_name();
    match build_backend {
        ProjectBuildBackend::Uv => {
            // Limit to the stable version range.
            let min_version = Version::from_str(uv_version::version()).unwrap();
            debug_assert!(
                min_version.release()[0] == 0,
                "migrate to major version bumps"
            );
            let max_version = Version::new(
                [0, min_version.release()[1] + 1]
                    .into_iter()
                    // Add trailing zeroes to match the version length, to use the same style
                    // as `--bounds`.
                    .chain(iter::repeat_n(0, min_version.release().len() - 2)),
            );
            indoc::formatdoc! {r#"
                [build-system]
                requires = ["uv_build>={min_version},<{max_version}"]
                build-backend = "uv_build"
            "#}
        },
        // Pure-python backends
        ProjectBuildBackend::Hatch => indoc::indoc! {r#"
                [build-system]
                requires = ["hatchling"]
                build-backend = "hatchling.build"
            "#}
        .to_string(),
        ProjectBuildBackend::Flit => {
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
        },
        ProjectBuildBackend::PDM => indoc::indoc! {r#"
                [build-system]
                requires = ["pdm-backend"]
                build-backend = "pdm.backend"
            "#}
        .to_string(),
        ProjectBuildBackend::Setuptools => indoc::indoc! {r#"
                [build-system]
                requires = ["setuptools>=61"]
                build-backend = "setuptools.build_meta"
            "#}
        .to_string(),
        ProjectBuildBackend::Poetry => indoc::indoc! {r#"
                [build-system]
                requires = ["poetry-core>=2,<3"]
                build-backend = "poetry.core.masonry.api"
            "#}
        .to_string(),
        // Binary build backends
        ProjectBuildBackend::Maturin => indoc::formatdoc! {r#"
                [tool.maturin]
                module-name = "{module_name}._core"
                python-packages = ["{module_name}"]
                python-source = "src"

                [tool.uv]
                cache-keys = [{{ file = "pyproject.toml" }}, {{ file = "src/**/*.rs" }}, {{ file = "Cargo.toml" }}, {{ file = "Cargo.lock" }}]

                [build-system]
                requires = ["maturin>=1.0,<2.0"]
                build-backend = "maturin"
            "#},
''' + scikit_arm + '''
    }
}'''

    text = replace_once(text, old_build_system, new_build_system, "build-system implementation")

    if scikit_policy == "support":
        validation_body = '''    if build_backend == ProjectBuildBackend::Maturin {
        bail!(
            "The generated simple stub scaffold for `{package}` is incompatible with the Maturin extension-module template; choose a Python build backend or use `--bare` for a custom Maturin layout"
        );
    }
    Ok(())'''
    else:
        validation_body = '''    match build_backend {
        ProjectBuildBackend::Maturin => bail!(
            "The generated simple stub scaffold for `{package}` is incompatible with the Maturin extension-module template; choose a Python build backend or use `--bare` for a custom Maturin layout"
        ),
        ProjectBuildBackend::Scikit => bail!(
            "The generated simple stub scaffold for `{package}` is incompatible with the current Scikit-build extension-module template; choose a Python build backend or use `--bare` for a custom Scikit-build layout"
        ),
        _ => Ok(()),
    }'''

    helpers = '''
/// Infer UV's simple generated stub scaffold from the canonical project name.
///
/// This is a scaffold-generation heuristic, not a claim that every distribution ending in
/// `-stubs` contains only stub files. Bare initialization deliberately bypasses this inference.
fn is_simple_stub_project(package: &PackageName) -> bool {
    package.as_str().ends_with("-stubs")
}

fn validate_simple_stub_backend(
    package: &PackageName,
    build_backend: ProjectBuildBackend,
) -> Result<()> {
''' + validation_body + '''
}

fn pyproject_simple_stub_config(
    package: &PackageName,
    build_backend: ProjectBuildBackend,
    simple_stub: bool,
) -> Option<String> {
    if !simple_stub {
        return None;
    }

    let package = package.as_str();
    match build_backend {
        ProjectBuildBackend::Hatch => Some(indoc::formatdoc! {r#"
            [tool.hatch.build.targets.wheel]
            packages = ["src/{package}"]
        "#}),
        ProjectBuildBackend::PDM => Some(indoc::formatdoc! {r#"
            [tool.pdm.build]
            includes = ["src/{package}"]
        "#}),
        ProjectBuildBackend::Setuptools => Some(indoc::indoc! {r#"
            [tool.setuptools.package-data]
            "*" = ["*.pyi"]
        "#}.to_string()),
        ProjectBuildBackend::Poetry => Some(indoc::formatdoc! {r#"
            [tool.poetry]
            packages = [{{ include = "{package}", from = "src" }}]
        "#}),
        ProjectBuildBackend::Uv | ProjectBuildBackend::Flit | ProjectBuildBackend::Scikit => None,
        ProjectBuildBackend::Maturin => unreachable!("validated simple stub backend"),
    }
}
'''

    text = replace_once(
        text,
        '''}

/// Generate the `[project.scripts]` section of a `pyproject.toml`.
fn pyproject_project_scripts''',
        '''}
''' + helpers + '''
/// Generate the `[project.scripts]` section of a `pyproject.toml`.
fn pyproject_project_scripts''',
        "stub helpers insertion",
    )

    text = replace_once(
        text,
        '''fn generate_package_scripts(
    package: &PackageName,
    path: &Path,
    build_backend: ProjectBuildBackend,
    is_lib: bool,
) -> Result<()> {
    let module_name = package.as_dist_info_name();

    let src_dir = path.join("src");
    let pkg_dir = src_dir.join(&*module_name);
    fs_err::create_dir_all(&pkg_dir)?;

    let pure_python_script = if is_lib {''',
        '''fn generate_package_scripts(
    package: &PackageName,
    path: &Path,
    build_backend: ProjectBuildBackend,
    simple_stub: bool,
    is_lib: bool,
) -> Result<()> {
    let module_name = package.as_dist_info_name();

    let src_dir = path.join("src");
    let pkg_dir = if simple_stub {
        src_dir.join(package.as_str())
    } else {
        src_dir.join(&*module_name)
    };
    fs_err::create_dir_all(&pkg_dir)?;

    if simple_stub {
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
