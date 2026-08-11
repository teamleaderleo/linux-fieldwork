# kmod depmod truncated-index publication review

## TL;DR

Current `kmod-project/kmod` master at `65ac890492c96b88d10d8c92342a1b00ff603dba` writes each `depmod` index to a temporary file, records `ferror(fp) | fclose(fp)`, publishes the temporary file with `renameat()`, and only afterward checks whether stream finalization failed.

A safe local probe against installed kmod 34.2 reproduced the consequence: with an old `modules.dep` sentinel in a disposable `--outdir`, a synthetic `fclose()` `EIO` caused `depmod` to return failure but the old index had already been replaced by an empty generated index.

That initially resembles the cache-publication defects found elsewhere. History changes the disposition. A 2012 commit specifically added ENOSPC/truncation error reporting while retaining rename-before-error-check ordering, and the 2025 tmpfile-helper refactor preserved that sequence. The strongest conclusion is therefore **not** that the 2025 tmpfile work accidentally introduced a publication bug. The behavior is longstanding and has strong intent evidence as an error-signaling policy.

Retain this as a negative result for the accidental-regression hypothesis. A separate design question remains: should modern `depmod` preserve the previous complete indexes when new index generation reports a write/close error, or is publishing the failed generation preferable to leaving stale dependency metadata?

## Explain like I'm five

`depmod` rebuilds lookup files that tell module tools what kernel modules exist and depend on each other. It builds a new file off to the side, then swaps it into the official filename.

It can notice that writing or closing the new file failed. Surprisingly, it still performs the swap first and reports the error afterward.

That looks accidental until history is checked: the project has behaved this way for years, and an old fix explicitly focused on returning an error while keeping this ordering. So the right follow-up is a policy question, not an immediate code-fix claim.

## Why care

The distinction changes what survives an ENOSPC or delayed write failure:

- current policy: callers receive failure, but a newly generated truncated index may replace the previous index;
- preserve-old policy: callers receive failure and the previous complete index remains, but that index may be stale relative to newly installed or removed modules.

Both states have operational drawbacks. A source review cannot choose between them without project intent and consumer expectations.

## Source boundary

- Project: `kmod-project/kmod`
- Reviewed current revision: `65ac890492c96b88d10d8c92342a1b00ff603dba`
- Primary source: `tools/depmod.c`
- Temporary-file helper: `shared/tmpfile.c`
- Tests inspected: `testsuite/test-depmod.c`
- Key history:
  - `a4fb97a71e336394e1a497c2b75ea42907937d1e` — 2012 `depmod: return error when index is truncated due to ENOSPC`
  - `aae48bc9f73a1bce726871027f73cbc0543c65d4` — 2025 `depmod: add tmpfile-util to generate temporary file`
- Runtime model: installed kmod 34.2
- Upstream contact: **not authorized and not performed**

## Bounded question

Did the modern temporary-file publication path accidentally make `depmod` replace a prior index after output finalization has already reported failure?

## Initial invariant hypothesis

A plausible generic publication invariant was:

> If writing or closing a replacement index fails, the temporary file should be discarded and the previous published index should remain.

The investigation deliberately searched for evidence that this invariant is wrong for `depmod` before promoting a defect claim.

## Current source observation

At the reviewed head, each generated index follows this sequence:

```c
r = itr->cb(depmod, fp);
if (fp == out)
    continue;

ferr = ferror(fp) | fclose(fp);

if (r < 0) {
    tmpfile_release(&file);
    ...
    break;
}

err = tmpfile_publish(&file, itr->name);
if (err != 0) {
    ...
    break;
}

if (ferr) {
    err = -ENOSPC;
    ERR("Could not create index '%s'. Output is truncated: %s\n",
        itr->name, strerror(-err));
    break;
}
```

`tmpfile_publish()` is a same-directory `renameat()` from the temporary name to the final index name. Once publication succeeds, the helper clears its temporary-file identity.

The code therefore distinguishes callback failure (`r < 0`) from stream finalization failure (`ferr`): callback failure releases the temp before publication; stream failure is reported after publication.

## Why the initial bug hypothesis loses

### 1. The ordering predates the 2025 tmpfile helper

The 2025 commit that introduced the shared tmpfile utility replaced hand-written temp naming and `renameat()` calls while preserving the existing sequence around:

```c
ferr = ferror(fp) | fclose(fp);
...
rename/publish
...
if (ferr) ...
```

So the modern helper did not create the publish-before-finalization-error behavior.

### 2. The 2012 ENOSPC fix specifically chose error reporting, not old-index preservation

Commit `a4fb97a71e336394e1a497c2b75ea42907937d1e` is titled:

```text
depmod: return error when index is truncated due to ENOSPC
```

Its motivating example shows `depmod` previously returning `0` while generated module indexes were truncated or empty. The fix changes the command to report an error and return `1`.

The patch records output state, closes the file, performs the existing rename, and checks truncation afterward. In other words, the historical fix addressed **error signaling** while retaining publication of the generated result.

That is strong evidence against describing current ordering as an accidental omission discovered only now.

### 3. The 2025 refactor preserved the historical decision

