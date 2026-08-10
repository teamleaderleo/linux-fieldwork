# shadow usermod --prefix numeric-GID ownership regression

## TL;DR

At `shadow-maint/shadow` commit `e4bd855661afe7c83ad2745d086a538398205225`, `prefix_getgr_nam_gid()` has two different ownership behaviors under `--prefix`:

- a group **name** is looked up with `prefix_getgrnam()` and then deep-copied with `__gr_dup()`;
- a **numeric GID** is returned directly from `prefix_getgrgid()`, whose prefix implementation returns the `struct group *` produced by `fgetgrent()`.

Current `usermod` treats both results as owned and calls `gr_free()` on them. On glibc 2.41, `fgetgrent()` reused libc-managed storage, and applying Shadow's `gr_free()` ownership contract to the numeric result aborted with `SIGABRT` / `free(): invalid pointer`. A reduced fixture modeled from the current source gives a clean differential: the named lookup exits 0; the numeric lookup aborts.

This is a recurrence of a defect class Shadow has fixed before. Issue 110 (2018) reported `usermod --prefix` invalid-pointer crashes and led to commit `73a876a05612c278da747faeaeea40c3b8d34a53`, whose stated purpose was to return newly allocated pointers when callers free them. That fix duplicated the name path but left the numeric GID path returning `prefix_getgrgid()` directly. Issue 394 (2021) later reported the same `fgetgrent()`/`gr_free()` ownership mismatch in `useradd`; the maintainer explicitly agreed that some returned values were not freeable and reverted the offending free.

The narrow candidate repair is to make `prefix_getgr_nam_gid()` honor the same owned-result contract for both name and numeric-GID inputs, most likely by duplicating the result of `prefix_getgrgid()` before returning it. Before proposing a source candidate, build the exact current Shadow head and execute `usermod -P <synthetic-prefix> -g 4242 <synthetic-user>` plus the `-G 4242` supplementary-group path against a disposable prefix tree.

## Explain like I'm five

`usermod` asks a helper for information about a group and later throws that information away with `gr_free()`.

When the group is written as `users`, the helper makes a private copy first, so throwing it away is correct.

When the same group is written as `4242`, the helper hands back libc's shared lookup buffer instead. `usermod` still tries to free it as if it owned it. On the tested glibc, that ends in `free(): invalid pointer`.

The two inputs identify the same group; only the spelling changes who owns the returned memory.

## Why care

`usermod --prefix` is intended to operate on passwd/group databases rooted somewhere other than the host `/etc`. Both `-g GROUP` and `-G GROUPS` accept names or numeric IDs. A numeric GID in prefix mode therefore reaches a different memory-ownership path than the equivalent group name and can turn a valid lookup into a process abort before the requested account update completes.

This is especially useful as a regression target because the project history already states the intended ownership rule: callers that free the result need a newly allocated pointer.

## Source boundary

### Shadow

- Project: `shadow-maint/shadow`
- Reviewed revision: `e4bd855661afe7c83ad2745d086a538398205225`
- Reviewed files:
  - `lib/prefix_flag.c`
  - `lib/groupmem.c`
  - `lib/getgr_nam_gid.c`
  - `lib/prototypes.h`
  - `src/usermod.c`
  - adjacent `src/useradd.c`
- Relevant history:
  - `73a876a05612c278da747faeaeea40c3b8d34a53` — `Fix usermod crash`; "Return newly allocated pointers when the caller will free them."
  - `48dcf7852e51b9d8e7926737cc7f7823978b7d7d` — follow-up null handling for the same usermod prefix fix
  - `bd2d0079c90241f24671a7946a3ad175dc1a3aeb` — changed `usermod --gid` to use `prefix_getgr_nam_gid()` so `--prefix` is respected
- Relevant closed issues:
  - https://github.com/shadow-maint/shadow/issues/110
  - https://github.com/shadow-maint/shadow/issues/394

### Local execution environment

- Kernel: Linux `6.18.35` x86_64
- libc: Debian glibc `2.41-12+deb13u3`
- Compiler: GCC 14.2.0
- Fixture: [`prefix_group_ownership_probe.c`](prefix_group_ownership_probe.c)
- Privileges: ordinary process/file operations only
- State: synthetic temporary group files under `/tmp`; no host account database modification

## Bounded question

Does `prefix_getgr_nam_gid()` return memory with one consistent ownership contract for group names and numeric GIDs, as required by current `usermod` callers that unconditionally call `gr_free()`?

## Invariant

If a helper's callers own and free its successful return value, every successful input form accepted by that helper must return independently owned storage or the ownership difference must be explicit at the call site.

Equivalent group identifiers should not switch between owned and borrowed storage merely because one is written as a name and the other as a number.

## Operation owners

