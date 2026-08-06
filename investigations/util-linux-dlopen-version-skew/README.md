# util-linux runtime-optional loader version-skew probe

Tracks Linux Fieldwork issue #456.

## Question

Does util-linux's all-or-nothing `ul_dlopen_symbols()` make an old feature unavailable when the same-SONAME runtime library exports the feature's symbol but lacks one unrelated symbol that was present in the build headers?

## Exact source

- util-linux: `cdd407b45e00b6a6b561d10f3bcc9fdc6a05755f`
- shared resolver: `lib/dl-utils.c`
- actual libsystemd table: `lib/dl-systemd.c`
- concrete consumer: `misc-utils/logger.c`

The actual table contains both `sd_journal_sendv()` and newer device APIs such as `sd_device_open()`. `logger --journald` only calls `sd_journal_sendv()` after the common loader succeeds.

## Probe design

The hosted workflow:

1. checks out the exact util-linux commit;
2. compiles the real `lib/dl-utils.c` with a tiny harness;
3. builds a fake `libsystemd.so.0` exporting only `sd_journal_sendv()`;
4. loads it through a two-symbol table containing `sd_journal_sendv` and absent `sd_device_open`;
5. requires the common-table load to fail;
6. retries with a journal-only table;
7. requires that load to succeed and invokes the fake journal function;
8. retains stdout, stderr, source identity, exported-symbol inventory, and checksums.

## Interpretation

- common table fails, journal-only succeeds: confirmed feature over-coupling;
- both fail: fixture or loader-path problem;
- common table succeeds: fake DSO accidentally exports the supposedly missing symbol or source semantics changed.

No upstream contact is authorized or made.
