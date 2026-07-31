# Run 926 carrier preflight failure

State: `classified — zero package evidence`

PR: #72  
Exact head: `3e375984d7ceabd7d64b33b5b502c8701ab0c4dc`  
Workflow: `30631980224` / 926

## Result

The contained Debian sid job stopped before `autopkgtest` execution. The repository validator and disposable reproduction independently exposed retained patch-carrier defects.

Repository `lab-tools` failed during changed-patch validation:

```text
sigint-process-group-kill-sid.patch: declared old/new 7/7, observed 6/6
sourcesfilter-deb822.patch: declared old/new 36/37, observed 34/35
```

The disposable job applied `installed-command-wrapper.patch` with two `offset -2` receipts, then failed applying the malformed Deb822 patch. It uploaded five preflight files and returned status 1.

Artifact:

- ID `8793706715`;
- ZIP digest `sha256:3c47b9e42b606c605506ae444d7ba8a6a70c37ccc116243f59734d6af2713edf`;
- five files;
- no package console log, package result, Packet B execution, or SIGINT execution.

## Classification

This run rejects the carrier. It says nothing about the Packet B candidate, mmdebstrap interruption behavior, or the dash builtin integration override.

## Repair

- correct the signal hunk to `-7,6 +7,6`;
- correct the Deb822 hunk to `-1,34 +1,35`;
- correct wrapper hunk positions to current imported source lines 138 and 173;
- apply the capability patch before the wrapper so both testsuite patches land at their declared positions;
- fail preflight on any `fuzz` or `offset` receipt;
- execute all four patches as one local composition control before another privileged package run.

## Reopening boundary

Only a fresh exact head whose repository tests and four-patch composition pass may produce new package evidence.

## Authority

Internal Linux Fieldwork evidence only. External contact authorized: false.