- `prefix_getgrnam()` / `prefix_getgrgid()` own prefix-file lookup.
- `prefix_getgr_nam_gid()` owns conversion from name-or-number syntax into one returned `struct group *` contract.
- `__gr_dup()` creates the owned deep copy.
- `gr_free()` destroys an owned deep copy, including `gr_name`, `gr_passwd`, `gr_mem`, and the `struct group` itself.
- `usermod` owns the final caller decision to free the result.

## Current source observations

### 1. `gr_free()` is a deep owned-object destructor

`lib/groupmem.c` shows that `__gr_dup()` allocates a new `struct group`, duplicates `gr_name` and `gr_passwd`, allocates a new member vector, and duplicates every member string.

`gr_free()` performs the inverse: it frees the name, password, every member, the member vector, and finally the group structure itself.

This is not a generic release function for libc lookup storage; it requires the owned-copy contract produced by `__gr_dup()` (or an equivalent allocator).

### 2. The non-prefix name-or-GID helper returns owned storage

`lib/getgr_nam_gid.c` declares `getgr_nam_gid()` with the project's `/*@only@*/` ownership annotation and returns `xgetgrgid()` for numeric input or `xgetgrnam()` for a name.

That matches caller behavior that later passes the result to `gr_free()`.

### 3. Prefix name and numeric paths diverge

At the reviewed head, `prefix_getgrgid()` opens the prefixed group database, iterates with `fgetgrent()`, closes the stream, and returns the matched pointer directly.

`prefix_getgr_nam_gid()` then does:

```c
if (get_gid(grname, &gid) == 0)
    return prefix_getgrgid(gid);

g = prefix_getgrnam(grname);
return g ? __gr_dup(g) : NULL;
```

So under prefix mode:

- numeric GID -> direct `fgetgrent()` result;
- group name -> `fgetgrent()` result followed by `__gr_dup()`.

The successful return type is the same, but the ownership is different.

### 4. Current usermod frees both forms

`src/usermod.c::get_groups()` accepts a comma-separated mix of numerical and string group identifiers, obtains each with `prefix_getgr_nam_gid()`, copies the resolved name, and then unconditionally calls `gr_free(grp)`.

The `-g` primary-group option independently calls the same helper, stores `grp->gr_gid`, and unconditionally calls `gr_free(grp)`.

Therefore both `-g 4242` and a numeric entry in `-G ...` can reach the borrowed numeric-prefix result followed by the owned-object destructor.

## History pass

### 2018: usermod prefix invalid-free report

Shadow issue 110 reported an invalid-pointer abort in `usermod --prefix`. The reproduced stack ended in `gr_free()` inside `get_groups()`.

Commit `73a876a05612c278da747faeaeea40c3b8d34a53` closed that issue with the explicit message:

> Return newly allocated pointers when the caller will free them.

The code change wrapped the **name** path in `__gr_dup(prefix_getgrnam(...))`. It did not wrap the numeric `prefix_getgrgid()` return.

The follow-up commit `48dcf7852e51b9d8e7926737cc7f7823978b7d7d` made the name-path duplication null-safe but again left the numeric path unchanged.

### 2021: same ownership class in useradd

Shadow issue 394 reported `free(): invalid pointer` from `useradd` after a prefixed `GROUP=100` lookup. The report specifically identified `prefix_getgr_nam_gid()` returning an `fgetgrent()` value that should not be freed.

The maintainer response agreed that the helper can return a non-freeable value and chose to revert the newly introduced free in `useradd` rather than treat every returned pointer as owned.

This prior decision is strong intent evidence for the ownership boundary under review.

### 2023: primary usermod --gid moved onto the prefix helper

Commit `bd2d0079c90241f24671a7946a3ad175dc1a3aeb` changed `usermod -g` from `getgr_nam_gid()` to `prefix_getgr_nam_gid()` so `--prefix` would be honored.

The caller's later `gr_free()` remained. That made the helper's asymmetric ownership contract directly relevant to the primary numeric `-g` path as well as numeric supplementary groups.

## Executed probe 1: raw fgetgrent ownership

A disposable C probe wrote two entries to a temporary group file, called `fgetgrent()` twice, and printed the returned addresses.

Observed on glibc 2.41:

```text
first struct=0x... name=alpha gid=4242
second struct=0x... name=beta gid=4343
same_struct=1
```

The same `struct group` and backing buffer were reused for successive calls.

A forked child then applied the same deep-free pattern used by Shadow's `gr_free()`. The child terminated with signal 6 and glibc printed:

```text
free(): invalid pointer
```

This establishes the relevant libc ownership behavior on the execution environment without touching `/etc/group`.

## Executed probe 2: current helper ownership split

The checked-in fixture reduces the current Shadow helper behavior against one synthetic entry:

```text
users:x:4242:alice
```

It models:

- `prefix_getgrnam()` using `fgetgrent()`;
- `prefix_getgrgid()` using `fgetgrent()`;
- current `prefix_getgr_nam_gid()` behavior where the name path duplicates and the numeric path returns directly;
- current `gr_free()` deep-free semantics.

