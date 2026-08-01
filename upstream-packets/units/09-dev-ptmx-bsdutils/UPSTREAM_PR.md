# Upstream pull-request draft

## Title

tests: include bsdutils for dev-ptmx

## Body

`tests/dev-ptmx` executes `script(1)` twice inside the generated apt-variant root. The root now includes `bsdutils` explicitly because that package provides `/usr/bin/script`.

The test previously received `script` through `bsdutils`' former Essential status. Once that package became ordinary, the apt variant omitted it and the case failed before reaching its intended PTY assertions.

The change adds one package to the existing include list:

```diff
-  --include=gcc,libc6-dev,python3,passwd \
+  --include=bsdutils,gcc,libc6-dev,python3,passwd \
```

All customize hooks and their order remain unchanged. mmdebstrap runtime behavior remains unchanged.

Validation completed before submission:

- the baseline contains two inner `script` hooks and omits `bsdutils`;
- the patch changes only the include line;
- the candidate retains the complete existing hook sequence;
- the historical failure identifies `script` as the first missing command and `bsdutils` as its provider;
- the focused current-sid `dev-ptmx --mode=root --variant=apt` case passes;
- cleanup completes and an immediate rerun passes.

## Submission checklist

- [ ] replace validation claims with exact current-head run identities after the open gates execute;
- [ ] create or identify a controlled fork;
- [ ] obtain explicit authorization for external contact;
- [ ] submit against the verified current `main` head.
