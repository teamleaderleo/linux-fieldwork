# TMPDIR fallback versus an explicit-path contract

## In simple words

`TMPDIR` usually means “a preferred place for temporary files,” not always “this exact directory or fail.” Libraries may skip an unusable value and choose `/tmp`. That is helpful for small disposable files, but it can be surprising when the temporary object is large or when the caller selected a particular filesystem deliberately.

The application has to decide which meaning it promises:

- **preference:** find a usable temporary location;
- **contract:** use this exact parent directory or report an error.

## What I learned

Perl's `File::Temp` exposes both meanings.

```perl
$tempdir = tempdir('example.XXXXXXXXXX', TMPDIR => 1);
```

`TMPDIR => 1` delegates to `File::Spec->tmpdir`. On Unix, that routine considers environment and system candidates and returns the first writable location. An unusable environment value can therefore be skipped.

```perl
$tempdir = tempdir('example.XXXXXXXXXX', DIR => $ENV{TMPDIR});
```

`DIR` names the exact parent directory. Creation fails when the path is missing, is not a directory, or cannot accept the new directory.

## Why a direct operation is better than a permission probe

A preliminary check such as `-w`, `access()`, or creating and deleting a probe file answers what was true during the check. The real operation occurs later and can still fail. It also duplicates work and can behave differently under ACLs, namespaces, mount changes, quotas, or concurrent filesystem changes.

A cleaner pattern is:

1. decide whether the input is a preference or a contract;
2. call the real safe creation primitive once;
3. report the failure from that operation.

`File::Temp` creates the random directory safely and raises an exception containing the requested path and operating-system error.

## Example

```perl
my @tempdir_options = (TMPDIR => 1);
if (defined $ENV{TMPDIR} && $ENV{TMPDIR} ne '') {
    @tempdir_options = (DIR => $ENV{TMPDIR});
}
my $root = tempdir('example.XXXXXXXXXX', @tempdir_options);
```

This policy means:

- absent value: choose a normal system temporary location;
- empty value: keep the normal default;
- non-empty value: use that exact parent or fail.

## Operational impact

Fallback can be harmless for a tiny short-lived file. It is more consequential when the temporary content is a package build tree, filesystem image, database export, compiler workspace, or full root filesystem. The caller may have chosen another location because `/tmp` is RAM-backed, capacity-limited, mounted with different options, or on the wrong storage device.

A silent fallback can then cause unexpected memory or disk consumption and a later out-of-space error whose connection to `TMPDIR` is unclear.

## Environment and assumptions

- Perl interface: `File::Temp::tempdir`
- Unix temporary-directory selection: `File::Spec->tmpdir`
- Exact versions influence wording of native error messages, not the preference-versus-contract distinction described here.

## Limits

This note does not say every program should treat `TMPDIR` strictly. Many programs intentionally use it as a preference. The correct policy depends on the command's documented behavior and the consequences of selecting another filesystem.

## Related work

- Related investigation: `../../investigations/mmdebstrap-unwritable-tmpdir/`
- Perl `File::Temp`: `https://perldoc.perl.org/File%3A%3ATemp`
- Perl `File::Spec`: `https://perldoc.perl.org/File%3A%3ASpec`