Command:

```sh
gcc -O0 -g -Wall -Wextra prefix_group_ownership_probe.c -o prefix_group_ownership_probe
./prefix_group_ownership_probe
```

Observed:

```text
arg=users resolved=users gid=4242 ptr=0x...
result arg=users exit=0
arg=4242 resolved=users gid=4242 ptr=0x...
free(): invalid pointer
result arg=4242 signal=6
```

The group identity and database are constant. Only name-vs-numeric syntax changes.

## Cross-context pass

### Prefix + symbolic name

**Discriminator:** helper executes the `__gr_dup()` branch.

Observed in the reduced fixture: cleanup exits 0.

This is the passing control.

### Prefix + numeric GID

**Discriminator:** helper returns `prefix_getgrgid()` directly.

Observed in the reduced fixture: Shadow-like cleanup aborts with `SIGABRT` / invalid pointer.

### No prefix

**Discriminator:** helper delegates to `getgr_nam_gid()`, which carries an owned-result annotation and uses `xgetgrgid()` / `xgetgrnam()`.

Source indicates this is the intended owned-result branch and explains why the caller's `gr_free()` was already valid before `usermod -g` was switched to the prefix-aware helper.

### usermod `-G`

**Discriminator:** repeated supplementary-group lookup and free.

Current source uses `prefix_getgr_nam_gid()` and frees each successful result. A numeric supplementary GID therefore has the same ownership hazard as primary `-g`.

### useradd

**Discriminator:** adjacent caller with different cleanup decisions.

Current `useradd` supplementary-group handling uses the local group database functions and explicitly duplicates before freeing, avoiding this exact branch. Its defaults handling also provides historical evidence that blindly freeing the prefix helper result was previously reverted.

## Candidate repair boundary

The strongest small boundary is `prefix_getgr_nam_gid()` itself because its non-prefix behavior and its historical usermod fix both imply an owned successful return.

A minimal candidate would make the numeric prefix path mirror the name prefix path conceptually:

```c
if (get_gid(grname, &gid) == 0) {
    g = prefix_getgrgid(gid);
    return g ? __gr_dup(g) : NULL;
}
```

Then both accepted input forms return storage compatible with `gr_free()`.

Do **not** change `prefix_getgrgid()` globally without auditing every direct caller; some callers may rely on its libc-style borrowed result. Fixing the name-or-GID adapter is a smaller compatibility surface.

## Next exact probe

Build Shadow exactly at `e4bd855661afe7c83ad2745d086a538398205225` and create a disposable prefix tree containing only synthetic passwd/group/shadow/gshadow/login.defs data needed by the command.

Run at least:

```text
usermod -P PREFIX -g users testuser
usermod -P PREFIX -g 4242 testuser
usermod -P PREFIX -G users testuser
usermod -P PREFIX -G 4242 testuser
```

Use the same `users:x:4242:...` group entry for all four cases.

Record:

- exit status and stderr;
- whether the command reaches database commit;
- whether the numeric path aborts before any write;
- AddressSanitizer or Valgrind result if the project build supports it;
- resulting passwd/group files;
- cleanup and immediate rerun.

A candidate fix should make all four cases reach equivalent group-resolution behavior while preserving the ordinary no-prefix path.

## Evidence boundary

Established:

- exact current source ownership split in `prefix_getgr_nam_gid()`;
- exact current `usermod` callers that unconditionally `gr_free()` successful results for `-g` and `-G`;
- exact current deep-free behavior of `gr_free()`;
- glibc 2.41 reuse of `fgetgrent()` storage in a synthetic file;
- invalid free / SIGABRT when that storage is passed through Shadow's deep-free contract in a forked child;
- a name-vs-numeric reduced differential with a passing name control and failing numeric case;
- prior Shadow issue/commit evidence that the same ownership class caused real `useradd`/`usermod --prefix` crashes and that owned copies are intended when callers free them;
- no matching currently open issue found using the searched terms;
- no upstream contact occurred.

Not established yet:

- execution of a `usermod` binary built from the exact reviewed 2026 head;
- the exact distribution/kernel/libc matrix beyond glibc 2.41;
- whether another libc implementation happens to allocate `fgetgrent()` results differently;
- whether a current upstream issue under different wording already tracks the numeric-only recurrence;
- a reviewed source patch or upstream-ready test.

## Disposition

**Promote to exact-current-binary reproduction.**

The source contract, reduced runtime probe, historical fixes, and caller audit are strong enough to retain this as a concrete regression candidate. The remaining gate is execution of the actual current `usermod` binary against a synthetic prefix tree before preparing any candidate patch.

## External-contact state

No upstream greenlight was given. No upstream issue, pull request, comment, review, email, reaction, or other external contact was created.
