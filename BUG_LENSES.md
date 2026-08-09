# High-value Linux bug lenses

## In simple words

The most useful Linux and Debian defects often appear when several individually reasonable components disagree about ownership, time, identity, cleanup, metadata, or authority. Use these lenses after source orientation to decide which invariants deserve a real probe.

This guide complements `FIELD_GUIDE.md`. It turns recurring defect classes into questions that can drive investigations.

## Start with the invariant

Write the property that must survive the complete operation.

Examples:

- interruption leaves no owned child process, mount, lock, socket, temporary tree, or partial package state behind;
- a cache or archive becomes visible only when its bytes and metadata are complete;
- path validation and the later destructive operation refer to the same resolved object;
- a package action performed with elevated authority remains confined to the intended root and mode;
- a signal preserves its identity through cleanup and final exit status;
- a retry cannot publish the same logical result twice;
- equivalent package or filesystem output preserves the compatibility properties consumers actually depend on.

Then ask: **what sequence could violate this property while every local command still looks plausible?**

## 1. Concurrency, ordering, and partial failure

High-yield Linux cases include:

- concurrent cache misses and final-name publication;
- lock acquisition, timeout, stale lock recovery, and owner death;
- signal arrival during wait, cleanup, rename, mount, extraction, or package-script execution;
- retry after a child succeeded but before the parent recorded success;
- service or socket creation being treated as readiness;
- producer EOF being treated as completeness;
- cleanup racing a new invocation.

Useful probes inject delay, duplicate work, send signals between phases, kill an owner, truncate a stream, and immediately rerun.

## 2. Process and resource lifecycle

Model processes, subprocesses, descriptors, sockets, mounts, namespaces, temporary directories, services, and traps as owned resources with explicit birth and death conditions.

Ask:

- which process owns cleanup;
- whether a child can outlive the parent unexpectedly;
- whether process-group behavior differs from single-PID behavior;
- whether EXIT and signal traps can re-enter cleanup;
- whether cleanup failure changes the primary result;
- whether a second invocation inherits stale files, sockets, locks, mounts, environment, or service state;
- whether setup can fail after allocating only part of the resource set.

Repeated execution after interruption is one of the strongest lifecycle probes.

## 3. Filesystem and package data integrity

Check more than file contents.

Trace:

- atomic rename and visibility;
- final mode, owner, group, ACLs, xattrs, timestamps, link type, sparse extents, and allocation;
- archive member names, type flags, PAX metadata, ordering, hard links, symlinks, and extraction semantics;
- package database state versus filesystem state;
- partial writes, short reads, truncation, and durability;
- migration or format-version assumptions;
- derived indexes, caches, manifests, checksums, and metadata that may disagree with primary content.

A good integrity test compares independent representations of the same result and explains which representation consumers actually trust.

## 4. Paths, identity, privilege, and authority

Linux gives tiny strings enormous authority. Treat path and identity transformations as security-relevant boundaries.

Ask:

- whether normalization, decoding, symlink resolution, bind mounts, namespaces, `..`, or alternate roots change the object after validation;
- whether UID/GID, user names, groups, capabilities, namespaces, or fakeroot state are interpreted consistently;
- whether validation happens before an authority-changing step and use happens after it;
- whether a helper, maintainer script, hook, wrapper, or service runs with broader authority than its caller assumes;
- whether environment sanitization removes required normalized state or preserves attacker-controlled state;
- whether a checked path and a later `rm`, `chmod`, extraction, open, mount, or exec still name the same object.

Identify the exact operation owner and authority boundary before widening a patch.

## 5. Cross-layer contract drift

Trace one operation through shell or CLI → wrapper → process tree → kernel/filesystem/network primitive → package or service state → reported result.

Compare each layer's idea of:

- success and failure;
- readiness and completion;
- signal identity;
- ownership;
- path identity;
- bytes versus metadata;
- retry safety;
- environment inheritance;
- privilege;
- durable publication.

Many Linux bugs live between layers that are each internally coherent.

## 6. Nonlinear performance and resource collapse

Look for load-dependent failures where cost compounds:

- fork or process fan-out;
- descriptor or socket growth;
- lock contention;
- repeated directory scans;
- quadratic package or manifest operations;
- retry amplification;
- unbounded queues or buffered output;
- cache stampedes;
- temporary-disk or inode exhaustion;
- work serialized through one namespace, lock, service, or database.

Measure increasing input size, concurrency, file count, process count, or retry count. Name the resource that saturates and the variable driving it.

## 7. Specification and semantic disagreement

Compare source behavior with the contracts carried by:

- command help and man pages;
- Debian policy and package metadata;
- configuration schemas;
- test suites;
- exit-status conventions;
- archive or protocol specifications;
- service-manager expectations;
- real downstream scripts and package consumers.

When these disagree, identify the intended invariant first. A passing test can preserve an obsolete or incomplete contract.

## Predict where defects will cluster

Give extra attention to code where several conditions meet:

1. more than one process or component appears to own state;
2. correctness spans setup, execution, cleanup, and rerun;
3. paths or identities are transformed before a privileged operation;
4. bytes and metadata can diverge;
5. a wrapper translates signals, exit status, environment, or argv;
6. retries or interruption occur near publication;
7. package state is mirrored across filesystem, database, cache, or generated metadata;
8. correctness changes with namespace, privilege, distribution mode, or chrootless execution;
9. tests check headline output while lifecycle or compatibility properties remain implicit.

These are strong investigation candidates because a small command or helper may carry a much larger system contract.

## Turn a lens into an investigation

Record:

1. **Invariant** — what must stay true.
2. **Operation owner** — process, wrapper, package tool, kernel primitive, service, or caller responsible for it.
3. **Authority boundary** — user, root, capability, namespace, filesystem root, service account, or remote peer involved.
4. **Failure sequence** — the smallest ordering or input that could violate the invariant.
5. **Distinguishing probe** — exact command or fixture with multiple plausible outcomes.
6. **Negative control** — proof the probe can recognize correct behavior.
7. **Surviving state** — processes, files, modes, mounts, sockets, locks, package records, environment, or metadata left behind.
8. **Clean rerun** — immediate repeat after the failure path.
9. **Repair boundary** — the smallest owner that can enforce the invariant.
10. **Evidence limit and reopen trigger** — what remains outside the claim and what new fact would require another experiment.

The useful end state is precise: this invariant fails under this sequence, at this owner and authority boundary, with these surviving consequences.