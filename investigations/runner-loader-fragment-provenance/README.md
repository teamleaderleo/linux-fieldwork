# GitHub-hosted Ubuntu loader-fragment provenance

## TL;DR

Linux Fieldwork issue #501 already established that the public Ubuntu runner-image apt table is curated rather than a complete `dpkg` inventory. The remaining question is package provenance: on fresh hosted images, which installed package owns each dynamic-loader configuration fragment, why is `libc6-i386` installed on x86_64 when present, and does ARM64 differ cleanly?

This record runs observation-only package queries on two fresh x86_64 jobs and one ARM64 job. It installs and removes nothing.

## Bounded question

For each fresh job, retain:

- hosted image identity and architecture;
- installed/manual/automatic state for `libc6-i386`, `libc6`, `fakeroot`, and relevant Clang runtime packages;
- installed reverse dependencies of `libc6-i386`;
- apt dependency trees for the Clang runtime packages that were removed with `libc6-i386` in the earlier SmolRunner job;
- every `/etc/ld.so.conf.d/*` filename, content digest, content, and owning package when one exists.

## Expected outcomes

- **Mapped behavior:** `libc6-i386` is automatic/transitive and its dependency chain is attributable to the preinstalled toolchain; the README omission remains expected because its apt table is curated.
- **Reopen image-composition question:** `libc6-i386` is manual, unowned by the expected provisioning chain, or current x86 jobs disagree about its presence/provenance.
- **Architecture boundary:** ARM64 lacks the x86 biarch package/fragment while retaining ordinary architecture-specific loader configuration.

## Evidence boundary

The probe observes the exact hosted images selected for its workflow run. Hosted images roll over time, so image version is part of every conclusion. No `apt-get install`, purge, package configuration, loader-cache regeneration, or host mutation is performed.

## Authority

Internal Linux Fieldwork only. No `actions/runner-images` issue, pull request, comment, review, email, or other external contact is authorized.
