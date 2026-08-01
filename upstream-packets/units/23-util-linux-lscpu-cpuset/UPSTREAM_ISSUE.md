# Withheld Debian BTS draft

Status: `DO NOT SEND — candidate and package-native gates pending; external contact unauthorized`

## Suggested subject

`util-linux: lscpu double-free on malformed cpuset input in trixie 2.41-5`

## Draft

Debian trixie `util-linux 2.41-5` retains an upstream-fixed ownership defect in `lib/path.c:ul_path_cpuparse()`.

On parse failure, the function frees the allocated cpuset while leaving the caller-visible output pointer unchanged. Later ordinary `lscpu` cleanup can free the stale address again.

A deterministic 16-CPU sysroot reproduces against the trixie amd64 package:

```text
valid text: 0
valid JSON: 0
malformed text (`online` = `5,12-%`): 134
malformed JSON: 134
stderr: free(): double free detected in tcache 2
```

The full matrix repeats from clean state. A larger allocation-size case can evade the duplicate free and is retained as a losing control.

Upstream fixed the defect in commit:

```text
4581ede384f22983d6155768635ce43cb5304cb0
lib/path: avoid double free() for cpusets
```

The correction adds `*set = NULL` immediately after the error-path free. The original reporter confirmed it, and maintained upstream branches contain it.

Exact Debian `2.41-5` source was unpacked with its quilt series. Effective `lib/path.c` still contains the affected free-without-NULL path. The canonical patch applies with zero fuzz and a patched amd64 binary package builds successfully.

Before sending, fill in:

- candidate actual-binary text/JSON matrix;
- valid baseline/candidate output comparison;
- util-linux native test result;
- source package version and debdiff;
- proposed-updates request reference;
- severity and stable-update rationale;
- cleanup and immediate rerun receipt.

## Send gate

Send only after explicit authorization and completion of every blank above.
