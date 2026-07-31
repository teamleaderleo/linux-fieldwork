# Hosted temp HOME containment repair

Date: 2026-07-31  
Owning issue: #130  
Carrier: PR #250  
External contact authorized: `false`

## TL;DR

The reusable chrootless harness accepts `/home/runner/work/_temp` as a trusted disposable parent even though that directory normally sits below `/home/runner`.

The first repair skipped every HOME-overlap check for that hosted family. A caller could therefore override HOME to the exact derived runtime or a descendant of it, and later recursive cleanup would erase HOME.

The current candidate keeps the normal hosted relationship valid while rejecting a HOME equal to or below:

```text
/home/runner/work/_temp/mmdebstrap-chrootless-env
```

## Exact policy

For `/tmp` and `/var/tmp` families, the candidate continues to reject:

- parent inside HOME;
- runtime inside HOME;
- runtime equal to or containing HOME.

For `/home/runner/work/_temp`, the candidate deliberately permits the normal runtime-below-`/home/runner` relationship. It still rejects runtime equal to or containing HOME.

This preserves the hosted runner path without allowing an overridden HOME to become the deletion target.

## Distinguishing controls

The focused regression now requires:

- parent `/home/runner/work/_temp` plus HOME `/home/runner` → accepted;
- HOME equal to the derived runtime → rejected;
- HOME below the derived runtime → rejected;
- zero-fuzz exact patch application;
- complete shell syntax;
- the existing repository, home, source-copy, mode, content, and Git-state controls.

## Evidence boundary

This is a pathname-authority check before execution. It does not close a hostile rename or symlink race after validation, prove non-GNU tooling, or widen the accepted parent families.

## Disposition

`REPAIR COMPLETE — EXECUTE` on the resulting exact head. Prior runs on `f58fe100...` do not validate this hosted-HOME boundary.
