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
        raise SystemExit("usage: backend_first_transform.py <uv init.rs>")

    path = pathlib.Path(sys.argv[1])
    text = path.read_text()

    text = replace_once(
        text,
        '''    fn init(
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
    }''',
        '''    fn init(
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
            && simple_stub_module_dir(name).is_some();
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
                // Bare initialization deliberately leaves custom source-layout decisions to the user.
                pyproject.push('\\n');
                pyproject.push_str(&pyproject_build_system(name, build_backend, false));
            }
            Self::ApplicationWithLibrary => {
                // The inferred simple stub scaffold has no generated runtime module to target.
                if !simple_stub {
                    pyproject.push('\\n');
                    pyproject.push_str(&pyproject_project_scripts(name, name.as_str(), "main"));
                }

                pyproject.push('\\n');
                pyproject.push_str(&pyproject_build_system(name, build_backend, simple_stub));
                if !simple_stub {
                    pyproject_build_backend_prerequisites(name, path, build_backend)?;
                }

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
                pyproject.push('\\n');
                pyproject.push_str(&pyproject_build_system(name, build_backend, simple_stub));
                if !simple_stub {
                    pyproject_build_backend_prerequisites(name, path, build_backend)?;
                }

                generate_package_scripts(name, path, build_backend, true)?;
            }
        }
        fs_err::write(path.join("pyproject.toml"), pyproject)?;
        Ok(())
    }''',
        "project init implementation",
    )

    text = replace_once(
        text,
        '''fn pyproject_build_system(package: &PackageName, build_backend: ProjectBuildBackend) -> String {
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
}''',
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
    };

    let build_system = match build_backend {
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
        ProjectBuildBackend::Scikit => {
            if let Some(stub_module_dir) = stub_module_dir.as_deref() {
                indoc::formatdoc! {r#"
                    [tool.scikit-build]
                    minimum-version = "build-system.requires"
                    wheel.cmake = false
                    wheel.packages = ["src/{stub_module_dir}"]

                    [build-system]
                    requires = ["scikit-build-core>=0.12", "pybind11>=3"]
                    build-backend = "scikit_build_core.build"
                "#}
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
        },
    };

    if !simple_stub {
        return build_system;
    }
    let stub_module_dir = stub_module_dir.as_deref().expect("simple stub module directory");
    let stub_config = match build_backend {
        ProjectBuildBackend::Hatch => indoc::formatdoc! {r#"
            [tool.hatch.build.targets.wheel]
            packages = ["src/{stub_module_dir}"]
        "#},
        ProjectBuildBackend::PDM => indoc::formatdoc! {r#"
            [tool.pdm.build]
            includes = ["src/{stub_module_dir}"]
        "#},
        ProjectBuildBackend::Setuptools => indoc::indoc! {r#"
            [tool.setuptools.package-data]
            "*" = ["*.pyi"]
        "#}
        .to_string(),
        ProjectBuildBackend::Poetry => indoc::formatdoc! {r#"
            [tool.poetry]
            packages = [{{ include = "{stub_module_dir}", from = "src" }}]
        "#},
        ProjectBuildBackend::Uv | ProjectBuildBackend::Flit | ProjectBuildBackend::Scikit => {
            String::new()
        }
        ProjectBuildBackend::Maturin => unreachable!("validated simple stub backend"),
    };

    if stub_config.is_empty() {
        build_system
    } else {
        format!("{stub_config}\\n{build_system}")
    }
}''',
        "build-system implementation",
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
    if build_backend == ProjectBuildBackend::Maturin {
        bail!(
            "The generated simple stub scaffold for `{package}` is incompatible with the Maturin extension-module template; choose a Python build backend or use `--bare` for a custom Maturin layout"
        );
    }
    Ok(())
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
