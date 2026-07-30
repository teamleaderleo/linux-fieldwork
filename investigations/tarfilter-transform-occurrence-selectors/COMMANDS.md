# Commands

Focused regression:

```sh
python3 -m unittest tests.test_tarfilter_transform_occurrences -v
```

Complete repository suite:

```sh
python3 -m unittest discover -s tests -v
```

Manual predecessor check:

```sh
python3 upstream/mmdebstrap/tarfilter --transform 's/a/b/2'
```

The automated test supplies a valid archive on standard input and checks the predecessor rejection before applying the incremental patch.
