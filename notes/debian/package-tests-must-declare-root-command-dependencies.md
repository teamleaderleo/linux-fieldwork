# Package tests must declare commands used inside generated roots

## Principle

A package test that creates a root filesystem and then runs a command inside it must request the package providing that command unless the test explicitly targets a policy-guaranteed base set.

Do not treat the current Essential set as an undocumented dependency list. Essential membership and package splits can change during distribution transitions while the command name and test logic remain unchanged.

## Separate execution environments

Distinguish commands by where they run:

- **testbed commands** run outside the generated root and are supplied by autopkgtest dependencies or the host image;
- **generated-root commands** run through `chroot`, `systemd-nspawn`, a namespace wrapper, or an equivalent root selector and must be present in that root's package set.

The same command can appear in both environments and require two different dependency declarations.

## Review method

1. Inventory commands executed after each root-selection boundary.
2. Resolve each command to its providing package.
3. Compare that package list with the root-construction include set.
4. Treat incidental presence through Essential, Priority, or transitive dependencies as unstable unless the test is specifically verifying that policy.
5. Retain a negative control from a package-universe transition when available.

Useful checks include:

```sh
dpkg-query -S /usr/bin/script
apt-file search /usr/bin/script
```

## mmdebstrap dev-ptmx example

`tests/dev-ptmx` runs `script` once in the autopkgtest testbed and twice inside the generated apt-variant root. The outer command was available, but the inner commands disappeared when `bsdutils` stopped being Essential. Explicitly including `bsdutils` repairs the test without changing mmdebstrap runtime behavior.

## Validation

A focused regression should prove that:

- every generated-root command has an explicit provider in the root package set;
- unrelated package selections and hook order remain unchanged;
- the named test still passes against a current package universe;
- historical failure ownership remains separate from current validation.
