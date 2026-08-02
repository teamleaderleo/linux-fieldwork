# Handoff — UV lockfile requirements diagnostic

Handoff date: 2026-08-02  
State: `ACTIVE — WAITING FOR CONTROLLED CI`  
External contact authorized: `false`  
External contact made: `none`

## Exact stopping point

```text
controlled repo: teamleaderleo/uv
base branch: main
base commit: 1da26a68629be6ae5fd7f924a7d49ff54763a7df
candidate branch: fieldwork/uv-lock-requirements-diagnostic
candidate head: a67f97bec7782c6f60aceefb2a9bcd7045582015
internal draft PR: #12
CI run: 30752526287
CI state: queued
```

Current canonical UV head checked:

```text
79bbface771210df216b738e9bdc7df95e5a9e6b
```

Canonical and controlled-base `crates/uv-requirements/src/sources.rs` were the same Git blob:

```text
cf6218326b96db5ce40e1fae31a0803e2c65e437
```

## Implemented result

The candidate detects only lockfiles UV itself can identify without reading lockfile contents:

- exact existing `uv.lock`;
- existing `<script-name>.lock` paired with a sibling that passes UV's PEP 723 parser.

An arbitrary `.lock` paired with an ordinary script remains a requirements input. Missing paths remain owned by the existing missing-file path.

## Commits

```text
72aec38bee0581bf742a8ddac24f4b2c65021ac3 — focused positive and negative tests
631b193e07768b29fe2aac983c65c53c727b1d89 — include focused test module
1180b4e5a0bac4b42455666ca0bc2bac5383a6ed — source implementation
 a67f97bec7782c6f60aceefb2a9bcd7045582015 — remove unrelated reconstructed doc changes
```

The leading space before the final SHA above is formatting only; the exact head is `a67f97bec7782c6f60aceefb2a9bcd7045582015`.

## First incomplete step

Read run `30752526287` and classify the first non-green job or step. Do not infer success from queue state.

## Required acceptance evidence

- `cargo fmt` or repository formatting gate passes;
- `uv-requirements` compiles with `uv_scripts::Pep723Metadata` usage;
- exact `uv.lock` test reports the intended diagnostic;
- paired PEP 723 script lock reports the intended diagnostic;
- ordinary `.lock` losing control remains accepted;
- missing-file behavior remains unchanged;
- complete branch diff contains no unrelated changes;
- cleanup and exact rerun state are recorded.

## Design warning

Do not replace the sibling-script discriminator with lockfile substring matching. That recreates the rejected upstream approach and can classify arbitrary TOML content as UV-owned.

## Publication boundary

The fork PR is internal and draft. Do not open or comment on a canonical UV issue or pull request without explicit authorization. Astral's repository guidance also separates AI-assisted coding from public communication; any eventual public text must be handled under the project's current policy and the user's explicit send decision.
