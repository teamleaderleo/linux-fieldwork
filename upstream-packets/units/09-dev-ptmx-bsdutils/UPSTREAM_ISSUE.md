# Upstream issue disposition

## State

`RETIRED — DO NOT SUBMIT`

A separate issue would duplicate an existing canonical correction.

Canonical mmdebstrap commit:

```text
c75b58e3c88b1f49626b9ee073e9e9688d38922c
make_mirror.sh,tests/dev-ptmx: explicitly install bsdutils for script utility
```

The commit is present on canonical `develop` and tag `1.5.7+develop` and changes:

```diff
-	--include=gcc,libc6-dev,python3,passwd \
+	--include=gcc,libc6-dev,python3,passwd,bsdutils \
```

Historical Debian failure, static regression, downstream candidate, current-sid double pass, and canonical audit remain in this packet as validation evidence. No upstream issue was created.
