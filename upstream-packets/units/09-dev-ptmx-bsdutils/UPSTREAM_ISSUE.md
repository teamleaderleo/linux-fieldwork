# Upstream issue draft

## Disposition

A separate upstream issue adds little value because the source correction is one line, the owner is exact, and the pull-request draft contains the complete explanation and validation. Prefer a direct pull request after authorization and completion of the current-head gates.

If maintainers request an issue first, use this draft.

## Title

tests/dev-ptmx relies on bsdutils being Essential

## Body

The `dev-ptmx` package test invokes `script(1)` twice inside the generated apt-variant root while its explicit include set contains only `gcc,libc6-dev,python3,passwd`.

Debian's `bsdutils` package provides `/usr/bin/script`. After `bsdutils` stopped being Essential, the generated root no longer received that command implicitly and the test failed at:

```text
chroot "$1" script -c "echo foobar"
chroot: failed to run command ‘script’: No such file or directory
```

The direct correction is to add `bsdutils` to the existing include set. This changes the test dependency only and leaves runtime behavior and hook order untouched.

A focused patch and regression evidence are ready. External submission remains pending authorization.
