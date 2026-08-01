# Upstream pull-request disposition

## State

`RETIRED — DO NOT SUBMIT`

Canonical mmdebstrap already owns the correction:

```text
commit: c75b58e3c88b1f49626b9ee073e9e9688d38922c
branch: develop
also reachable from: tag 1.5.7+develop
subject: make_mirror.sh,tests/dev-ptmx: explicitly install bsdutils for script utility
```

Canonical hunk:

```diff
-	--include=gcc,libc6-dev,python3,passwd \
+	--include=gcc,libc6-dev,python3,passwd,bsdutils \
```

The Linux Fieldwork candidate used equivalent package membership with a different ordering. Canonical source ordering and ownership take precedence.

No external pull request was created. The retained draft, patch, regressions, and execution artifacts are historical confirmation only.