The tmpfile refactor changed implementation mechanics but kept publication before `ferr` handling. This second preservation point makes an accidental one-off ordering mistake less plausible.

## Runtime probe

The local runtime has:

```text
kmod version 34.2
+ZSTD +XZ -ZLIB +OPENSSL
```

`depmod` supports separate input and output roots, so the test used only disposable state:

```text
/tmp/kmod-depmod-probe/root/lib/modules/6.0.0-test
/tmp/kmod-depmod-probe/out-fail2/lib/modules/6.0.0-test
```

No host `/lib/modules` file was changed.

### Passing control

An empty fake module tree with a pre-existing sentinel index was generated normally:

```sh
printf 'OLD-SENTINEL\n' > out/lib/modules/6.0.0-test/modules.dep
depmod -b root -o out 6.0.0-test
```

Observed:

```text
exit: 0
modules.dep: 0 bytes
```

The normal run replaces the sentinel as expected because the fake module tree has no modules.

### Synthetic close-error probe

An `LD_PRELOAD` shim targeted the first output temporary file under the disposable output directory. It allowed the real `fclose()` to complete and then returned `EOF` with `errno=EIO` to `depmod`.

Observed:

```text
FW_PROBE: fclose path .../modules.dep.<temporary suffix> [inject]
depmod: ERROR: Could not create index 'modules.dep'. Output is truncated: No space left on device
exit: 1
modules.dep: 0 bytes
```

The pre-existing `OLD-SENTINEL` content was gone. No temp file remained.

### What the probe establishes

The installed kmod behavior matches current-source ordering at the decision boundary:

- stream close failure is detected;
- the command reports failure;
- publication has already happened;
- the prior index is not preserved.

The shim models error reporting after real close. It does not model physically incomplete persisted bytes.

## Cross-context pass

### Callback failure vs stream failure

**Discriminator:** whether `itr->cb()` returns a negative error or stdio finalization sets `ferr`.

- callback failure: temp is released before publication;
- stream failure: temp is published, then error is returned.

This is a deliberate-looking semantic split in current code.

### Old manual temp implementation vs 2025 helper

**Discriminator:** source generation.

- pre-2025: hand-built temporary name and direct `renameat()`;
- current: `tmpfile_openat()` / `tmpfile_publish()` / `tmpfile_release()`.

The ordering survives the implementation change, which narrows the claim away from a tmpfile-helper regression.

### Fresh index vs stale previous index

**Discriminator:** which imperfect state should remain after generation failure.

- current behavior may leave a truncated/empty newly generated index;
- moving `ferr` before publication would leave the previous index, which may describe a different module set.

This is the unresolved policy boundary. Source evidence alone does not establish which failure state the project wants today.

## Existing tests

`testsuite/test-depmod.c` covers ordering, output directories, alternate module directories, weak dependencies, loop detection, and other functional cases. This pass found no ENOSPC/finalization-failure test that asserts whether the prior published index should survive.

The absence of such a test does not erase the historical commit evidence; it means the failure policy is not currently encoded by the inspected test suite.

## Disposition

### Retained negative result

Do **not** promote this as:

> the 2025 tmpfile refactor accidentally publishes failed depmod output.

History disproves that framing.

### Successor design question

A legitimate new bounded question is:

> When `depmod` detects output truncation or close failure, should it preserve the previous complete index instead of publishing the failed generation, and what do module-management consumers expect after a failed depmod run?

That successor needs evidence from package-manager workflows, kmod maintainer intent, recovery behavior, and possibly distribution expectations before any candidate reorder is justified.

## What would reopen a defect claim

Reopen with stronger language if one of these appears:

- project documentation promises atomic preservation of previous indexes on generation failure;
- consumers demonstrably assume a failed `depmod` leaves old indexes untouched;
- a maintainer change or test establishes preserve-old as the intended contract;
- current publication can produce a state worse than both documented and historically accepted failure behavior in a newly introduced way;
- the temporary-file helper creates a separate cleanup, identity, or durability defect beyond the longstanding ordering.

## Evidence boundary

Established:

- exact current source order at `65ac890492c96b88d10d8c92342a1b00ff603dba`;
- current `tmpfile_publish()` is rename-based;
- installed kmod 34.2 publishes before reporting the injected close failure;
- an old sentinel is replaced in the disposable fixture;
- 2012 history intentionally added truncation error signaling while retaining rename-before-error-check;
- 2025 tmpfile refactor preserved the same order;
- inspected current tests do not define old-index survival on finalization failure.

Not established:

- that current maintainers explicitly prefer truncated new indexes over stale previous indexes in 2026;
- package-manager or initramfs consumer behavior after failed `depmod`;
- a real ENOSPC/NFS close-only reproduction on current master;
- exact-current binary execution;
- a reason to change the historical policy.

## Next action

Treat this investigation as closed for the accidental-regression hypothesis. If revisited, start a separate successor around **failure-state policy**, comparing stale-old versus truncated-new consequences across package installation/removal and module-loading consumers.

## External-contact state

No upstream greenlight was given. No kmod issue, pull request, discussion, comment, email, or other external contact was made.
