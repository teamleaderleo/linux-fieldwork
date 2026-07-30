# Tests must declare command providers instead of relying on the Essential set

## In simple words

A package test that creates a minimal root and executes a command inside it must explicitly install the package that provides that command, unless the command is part of the test's stated base-system contract.

Debian's Essential set can change. A test that passes only because a provider currently carries `Essential: yes` can fail after a legitimate archive transition even though the command, package, and product behavior remain correct.

## Stable lesson

For every command executed inside a generated root:

1. identify the binary path actually resolved in that root;
2. identify the Debian binary package that owns it;
3. include or depend on that package explicitly;
4. keep the assertion focused on the behavior under test rather than the incidental base image composition.

The outer testbed and inner generated root are separate package universes. A command available to the test driver is not automatically available inside `chroot`, `unshare`, a container image, or a bootstrap target.

## Why Essential is a weak test dependency

The `Essential` field defines a distribution-level base-system contract. It is not a stable substitute for a test dependency list.

A package can stop being Essential while remaining available and correct. When that happens:

- full or standard roots may still contain it;
- minimal or apt variants may omit it;
- a broad integration test can fail late and look like a runtime regression;
- the correct repair is often to name the provider in the test fixture.

## The mmdebstrap dev-ptmx example

The `dev-ptmx` test uses `script(1)` to exercise pseudo-terminal behavior inside a generated apt-variant root. The test included compiler, libc development, Python and passwd packages, but did not include `bsdutils`, which provides `/usr/bin/script`.

`bsdutils 1:2.41-5` was Essential. By `1:2.42.2-1`, it was no longer Essential. Debian CI run `72574145` therefore built a valid apt-variant root without `script` and failed before the PTY assertions:

```text
chroot: failed to run command ‘script’: No such file or directory
```

The bounded repair is to add `bsdutils` to the same `--include` set used to construct that root.

## Regression shape

A useful regression should prove all of these:

- the unmodified fixture invokes the command but omits its provider;
- the candidate adds the provider to the correct root construction;
- no hook, assertion, privilege mode or unrelated package changes;
- the historical failure signature names that missing command;
- a reduced behavioral run passes with the provider installed.

## Limits

Do not add broad packages merely to make a test pass. Verify the exact binary provider and scope the dependency to the fixture that executes it. When a command is deliberately expected to be part of the base contract, document and test that contract separately.

## Related records

- Issue #84
- Central investigation #53
- `investigations/mmdebstrap-dev-ptmx-bsdutils/README.md`
- Historical capture PR #82
