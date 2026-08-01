# Deep dive

## Mechanism

`tests/dev-ptmx` wraps the generated mmdebstrap invocation with host-side `script -qfec` to supply a pseudo-terminal. Inside the generated root, two customize hooks invoke `script(1)` again:

1. as root: `chroot "$1" script -c "echo foobar"`;
2. as the generated user: `chroot "$1" runuser -u user -- env --chdir=/home/user script -c "echo foobar"`.

The host-side `script` comes from the autopkgtest testbed. The two inner calls depend on packages selected into the generated apt-variant root.

The baseline include set is:

```text
gcc,libc6-dev,python3,passwd
```

`bsdutils` supplies `/usr/bin/script`. While `bsdutils` was Essential, the apt variant received it implicitly. In Debian testing with `bsdutils 1:2.42.2-1`, that implicit guarantee disappeared. The test fixture then failed before its intended PTY assertions could complete.

## Why the dependency belongs in the test

The test deliberately runs `script` inside the root. Explicitly naming the provider beside the existing root dependencies keeps the fixture independent from changes in Debian's Essential set. The correction expresses the command-level requirement where the root is constructed.

## Candidate properties

- adds exactly one package name;
- preserves the existing package order after the new provider;
- preserves all customize hooks and their order;
- changes no product runtime code;
- changes no Debian package metadata;
- changes no host-side testbed dependency;
- remains valid whether `bsdutils` is Essential or ordinary.

## Approaches rejected

### Change util-linux packaging

Rejected. The test owns an undeclared command dependency. Restoring Essential status would broaden the intervention far beyond this fixture and would leave the test coupled to implicit package-set composition.

### Replace `script` with another PTY helper

Rejected. The case intentionally exercises PTY behavior through `script`; replacing it would alter the test's behavior and obscure the missing-provider defect.

### Install `bsdutils` in the autopkgtest control dependencies only

Rejected. Host-side availability already existed. The missing binary was inside the generated root, so the package belongs in the mmdebstrap `--include` set.

### Add a runtime dependency to mmdebstrap

Rejected. mmdebstrap itself does not require `script` for ordinary operation. The dependency belongs solely to this test fixture.

### Fold current-sid harness defects into this patch

Rejected. PR `#72` found independent phase-order, wrapper, signal, and observability issues. Combining them would lose the one-line ownership boundary proven by the historical transcript.

## Compatibility analysis

The package name `bsdutils` is stable across the reviewed Debian releases and remains the direct provider recorded for `/usr/bin/script`. Adding it explicitly is harmless on releases where it remains Essential because apt deduplicates package selection. On releases where it is ordinary, the root gains the required binary.

The candidate should apply to the current upstream `tests/dev-ptmx` as long as the include declaration and hook sequence remain as observed. Exact application to upstream head `77ec9be5417ee44c96343d2347145585da1b1f94` remains an execution gate because this environment could read the official repository page but could not resolve its Git hostname for a raw checkout.

## Open discriminators

1. Does the upstream-path patch apply to exact head `77ec9be5417ee44c96343d2347145585da1b1f94` with zero fuzz and zero offset?
2. Does the named current-sid case pass after the candidate?
3. Does an immediate rerun pass after cleanup?
4. Has an equivalent upstream change landed outside the indexed page or after the advertised head?

A positive exact application and named-case pass would move the unit to `READY FOR AUTHORIZATION`. An equivalent upstream change would retire the submission while preserving the historical evidence.
