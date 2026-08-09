from __future__ import annotations

import pathlib
import sys

MARKER = '''#[test]
fn init_bare_lib() {'''

TESTS = r'''#[test]
fn init_package_simple_stub() -> Result<()> {
    let context = uv_test::test_context!("3.12");

    let child = context.temp_dir.child("foo-stubs");
    child.create_dir_all()?;

    context
        .init()
        .current_dir(&child)
        .arg("--package")
        .assert()
        .success();

    let pyproject = fs_err::read_to_string(child.join("pyproject.toml"))?;
    let _ = fs_err::read_to_string(child.join("src/foo-stubs/__init__.pyi"))?;
    child
        .child("src/foo_stubs/__init__.py")
        .assert(predicate::path::missing());

    insta::with_settings!({
        filters => context.filters(),
    }, {
        assert_snapshot!(
            pyproject, @r#"
        [project]
        name = "foo-stubs"
        version = "0.1.0"
        description = "Add your description here"
        readme = "README.md"
        requires-python = ">=3.12"
        dependencies = []

        [build-system]
        requires = ["uv_build>=[CURRENT_VERSION],<[NEXT_BREAKING]"]
        build-backend = "uv_build"
        "#
        );
    });

    context.build().current_dir(&child).assert().success();

    Ok(())
}

#[test]
fn init_simple_stub_pure_python_backends() -> Result<()> {
    let context = uv_test::test_context!("3.12");

    let cases = [
        (
            "hatchling",
            "[tool.hatch.build.targets.wheel]\npackages = [\"src/foo-stubs\"]",
        ),
        (
            "poetry",
            "[tool.poetry]\npackages = [{ include = \"foo-stubs\", from = \"src\" }]",
        ),
        ("flit", "requires = [\"flit_core>=4,<5\"]"),
        (
            "pdm",
            "[tool.pdm.build]\nincludes = [\"src/foo-stubs\"]",
        ),
        (
            "setuptools",
            "[tool.setuptools.package-data]\n\"*\" = [\"*.pyi\"]",
        ),
    ];

    for (backend, expected_config) in cases {
        let child = context.temp_dir.child(format!("foo-stubs-{backend}"));
        child.create_dir_all()?;

        context
            .init()
            .current_dir(&child)
            .arg("--package")
            .arg("--name")
            .arg("foo-stubs")
            .arg("--build-backend")
            .arg(backend)
            .assert()
            .success();

        let pyproject = fs_err::read_to_string(child.join("pyproject.toml"))?;
        assert!(
            !pyproject.contains("[project.scripts]"),
            "{backend}: stub scaffold unexpectedly contains a runtime script:\n{pyproject}"
        );
        assert!(
            pyproject.contains(expected_config),
            "{backend}: missing expected stub configuration:\n{pyproject}"
        );
        let _ = fs_err::read_to_string(child.join("src/foo-stubs/__init__.pyi"))?;
        child
            .child("src/foo_stubs/__init__.py")
            .assert(predicate::path::missing());
    }

    let child = context.temp_dir.child("foo-stubs-lib");
    child.create_dir_all()?;
    context
        .init()
        .current_dir(&child)
        .arg("--lib")
        .arg("--name")
        .arg("foo-stubs")
        .arg("--build-backend")
        .arg("hatchling")
        .assert()
        .success();
    let pyproject = fs_err::read_to_string(child.join("pyproject.toml"))?;
    assert!(!pyproject.contains("[project.scripts]"));
    assert!(pyproject.contains(
        "[tool.hatch.build.targets.wheel]\npackages = [\"src/foo-stubs\"]"
    ));
    let _ = fs_err::read_to_string(child.join("src/foo-stubs/__init__.pyi"))?;

    Ok(())
}

#[test]
fn init_simple_stub_native_backends() -> Result<()> {
    let context = uv_test::test_context!("3.12");

    for backend in ["scikit", "maturin"] {
        let child_name = format!("reject-{backend}");
        context
            .init()
            .current_dir(&context.temp_dir)
            .arg(&child_name)
            .arg("--package")
            .arg("--name")
            .arg("foo-stubs")
            .arg("--build-backend")
            .arg(backend)
            .assert()
            .failure()
            .stderr(predicate::str::contains("generated simple stub scaffold"))
            .stderr(predicate::str::contains("use `--bare`"));

        context
            .temp_dir
            .child(&child_name)
            .assert(predicate::path::missing());

        let child = context.temp_dir.child(format!("bare-{backend}"));
        child.create_dir_all()?;
        context
            .init()
            .current_dir(&child)
            .arg("--bare")
            .arg("--name")
            .arg("foo-stubs")
            .arg("--build-backend")
            .arg(backend)
            .assert()
            .success();
        let _ = fs_err::read_to_string(child.join("pyproject.toml"))?;
        child.child("src").assert(predicate::path::missing());
    }

    Ok(())
}

'''


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: uv_native_tests_transform.py <crates/uv/tests/project/init.rs>")

    path = pathlib.Path(sys.argv[1])
    text = path.read_text()

    if "fn init_package_simple_stub()" in text:
        print("UV-native simple-stub tests already materialized")
        return

    count = text.count(MARKER)
    if count != 1:
        raise SystemExit(f"expected exactly one test insertion marker, found {count}")

    path.write_text(text.replace(MARKER, TESTS + MARKER, 1))


if __name__ == "__main__":
    main()
