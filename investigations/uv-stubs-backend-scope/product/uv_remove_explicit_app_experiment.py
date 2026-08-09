from __future__ import annotations

import pathlib
import re
import sys


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: uv_remove_explicit_app_experiment.py <lib.rs> <commands/project/init.rs> <tests/project/init.rs>"
        )

    lib_path = pathlib.Path(sys.argv[1])
    init_path = pathlib.Path(sys.argv[2])
    tests_path = pathlib.Path(sys.argv[3])

    lib = lib_path.read_text()
    init = init_path.read_text()
    tests = tests_path.read_text()

    if "let explicit_app = args.app;" not in lib:
        print("Explicit-app experiment is already absent")
        return

    lib = replace_once(
        lib,
        '''        ProjectCommand::Init(args) => {
            // Preserve explicit application intent before settings resolution collapses it into
            // the packaged-application project kind.
            let explicit_app = args.app;

            // Resolve the settings from the command-line arguments and workspace configuration.
            let args = settings::InitSettings::resolve(args, filesystem, environment)?;''',
        '''        ProjectCommand::Init(args) => {
            // Resolve the settings from the command-line arguments and workspace configuration.
            let args = settings::InitSettings::resolve(args, filesystem, environment)?;''',
        "remove explicit --app capture",
    )
    lib = replace_once(
        lib,
        '''                args.name,
                args.kind,
                explicit_app,
                args.bare,''',
        '''                args.name,
                args.kind,
                args.bare,''',
        "remove explicit --app dispatch argument",
    )

    init = replace_once(
        init,
        '''    name: Option<PackageName>,
    init_kind: InitKind,
    explicit_app: bool,
    bare: bool,''',
        '''    name: Option<PackageName>,
    init_kind: InitKind,
    bare: bool,''',
        "commands::init explicit_app parameter",
    )
    init = replace_once(
        init,
        '''                &name,
                project_kind,
                explicit_app,
                bare,''',
        '''                &name,
                project_kind,
                bare,''',
        "init_project explicit_app call",
    )
    init = replace_once(
        init,
        '''    name: &PackageName,
    project_kind: InitProjectKind,
    explicit_app: bool,
    bare: bool,''',
        '''    name: &PackageName,
    project_kind: InitProjectKind,
    bare: bool,''',
        "init_project explicit_app parameter",
    )
    init = replace_once(
        init,
        '''        name,
        path,
        &requires_python,
        explicit_app,
        description.as_deref(),''',
        '''        name,
        path,
        &requires_python,
        description.as_deref(),''',
        "project-kind explicit_app call",
    )
    init = replace_once(
        init,
        '''        name: &PackageName,
        path: &Path,
        requires_python: &RequiresPython,
        explicit_app: bool,
        description: Option<&str>,''',
        '''        name: &PackageName,
        path: &Path,
        requires_python: &RequiresPython,
        description: Option<&str>,''',
        "project-kind explicit_app parameter",
    )
    init = replace_once(
        init,
        '''        let simple_stub = !explicit_app
            && matches!(self, Self::ApplicationWithLibrary | Self::Library)
            && is_simple_stub_project(name);''',
        '''        let simple_stub = matches!(self, Self::ApplicationWithLibrary | Self::Library)
            && is_simple_stub_project(name);''',
        "restore simple-stub heuristic",
    )

    pattern = re.compile(
        r'''#\[test\]\nfn init_simple_stub_explicit_app_precedence\(\) -> Result<\(\)> \{.*?\n\}\n\n(?=#\[test\]\nfn init_bare_lib\(\) \{)''',
        re.DOTALL,
    )
    tests, count = pattern.subn("", tests, count=1)
    if count != 1:
        raise SystemExit(f"explicit-app compact test: expected one block, found {count}")

    lib_path.write_text(lib)
    init_path.write_text(init)
    tests_path.write_text(tests)


if __name__ == "__main__":
    main()
