# Handoff — UV BusyBox relocatable `realpath`

Handoff date: 2026-08-02  
State: `INVESTIGATED — SOURCE WORK NOT STARTED`  
External contact authorized: `false`  
External contact made: `none`

## Exact issue

```text
canonical issue: astral-sh/uv#16209
current canonical source head checked during round:
79bbface771210df216b738e9bdc7df95e5a9e6b
controlled source branch: none
controlled source PR: none
```

## Established findings

- generated relocatable console scripts use `realpath -- "$0"` inside the `/bin/sh` trampoline;
- BusyBox `realpath` treats `--` as a filename and emits an error;
- the command can continue, making this primarily misleading stderr rather than a guaranteed execution failure;
- `realpath` was added to fix symlinked relocatable entrypoints, so deleting path resolution is a regression;
- relocatable activation paths use the same command form and require review in the same source unit;
- a focused BusyBox shell matrix found that omitting only the `realpath` delimiter preserved direct, relative, space, symlink, and leading-dash cases.

## First incomplete step

Search current canonical pull requests and commits for equivalent work. If the lane is free, create a controlled branch from an exact canonical commit and add a failing Alpine/BusyBox integration test that also retains the historical symlink control.

## Required evidence before source acceptance

- current BusyBox reproduction through UV-generated output;
- exact baseline stderr and exit status;
- candidate clean stderr and correct exit status;
- symlinked console entrypoint still resolves the original environment;
- moved environment works;
- spaces and leading-dash path components work;
- activation and console-script behavior both classified;
- conventional Linux and macOS behavior reviewed;
- no broad shell-template rewrite without distinguishing evidence.

## Publication boundary

No upstream interaction is authorized. Keep all source and execution carriers on controlled forks until overlap, policy, and exact test results are reviewed.
