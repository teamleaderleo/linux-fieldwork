# uutils coreutils Target Map

## In simple words

uutils coreutils reimplements familiar GNU command-line utilities in Rust. It is a recurring Linux Fieldwork target because small file, process, signal, and metadata decisions in commands such as `cp`, `install`, `cat`, `rm`, and `yes` can affect scripts throughout an operating system.

The central research challenge is not merely finding output mismatches. It is identifying the operation owner and commitment boundary: which pathname or file descriptor represents the object, when a replacement becomes committed, what state survives a failure, and which later operand is allowed to act.

## Source identity

- Canonical repository: `https://github.com/uutils/coreutils.git`
- Canonical default branch: `main`
- Controlled fork: `https://github.com/teamleaderleo/coreutils.git`
- Latest canonical revision recorded while creating this map: `a0cb02453f314bdd3addda6f321f7e03adceb56b`
- Local imported source: none
- Source boundary: exact Git commit and blob identities in each investigation

The controlled fork's default branch has lagged canonical main during this work. Clean comparison base branches are created at exact canonical heads rather than treating fork `main` as authoritative.

## Why it recurs

The project contains dozens of utilities and shared libraries covering:

- file replacement, backups, sparse files, permissions, timestamps, xattrs, ACLs, links, and directory traversal;
- pipes, signals, standard streams, subprocesses, file descriptors, and resource limits;
- compatibility with current GNU executable behavior across Linux, BSDs, macOS, Windows, Android, WASI, and other targets;
- performance paths such as `splice`, reflinks, sparse writes, and bulk buffered I/O;
- localization, embeddability, fuzzing, and differential test infrastructure.

A defect in a small utility can become a package-build failure, infinite loop, data-loss edge, security race, or diagnostic incompatibility in many downstream scripts.

## Project contract

The governing contribution rules include:

- GNU executable behavior and documentation may be used as compatibility oracles;
- GNU source code must not be read, linked, copied, or used to derive an implementation;
- changes should remain small, focused, idiomatic, cross-platform, and understandable line by line;
- paths should remain `Path`/`OsStr` rather than assuming UTF-8;
- unexpected panics and direct process exits should be avoided;
- new behavior requires tests;
- rustfmt, clippy, and the relevant test suites are merge gates;
- a canonical solution discussion is expected before an upstream PR.

Linux Fieldwork records black-box behavior, public uutils source and history, and controlled-fork candidates. It authorizes no upstream interaction by itself.

## Relevant programmes

- [`Filesystems, archives, and disk images`](../../programmes/filesystems-images/STATUS.md)
- [`Services, processes, and resources`](../../programmes/services-resources/STATUS.md)
- [`Security and networking boundaries`](../../programmes/security-networking/STATUS.md)

## Active investigations

- [`install` just-created destination ownership](../../investigations/coreutils-install-just-created-12926/README.md)
- [`install` backup rollback after data-copy failure](../../investigations/coreutils-install-backup-rollback/README.md)
- [`cp --sparse=always` early EOF](../../investigations/coreutils-cp-sparse-early-eof-12648/README.md)

A controlled `cat` descriptor-classification candidate is also being validated against issue `#13042`; add its investigation link here when the durable record lands.

## Reusable notes

- [`install` replacement state machines](../../notes/filesystems/coreutils-install-state-machines.md)
- [`cp` sparse-copy early EOF](../../notes/filesystems/coreutils-sparse-copy-early-eof.md)

## Source and test surfaces

Begin with:

- `src/uu/<utility>/src/` for utility behavior;
- `src/uucore/src/lib/features/` for shared backup, copy, traversal, mode, and parser machinery;
- `tests/by-util/` for integration behavior;
- utility-local unit tests for deterministic internal transitions;
- `util/run-gnu-test.sh` and the GNU comparison CI for compatibility;
- recent commits and active PRs touching the same lifecycle boundary.

For filesystem work, sample the full operation chain: classify/open, backup/remove, create/write, finalize metadata, report output, cleanup, and later operands. For process work, sample normal output, closed descriptors, broken pipes, signals, and resource exhaustion.

## Selection discipline

Do not select work from the open issue list alone. Before starting a candidate:

1. verify the defect against current canonical main source;
2. search active and historical PRs;
3. read issue comments for explicit implementation claims;
4. distinguish stale-open issues from genuinely live code;
5. compare exact branch ancestry and file overlap;
6. define a deterministic test that observes the operation boundary rather than a coincidental symptom.

Existing examples:

- several TOCTOU issues remained open after their fixes merged;
- `yes >&-` is live but already has an active reviewed PR;
- the `install` special-file defect has a contributor claim;
- the `cp` sparse early-EOF issue was open, live in current source, and had no matching PR at selection time.

## Review heuristics

Ask these questions before enlarging a patch:

- Is the owner the pathname, an opened descriptor, one operand, or the whole invocation?
- What event commits the operation?
- Does a failed operation leave old data, partial new data, or no entry?
- Is cleanup acting on the same object that was created or merely the same path spelling?
- Does a fast path preserve the slow path's failure semantics?
- Does the test prove the transition without relying on a scheduler race?
- Does another open PR already move the same boundary?
- Are platform-specific differences explicit and fenced?

## Current controlled-fork carriers

At the map's initial revision:

- draft PR `teamleaderleo/coreutils#1` — `install` destination ownership;
- draft PR `teamleaderleo/coreutils#3` — `install` backup rollback;
- draft PR `teamleaderleo/coreutils#4` — `cp` sparse early EOF;
- draft PR `teamleaderleo/coreutils#5` — `cat` descriptor classification;
- closed PR `teamleaderleo/coreutils#2` — retired provenance superseded by an older, more complete upstream PR.

These are controlled validation surfaces, not canonical submissions.

## Policy boundary

No canonical uutils issue comment, pull request, review, email, patch submission, or maintainer contact is authorized by this map. Refresh exact canonical main, issue disposition, PR overlap, and controlled heads immediately before any external action.