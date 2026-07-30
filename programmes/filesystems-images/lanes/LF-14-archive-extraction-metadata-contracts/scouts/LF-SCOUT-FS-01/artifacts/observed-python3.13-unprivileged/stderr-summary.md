# Non-empty extraction stderr

## GNU tar direct: traversal

```text
tar: Removing leading `../' from member names
tar: ../lf14-traversal-escape: Member name contains '..'
tar: Exiting with failure status due to previous errors
```

## GNU tar direct: absolute

```text
tar: Removing leading `/' from member names
```

## GNU tar direct: symlink

```text
tar: pivot/payload: Cannot open: Not a directory
tar: Exiting with failure status due to previous errors
```

## mmdebstrap tarfilter: traversal

```text
tar: Removing leading `../' from member names
tar: ../lf14-traversal-escape: Member name contains '..'
tar: Exiting with failure status due to previous errors
```

## mmdebstrap tarfilter: absolute

```text
tar: Removing leading `/' from member names
```

## mmdebstrap tarfilter: symlink

```text
tar: pivot/payload: Cannot open: Not a directory
tar: Exiting with failure status due to previous errors
```

## mmdebstrap tarfilter: sparse

```text
tar: .sparse-source: numeric overflow in sparse archive member
tar: Exiting with failure status due to previous errors
```
