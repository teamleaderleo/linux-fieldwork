# BusyBox sed close-failure probe results

## TL;DR

A deterministic local close-error model reproduced the publication problem on Debian BusyBox 1.37.0.

The probe allowed BusyBox `sed -i` to complete its normal explicit flush and real `fclose()`, then changed only the `fclose()` return for the temporary output stream to `EOF` with `errno=EIO`. BusyBox `sed -i` still exited `0` and replaced the original pathname with transformed content.

The same injected close result against BusyBox `dos2unix FILE` produced exit `1`, preserved the original file byte-for-byte, and removed the temporary output. This is the expected negative control from the source comparison.

Current upstream master at `7473045ad3504db9b421427a452fd9b146346306` still has the same relevant `sed -i` sequence: checked `fflush()`/`ferror()`, unchecked `fclose()`, then rename. Exact-current execution could not be run in this environment because outbound DNS prevented cloning the source tree.

## Environment

Observed local runtime:

```text
/usr/bin/busybox
BusyBox v1.37.0 (Debian 1:1.37.0-6+b8) multi-call binary
```

`ldd` showed a dynamically linked glibc build, which made `fclose()` interposition possible.

Reviewed current upstream source remains:

```text
vda-linux/busybox_mirror
7473045ad3504db9b421427a452fd9b146346306
```

## First execution attempt

An exact-current clone was attempted first:

```sh
git clone https://github.com/vda-linux/busybox_mirror.git /tmp/busybox-fieldwork
```

The runtime returned:

```text
fatal: unable to access 'https://github.com/vda-linux/busybox_mirror.git/': Could not resolve host: github.com
```

Failure owner: execution environment / outbound DNS, not BusyBox.

The source identity had already been retrieved through the GitHub connector, so the follow-up used the installed BusyBox only as a controlled execution model of the same finalization sequence.

## Test seam

The probe used an `LD_PRELOAD` wrapper that targets only a stream whose open descriptor path starts with the selected input pathname but is not the input pathname itself. For BusyBox in-place applets this selects the adjacent temporary output.

The wrapper lets the real `fclose()` execute first. If that succeeds for the selected temp stream, it overrides only the reported result:

```c
#define _GNU_SOURCE
#include <stdio.h>
#include <dlfcn.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <limits.h>

static int (*real_fclose_fn)(FILE *);

int fclose(FILE *stream)
{
    char linkpath[64], path[PATH_MAX + 1];
    const char *prefix = getenv("FW_FAIL_CLOSE_PREFIX");
    int fd = fileno(stream);
    int target = 0;
    ssize_t n = -1;

    if (!real_fclose_fn)
        real_fclose_fn = dlsym(RTLD_NEXT, "fclose");

    if (fd >= 0 && prefix && *prefix) {
        snprintf(linkpath, sizeof(linkpath), "/proc/self/fd/%d", fd);
        n = readlink(linkpath, path, sizeof(path) - 1);
        if (n >= 0) {
            path[n] = '\0';
            if (strncmp(path, prefix, strlen(prefix)) == 0
             && strcmp(path, prefix) != 0)
                target = 1;
        }
    }

    int rc = real_fclose_fn(stream);
    if (target && rc == 0) {
        static const char msg[] =
            "FW_PROBE: synthetic fclose EIO on temp output\n";
        write(STDERR_FILENO, msg, sizeof(msg) - 1);
        errno = EIO;
        return EOF;
    }
    return rc;
}
```

Build:

```sh
gcc -shared -fPIC -O2 -Wall -Wextra \
  -o fclose_fail.so fclose_fail.c -ldl
```

This seam models the error-reporting contract only. The real close and writes have already completed, so it does not model incomplete persisted bytes.

## Probe 1: `sed -i` close-only failure

Setup:

```sh
printf 'original line\n' > sed-input
FW_FAIL_CLOSE_PREFIX="$PWD/sed-input" \
LD_PRELOAD="$PWD/fclose_fail.so" \
/usr/bin/busybox sed -i 's/original/changed/' sed-input
```

Observed:

```text
FW_PROBE: synthetic fclose EIO on temp output
exit: 0
final content: changed line
```

No temporary output remained after the run.

### Interpretation

The injected `fclose()` error reached the BusyBox call site, but `sed -i` did not translate it into failure and continued into publication. This matches the reviewed source control flow.

