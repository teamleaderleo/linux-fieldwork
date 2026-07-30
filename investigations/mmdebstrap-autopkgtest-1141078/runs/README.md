# Run artifacts

Give each run its own directory. Retain compact evidence another person can inspect and repeat:

- execution context with sensitive fields excluded;
- exact command and source hashes;
- APT policy and installed package versions;
- exit status and result classification;
- root filesystem manifests and field-level comparisons;
- focused logs around the first failing operation;
- hashes for large or temporary artifacts.

Root filesystem tarballs, disk images, extracted roots, and raw Debian BTS mail stay outside Git. Hosted workflow artifacts expire after review. Promote only the minimal public evidence needed to support a finding.
