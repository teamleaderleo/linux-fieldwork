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

## Controlled GitHub carrier provenance

The user-controlled repository `teamleaderleo/mmdebstrap` is a GitHub fork of `deepin-community/mmdebstrap`, not a mirror of canonical Forgejo ancestry. Both repositories identify `master` head `574048f2a720057b75e56622003932f344dc700a` with subject `feat: update mmdebstrap to 1.5.7-3`.

Its `tests/dev-ptmx` blob is `ca1cde040f945fe871f904ef6a56e040b6a5c9ea`, byte-identical to the Linux Fieldwork import. This creates a strong implementation carrier for the Debian `1.5.7-3` source generation. The controlled candidate branch changes that file to blob `fa93b4b845ff4927a72f258364bd920e8c7dc573` at commit `43082a6bc959e2d7cefae48f52e045cc90869287`.

The carrier proves exact application to the source generation that produced the historical Debian failure and remains relevant because Debian sid still carries source package `1.5.7-3`. It does not prove current canonical ancestry or the presence of patches delivered through Forgejo, Salsa, Debian packaging, or mailing-list review.

## Mailing-list and canonical-main freshness risk

The one-line dependency correction has a narrow overlap surface, yet final delivery still needs a canonical fetch. Later work may have:

- changed the include declaration or hook sequence;
- added `bsdutils` equivalently;
- renamed or retired the case;
- carried adjacent test fixes through a mailing list or Debian patch series without appearing in the Deepin GitHub history.

The response to drift is deterministic:

- equivalent correction present: retire external submission and retain historical evidence;
- surrounding edits with the dependency still absent: rebase the one-line change and rerun static and dynamic gates;
- changed test intent or command provider: reopen ownership analysis before proposing code.

## Packet-carrier validation failure and repair

The first internal PR `#402` run reached the repository's changed-patch validator and rejected the retained email-style patch before tests:

```text
invalid hunk-body prefix '2'
hunk count mismatch: declared old/new 8/8, observed 8/7
```

The source candidate was unaffected. The retained patch declared eight hunk lines while carrying seven and included an email trailer that the validator then read as hunk content. The packet carrier was replaced with the exact pure unified diff from controlled-fork commit `43082a6bc959e2d7cefae48f52e045cc90869287`, using a `7/7` hunk and no trailer.

This red run classifies as a packet-format defect with zero package claim.

## Approaches rejected

### Change util-linux packaging

Rejected. The test owns an undeclared command dependency. Restoring Essential status would broaden the intervention far beyond this fixture and would leave the test coupled to implicit package-set composition.

### Replace `script` with another PTY helper

Rejected. The case intentionally exercises PTY behavior through `script`; replacing it would alter the test's behavior and obscure the missing-provider defect.

### Install `bsdutils` in the autopkgtest control dependencies only

Rejected. Host-side availability already existed. The missing binary was inside the generated root, so the package belongs in the mmdebstrap `--include` set.

### Add a runtime dependency to mmdebstrap

Rejected. mmdebstrap itself does not require `script` for ordinary operation. The dependency belongs solely to this test fixture.

### Treat the Deepin GitHub history as canonical upstream

Rejected. Its exact source bytes are useful for Debian `1.5.7-3` execution, while its ancestry and branch identity differ from canonical Forgejo `main`.

### Fold current-sid harness defects into this patch

Rejected. PR `#72` found independent phase-order, wrapper, signal, and observability issues. Combining them would lose the one-line ownership boundary proven by the historical transcript.

## Compatibility analysis

The package name `bsdutils` is stable across the reviewed Debian releases and remains the direct provider recorded for `/usr/bin/script`. Adding it explicitly is harmless on releases where it remains Essential because apt deduplicates package selection. On releases where it is ordinary, the root gains the required binary.

The candidate applies exactly to the imported and controlled downstream source blob. Exact application to canonical upstream head `77ec9be5417ee44c96343d2347145585da1b1f94`, or a fresher verified head, remains an execution gate because this environment can read the official repository page but cannot resolve its Git hostname for a raw checkout.

## Open discriminators

1. Does the corrected packet regression pass on the final exact Linux Fieldwork head?
2. Does the upstream-path patch apply to verified canonical `main` with zero fuzz and zero offset after overlap review?
3. Does the named current-sid case pass after the candidate?
4. Does an immediate rerun pass after cleanup?
5. Has an equivalent canonical or mailing-list-carried change already landed?

A green packet regression, positive canonical application, and named-case run/rerun would move the unit to `READY FOR AUTHORIZATION`. An equivalent canonical change would retire the submission while preserving the historical evidence and downstream execution receipt.
