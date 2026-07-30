# Subordinate-ID files require exact account-field matching

## In simple words

`/etc/subuid` and `/etc/subgid` are colon-delimited records. The account identity is field 1. Code that asks whether a user already has a range must compare that field literally and exactly.

An unanchored regular-expression search can match another account whose name merely contains the requested username. It can also interpret punctuation as regex syntax. Either mistake can suppress required setup and cause a later user-namespace failure far from the real defect.

## Stable lesson

For subordinate-ID checks:

1. read field 1 only;
2. compare it as a fixed string;
3. distinguish absent, empty and exact-present files;
4. make setup idempotent;
5. apply identical semantics to subuid and subgid.

A suitable shell form is:

```sh
cut -s -d: -f1 /etc/subuid | grep -Fxq -- "$user"
```

The `-s` option suppresses delimiter-free malformed records, `--` protects
usernames beginning with `-`, `-F` disables regex interpretation, `-x`
requires the whole extracted field, and `-q` keeps the check quiet.

## Counterexample

For requested user `debci`, this record belongs to another account:

```text
old-debci-helper:200000:65536
```

A plain `grep debci /etc/subuid` succeeds and falsely reports that `debci` is configured.

## mmdebstrap package-test example

The imported `debian/tests/testsuite` ensures subordinate ranges for the ordinary autopkgtest user before running unshare cases. Its original check searches the whole line with an unanchored regex. Issue #80 and its focused candidate change only the two match conditions; the existing append policy remains intact.

The regression executes the exact patched shell blocks against temporary files and covers:

- exact account present;
- username appearing only inside another account;
- username appearing alone on a delimiter-free malformed line;
- regex-significant input treated literally;
- empty file;
- absent file;
- subuid and subgid parity;
- immediate rerun without duplicate entries.

## Limits

Exact matching does not validate range overlap, numeric bounds, duplicate conflicting records or allocation policy. Those are separate contracts. This fix answers only whether the requested account already has any record.

## Related records

- Issue #80
- `investigations/mmdebstrap-exact-subid-user-match/README.md`