The probe establishes ignored close-error signaling and replacement-after-reported-close-failure. It does not establish that the transformed bytes would be damaged on a real filesystem.

## Probe 2: ordinary `sed -i` passing control

```sh
printf 'original line\n' > sed-control
/usr/bin/busybox sed -i 's/original/changed/' sed-control
```

Observed:

```text
exit: 0
final content: changed line
```

This confirms the fixture still recognizes the ordinary successful path.

## Probe 3: `sed -i.bak` close-only failure

Setup:

```sh
printf 'original backup case\n' > sed-backup
FW_FAIL_CLOSE_PREFIX="$PWD/sed-backup" \
LD_PRELOAD="$PWD/fclose_fail.so" \
/usr/bin/busybox sed -i.bak 's/original/changed/' sed-backup
```

Observed:

```text
FW_PROBE: synthetic fclose EIO on temp output
exit: 0
sed-backup: changed backup case
sed-backup.bak: original backup case
```

### Interpretation

The ignored close result survives backup mode. The old bytes remain recoverable through the requested backup, but the command still publishes the temp output and reports success despite the finalization error.

## Probe 4: `dos2unix` negative control

Setup:

```sh
printf 'alpha\r\nbeta\r\n' > d2u-input
cp d2u-input d2u-before
FW_FAIL_CLOSE_PREFIX="$PWD/d2u-input" \
LD_PRELOAD="$PWD/fclose_fail.so" \
/usr/bin/busybox dos2unix d2u-input
```

Observed:

```text
FW_PROBE: synthetic fclose EIO on temp output
dos2unix: : Input/output error
exit: 1
original preserved byte-for-byte: yes
no conversion temp survived
```

### Interpretation

The same synthetic close result is observable and actionable in a neighboring BusyBox in-place converter. `dos2unix` rejects publication because its source checks `fclose(out)` before rename.

This is a strong negative control against explanations based on the wrapper, process environment, or BusyBox fatal cleanup generally.

## Result matrix

| Case | Injected temp close error | Exit | Published transformed output | Old content retained |
|---|---:|---:|---:|---:|
| `sed -i` | yes | 0 | yes | no explicit backup |
| `sed -i.bak` | yes | 0 | yes | yes, `.bak` |
| `dos2unix FILE` | yes | 1 | no | yes, original pathname |
| `sed -i` control | no | 0 | yes | n/a |

## Current disposition

The error-handling defect is reproduced at the control-flow interface on BusyBox 1.37.0, and current upstream master has the same relevant source sequence.

Promote the bounded claim to:

> BusyBox `sed -i` ignores a reported `fclose()` failure for its temporary output and can continue to rename that output over the input while returning success.

Keep the practical storage consequence narrower:

> Linux permits delayed write/finalization errors to surface at close time, so a real close-only failure can reach this unchecked branch. This probe does not demonstrate damaged persisted bytes on a specific filesystem.

## Next useful work

1. Prepare the smallest current-master candidate that checks output `fclose()` before either backup or final rename.
2. Reuse the existing `xfunc_error_retval = 4` write-error behavior and `cleanup_outname` fatal cleanup path.
3. Build and run the candidate against a deterministic close-error test seam.
4. Measure BusyBox size delta.
5. If practical, add a filesystem-backed delayed-close-error fixture as a consequence/reachability follow-up rather than as a prerequisite for the code fix.

## Evidence boundary

Established:

- current upstream source has unchecked output `fclose()` before rename;
- installed BusyBox 1.37.0 exhibits that exact error-handling behavior under a targeted close-return injection;
- plain `-i` and backup `-i.bak` both publish despite the reported close error;
- `dos2unix` rejects the same injected close error and preserves the original;
- normal `sed -i` control succeeds;
- exact-current clone failure was environmental and recorded separately.

Still open:

- exact-current binary execution at `7473045ad3504db9b421427a452fd9b146346306`;
- candidate compilation and code-size result;
- real filesystem reproduction of a close-only delayed write error;
- persisted-byte consequence under a real failure mode;
- upstream maintainer interpretation.

## Cleanup

All probe inputs, shim source, and shared object lived under `/tmp/busybox-close-probe`. No block devices, mounts, credentials, network targets, or external state were used.

## External-contact state

No upstream greenlight was given. No BusyBox issue, mailing-list message, patch submission, comment, email, or other external contact was made.
