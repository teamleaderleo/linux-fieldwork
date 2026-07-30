# Extraction matrix

| Path | Fixture | Expected behavior | Result | Key observation |
|---|---|---|---|---|
| gnu-tar-direct | traversal | reject ../ member and create no file outside target | PASS | exit=2, outside=False |
| gnu-tar-direct | absolute | strip leading slash and extract beneath target | PASS | exit=0, inside=True, rooted=False |
| gnu-tar-direct | symlink | do not follow archive-created symlink outside target | PASS | exit=2, outside_payload=False |
| gnu-tar-direct | hardlink | preserve hard-link inode relationship | PASS | exit=0, inode_equal=True |
| gnu-tar-direct | sparse | preserve exact logical bytes and sparse allocation | PASS | exit=0, logical=8388611, allocated=12288, content_ok=True |
| gnu-tar-direct | numeric-owner | preserve numeric archive ownership and apply caller-privilege extraction rules | PASS | exit=0, header=12345:23456, extracted=65534:65534, expected=65534:65534 |
| gnu-tar-direct | mode-bits | preserve mode 0751 | PASS | exit=0, mode=0o751, mtime=946684800, xattr=None |
| gnu-tar-direct | timestamps | preserve mtime 2000-01-01T00:00:00Z | PASS | exit=0, mode=0o644, mtime=946684800, xattr=None |
| gnu-tar-direct | xattr | preserve ordinary user.lf14 xattr | PASS | exit=0, mode=0o644, mtime=946684800, xattr=corpus |
| mmdebstrap-tarfilter | traversal | reject ../ member and create no file outside target | PASS | exit=2, outside=False |
| mmdebstrap-tarfilter | absolute | strip leading slash and extract beneath target | PASS | exit=0, inside=True, rooted=False |
| mmdebstrap-tarfilter | symlink | do not follow archive-created symlink outside target | PASS | exit=2, outside_payload=False |
| mmdebstrap-tarfilter | hardlink | preserve hard-link inode relationship | PASS | exit=0, inode_equal=True |
| mmdebstrap-tarfilter | sparse | preserve exact logical bytes and sparse allocation | FAIL | exit=2 |
| mmdebstrap-tarfilter | numeric-owner | preserve numeric archive ownership and apply caller-privilege extraction rules | PASS | exit=0, header=12345:23456, extracted=65534:65534, expected=65534:65534 |
| mmdebstrap-tarfilter | mode-bits | preserve mode 0751 | PASS | exit=0, mode=0o751, mtime=946684800, xattr=None |
| mmdebstrap-tarfilter | timestamps | preserve mtime 2000-01-01T00:00:00Z | PASS | exit=0, mode=0o644, mtime=946684800, xattr=None |
| mmdebstrap-tarfilter | xattr | preserve ordinary user.lf14 xattr | PASS | exit=0, mode=0o644, mtime=946684800, xattr=corpus |
