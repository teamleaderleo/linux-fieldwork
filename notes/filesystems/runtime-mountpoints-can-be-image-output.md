# Runtime mountpoints can become image output

## In simple words

A container runtime may create a directory only because it needs a place to attach a mount. In a build system, that directory can survive after the container exits and become part of the exported image layer. Once exported content is content-addressed, even an empty directory can affect the layer digest and become compatibility-sensitive behavior.

BuildKit's rootful/rootless `/sys` divergence is a concrete example. Rootful runc receives the `/sys` mount and can create an absent lower-root `/sys` mountpoint. BuildKit's rootless spec conversion removes `/sys`, so rootless runc has no reason to create the path. The final rootfs member set can therefore differ even when the build command itself did nothing relevant to `/sys`.

## What I learned

### A mountpoint has at least three lifetimes

Keep these separate when reading container/build code:

1. **image lifetime** — does the input rootfs already contain the directory?
2. **execution lifetime** — does the runtime need the directory while attaching a mount?
3. **output lifetime** — does the directory remain in the committed snapshot after the mount disappears?

A path can exist only for execution and still leak into output lifetime.

### Runtime setup can be part of build semantics

For an ordinary container runtime, an empty lower-root mountpoint may feel like implementation residue. For a build engine, every retained member can become image data.

Example:

```text
input rootfs: no /sys

rootful exec:
  OCI spec includes /sys
  -> runtime creates lower-root /sys
  -> mounts sysfs there
  -> container exits
  -> mount disappears
  -> empty lower-root sys/ remains

rootless exec:
  rootless conversion removes /sys from OCI spec
  -> runtime never needs the mountpoint
  -> no lower-root sys/ is created
```

If those snapshots are exported as layers, the member lists differ.

### Content identity makes tiny filesystem differences consequential

An empty directory contributes archive metadata and a member name. If one layer contains `sys/` and another omits it, their uncompressed layer byte streams differ and so do their diff IDs.

That can affect exact image identity, reproducibility comparisons, compatibility goldens, signatures and attestations tied to digests, and exported cache or registry artifacts whose identity derives from content.

This does not mean every application cares about the empty directory at runtime. It means the build system's output contract can care about it.

### Cleaning a temporary path can still be a compatibility change

A cleanup helper may correctly identify that a directory was created solely for a runtime mount and can safely remove it. That proves cleanup ownership. It does not prove project policy wants the historical artifact removed from exported output.

Ask two questions separately:

1. **Can we safely remove this runtime-created path?**
2. **Should existing builds stop producing this path?**

The first is a mechanism question. The second is a compatibility question.

### Final-tree parity can hide execution-time differences

Suppose rootless execution omits `/sys`. Pre-creating an ordinary `/sys` directory before running the build would make it easy to leave the desired directory in the final tree.

It would also expose a writable ordinary directory to the build command. Rootful execution instead sees `/sys` as a read-only mounted filesystem. A rootless compatibility fix therefore has to preserve both command-time behavior and final-output behavior.

When fixing parity bugs, compare both:

- what the process can observe and modify while it runs;
- what the committed snapshot contains afterward.

### Nested mount destinations require mount-namespace reasoning

If a spec contains `/sys` and `/sys/fs/cgroup`, the runtime normally creates the nested cgroup mountpoint inside the mounted `/sys` filesystem. That nested directory does not become a lower-root artifact.

A post-exit recreation helper therefore cannot blindly create every removed destination in the rootfs. It must distinguish top-level lower-root mountpoints from paths that would have existed only inside another mount.

## Example from BuildKit

Canonical investigation: `../../investigations/buildkit-rootless-mountpoint-compatibility/README.md`

Related upstream records:

- issue: https://redirect.github.com/moby/buildkit/issues/6686
- original candidate: https://redirect.github.com/moby/buildkit/pull/7033
- replacement candidate: https://redirect.github.com/moby/buildkit/pull/7039

The retained result is:

```text
same LLB
  rootful -> proc/ + sys/
  rootless -> proc/
```

The original candidate made both sides omit runtime-created stubs. The upstream replacement preserves historical rootful output and recreates rootless-removed mountpoints after successful execution.

## Limits

This lesson is about build systems that commit or export filesystem state after container execution. It does not imply that every runtime-created mountpoint survives every snapshotter, executor, runtime, or cleanup path.

The exact BuildKit execution evidence retained in Linux Fieldwork covers matching rootful/rootless runc workers with the native snapshotter. The upstream replacement also addresses containerd executor code, but this note does not claim independent live containerd-worker execution.

## Related work

- Related investigation: `../../investigations/buildkit-rootless-mountpoint-compatibility/README.md`
- Internal carrier: `teamleaderleo/linux-fieldwork#229`
- Reusable review guide: `../../FIELD_GUIDE.md`
