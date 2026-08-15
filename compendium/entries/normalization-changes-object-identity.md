# Normalization changes object identity

## Metadata

```json
{
  "schema": 1,
  "id": "normalization-changes-object-identity",
  "kind": "bug-species",
  "maturity": "candidate",
  "facets": {
    "domains": ["filesystems", "archives", "parsing"],
    "concerns": ["identity", "compatibility", "cross-layer-contracts"],
    "mechanisms": ["normalization", "path-matching", "string-processing"],
    "triggers": ["edge-case-input", "representation-conversion"]
  },
  "aliases": ["character-stripping-is-not-prefix-removal"],
  "relations": [],
  "cases": ["notes/filesystems/archive-path-normalization-must-not-change-names.md", "teamleaderleo/linux-fieldwork#28"]
}
```

## In simple words

A conversion intended to remove structural syntax also removes characters that belong to the object's real name, so validation/matching is performed against a different identity.

A classic shape is using a character-set strip when the contract requires removing one exact prefix:

```text
wanted: remove leading "./"
used:   strip any leading '.' or '/'
result: .hidden / ../path can become different names
```

## Hunt it

At every normalization boundary, write the exact equivalence relation the protocol intends. Compare prefix removal, separator normalization, case folding, decoding, Unicode normalization, path canonicalization, and generic trim/strip helpers. Feed values whose leading/trailing characters are meaningful object data rather than structural syntax.

## Repair shape

Implement the narrow structural transformation explicitly. Preserve original identity when later logic needs literal prefixes, references, or round-tripping. Do not reconstruct user intent from a compiled matcher or other lossy representation when the original token is available.

## Regression shape

Pair structurally equivalent forms with nearby non-equivalent names:

```text
./foo      ↔ foo       expected equivalent
./.secret  ↔ .secret   preserve filename dot
../foo                must not silently become foo
```

Keep a control where normalization genuinely should change representation without changing identity.

## Limits

Some protocols intentionally define aggressive canonicalization. The species exists when the chosen string operation is broader than the governing identity contract, not whenever normalization changes bytes.
