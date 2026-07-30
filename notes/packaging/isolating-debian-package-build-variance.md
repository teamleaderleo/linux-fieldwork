# Isolating Debian package build variance

## In simple words

A reproducibility probe changes one build input at a time and asks which outputs change: the `.deb`, its extracted payload, control metadata, `.buildinfo`, or `.changes`.

The important distinction is between package-content variance and build-event metadata. Two builds can produce byte-identical `.deb` files while their `.buildinfo` or `.changes` files differ because the build date or execution record changed.

## What I learned

Start with a same-environment repeat baseline. Then vary practical inputs such as:

- elapsed time;
- build path;
- locale;
- timezone;
- hostname environment;
- build user;
- source file creation order;
- parallel build scheduling;
- declared `SOURCE_DATE_EPOCH`.

Compare several layers instead of only the final package hash:

1. complete `.deb` bytes and SHA-256;
2. extracted payload bytes;
3. extracted control data;
4. outer `ar` member metadata;
5. data-tar member metadata;
6. `.buildinfo` and `.changes` records.

An explicitly changed `SOURCE_DATE_EPOCH` is a declared input change, not an ambient nondeterminism defect. If only archive timestamps change while extracted payload and control data remain equal, record that distinction.

A parallelism variant should contain at least two independent compile targets and should prove that the build actually invoked the intended job count. Merely setting `DEB_BUILD_OPTIONS=parallel=4` on a single-target build does not exercise concurrent scheduling.

“One factor at a time” should be literal when practical. If most variants also use different paths, retain a path-only control and state the residual confounding instead of overstating isolation.

Destructive build roots need an early guard. Resolve the caller path and reject `/`, temporary-root parents themselves, and paths outside the dedicated temporary hierarchy before `rm -rf`.

## Source and provenance

- Programme lane: LF-12 reproducible package variance
- Fixture: `lf12-variance-probe` version 1.0
- Runner: `artifacts/run-variance-probe.sh`
- Pull request: #19

## Example

A useful matrix row records:

```text
variant  deb_equal  unpacked_bytes_equal  control_equal  buildinfo_equal  changes_equal
```

The baseline repeat should establish the normal package and metadata behavior. A changed declared epoch can then be traced into outer and inner archive timestamps while preserving extracted content.

## Validation

The LF-12 runner builds a small native Debian package repeatedly on Debian 13, records complete hashes and archive listings, and asserts that practical ambient variants leave the package payload and control data unchanged. It also asserts that the alternate declared epoch changes the `.deb` while extracted payload and control remain equal.

A dedicated repository workflow is the execution carrier for the full matrix on the exact pull-request head in a Debian 13 container. Separate unit checks verify the destructive-path guard. The pull request must record the exact workflow run before claiming that its current head executed; the existence of the workflow alone is not an execution receipt.

## Environment and assumptions

- Debian 13 amd64 container.
- dpkg, dpkg-dev, GCC, GNU make, binutils, and standard archive tools.
- Controlled native source package with no external network dependency after package installation.

## Limits

This fixture does not replace `reprotest` or `diffoscope`, does not prove archive-source-package reproducibility, and does not cover other architectures, UTS namespace hostname changes, complex generated code, or genuinely large parallel build graphs.

Most variants use distinct run paths as well as their named environmental change. The separate path-only control supports the package-level conclusion, but the matrix should not be described as perfectly isolated one-factor execution for those rows.

## Related work

- Related issue: #15
- Related pull request: #19
- Related lane report: LF-SCOUT-DEB-02
