# UV project landscape follow-up — later 2026-08-10 pass

This record supplements `selection.md` and `adjacent-findings.md` with later results from the same broad Fieldwork pass.

Current-source reference moved during this pass from `1881d30773386da77017f2ad5ceaf160535d65da` through `e1c1f30e2537f46a6a3622f825d8da22ed4fbde9` to `62538397e59a7fd10db51cb3889df9b4d6449e6b`. Completed hosted receipts remain pinned to the exact source listed with each investigation; do not silently relabel old runs as current-main execution.

No canonical upstream interaction is authorized by this record. External GitHub references use `https://redirect.github.com/...`.

## 1. Malformed static metadata can cross the non-package project boundary

Canonical context:

- https://redirect.github.com/astral-sh/uv/issues/20908

Fieldwork #525 used an intentionally unusable declared build backend to distinguish project-package semantics from error wording.

Receipt:

- run `31345242697`
- job `93325843049`
- Ubuntu 24.04.4
- uv 0.12.3 plus pinned `1881d30773386da77017f2ad5ceaf160535d65da`
- artifact `malformed-metadata-package-525`
- artifact ID `9047154712`
- artifact SHA-256 `760df23fec9f5a8f180daa3593aac55ac699b9956d491f7f60e4945ef2a2a23c`

A valid project with `tool.uv.package = false`, `no-build = true`, and a nonexistent build backend locks successfully, proving UV normally honors the documented non-package rule and ignores the declared backend.

Changing only the dependency metadata to malformed PEP 508 text (`numpy<2.6>`) changes the control flow: UV attempts root metadata building. With `no-build = true` this surfaces as a build-disabled error; without `no-build` it falls into a legacy `setup.py` metadata path. The same malformed text in a requirements file is rejected directly by the parser.

Classification: the first owner is **static project metadata recovery crossing the non-package boundary**. `no-build` only changes the downstream error. A future repair should preserve malformed-static-metadata provenance for workspace members and avoid build-metadata recovery for a root explicitly marked `package = false`, without changing generic buildable-source fallback.

Fieldwork #525 and execution PR #526 are closed evidence-only.

## 2. Conditional source behavior contains one real leak and two expected constraints

Canonical context:

- https://redirect.github.com/astral-sh/uv/issues/13073

Fieldwork #528 replaced Git/index sources with three local source trees for the same package, carrying sentinel versions base 1.0.0, local 2.0.0, and remote 3.0.0.

Receipt:

- run `31345751324`
- job `93327239355`
- Ubuntu 24.04.4
- uv 0.12.3 plus pinned `1881d30773386da77017f2ad5ceaf160535d65da`
- artifact `conditional-sources-conflicts-528`
- artifact ID `9047393751`
- artifact SHA-256 `1c3be5836d52101c4bf30add01cb49898cbec2f8a5da3f349ec4d4d136e479c8`

Two broad behaviors are expected under current contracts:

- two extra-only sources with mutually conflicting extras but no base source cannot satisfy the universal project's no-extra split, while `uv pip` can resolve a narrower selected-extra input;
- an unconditional source plus extra-conditioned sources produces URL conflicts because current configuration does not define an unconditional source as a default overridden by a more specific extra source.

The actual contradiction is simpler: with **one** source declared only as `extra = "local"`, project `uv lock` uses that source even with no extra selected, and `uv sync --extra remote` also uses it. `uv pip` base/remote controls correctly do not use it.

Source review narrows the likely owner:

- metadata lowering correctly applies an extra-conditioned source only while lowering that optional dependency;
- the lowered direct requirement preserves the top-level `extra == "local"` marker;
- resolver initialization builds `Urls::from_manifest(&manifest, &env)` once before later conflict-fork solving;
- regular direct URLs are stored package-wide in `FxHashMap<PackageName, Vec<VerbatimParsedUrl>>`, while URL overrides already use a fork-aware `ForkMap`;
- the upstream resolver author independently suspected URL-source detection was not accounting for conflicting extras.

Current hypothesis: **regular direct URL/path eligibility needs fork-aware provenance**. Do not change universal lock coverage and do not invent base-source override precedence as part of this bug.

Fieldwork #528 remains open for source/fork modeling; execution PR #529 is closed evidence-only.

## 3. Managed-Python publication needs a cross-source discovery invariant on Windows

Canonical context:

- https://redirect.github.com/astral-sh/uv/issues/19329

The existing Linux publication race in Fieldwork #309 was already fully reproduced and had a clean `.uv-installing` marker candidate, internal UV PR #64 at head `8525cfc69e561adc0b4f71c2c1f02ae457b37b7c`.

The original marker protocol correctly hides directories from `ManagedPythonInstallations::find_all()`, but Windows validation exposed a second discovery route: PEP 514 registry entries can point directly to the exact patch-level interpreter and bypass directory enumeration.

Windows proof receipt:

- run `31346319867`
- job `93328815203`
- Windows Server 2025, `windows-2025-vs2026` image `20260803.193.1`
- artifact `managed-python-marker-windows-309`
- artifact ID `9047589828`
- artifact SHA-256 `b93e859489293614b1d61aaac40304c1c3c1317c92ba16fc35f376bc09cee19a`

An adapted `find_all()` unit test passes on Windows, proving marker-directory filtering itself is cross-platform. With the clean #64 binary, the marked patch-level interpreter remains visible. Setting `UV_PYTHON_NO_REGISTRY=1` removes that exact-path leak, isolating PEP 514 as the remaining bypass.

A discovery-layer prototype then passed both automatic `python list` and exact-version `python find` controls while preserving rediscovery after marker removal. The important factoring is **not** to make `Interpreter::query()` marker-aware, because installation finalization intentionally queries the interpreter while the marker exists. Instead, after a discovery source queries an interpreter, map it back to UV's managed root and skip the candidate if that root still carries `.uv-installing`.

Controlled source variant:

- internal UV PR #85
- branch `fix/hide-incomplete-managed-python-installations-cross-source`
- head `b09109fa147ccbbde87a9723852f21e1bf301289`
- base is clean #64
- product delta is only `crates/uv-python/src/discovery.rs` and `crates/uv-python/src/managed.rs`

Actual-source Linux validation on Fieldwork #537 passed the original marker unit plus paused-new-install, failed-publication/retry, and paused-reinstall reversing controls.

The first actual-source Windows validation also proved the automatic routes are fixed: managed list and exact-version discovery do not surface the marked root. It initially failed only because the research harness expected an **explicit absolute interpreter path** to be rejected.

Source intent classifies that distinction: `PythonRequest::File` is handled directly as `PythonSource::ProvidedPath`; it intentionally bypasses candidate enumeration and queries the user-provided path. Therefore the marker is a publication/discovery protocol, not a filesystem quarantine. The final validation model preserves explicit provided-path authority while requiring all automatic managed/PATH/registry discovery routes to hide incomplete installs.

A final Windows-only validation is running against exact #85 head with that contract.

## 4. Workspace EACCES is reproducible without Landlock, but the owner is shared discovery policy

Canonical context:

- https://redirect.github.com/astral-sh/uv/issues/18197

The public issue was tagged `needs-mre` because the Landlock setup was difficult to reproduce. Fieldwork #535 produced the same syscall distinction using ordinary permissions: an ancestor `pyproject.toml` is mode `000`, so `stat()` / `is_file()` succeeds while opening the file returns `EACCES`.

Baseline receipt:

- run `31347288571`
- job `93331453860`
- Ubuntu 24.04.4
- uv 0.12.3 plus pinned `e1c1f30e2537f46a6a3622f825d8da22ed4fbde9`
- artifact `workspace-eacces-boundary-535`
- artifact ID `9047796774`
- artifact SHA-256 `267a87d278b999f0cc7521d36e76e1f9ac1ea8a8c88f63c38a495a9b02b17f66`

`uv lock --dry-run`, `uv workspace metadata`, and `uv venv` all fail on the unreadable ancestor before creating project state.

Readable controls expose the real product choice:

- an ordinary readable parent project that is not a workspace already stops upward workspace discovery and leaves the child standalone; treating the unreadable copy as a boundary preserves effective semantics;
- a readable true workspace root changes the child's workspace identity; treating an unreadable copy as a boundary necessarily discards a hidden contract the sandbox does not permit UV to read.

The first one-function prototype caught only `PermissionDenied` inside `uv-workspace::find_workspace`, but still failed because **filesystem settings discovery independently walks the same ancestors first**. `FilesystemOptions::find` treats project-level `PermissionDenied` as fatal even though user-level configuration discovery already treats PermissionDenied as absent.

Therefore a coherent authority-boundary policy must be shared across at least:

1. project/settings discovery; and
2. workspace discovery.

The v2 prototype keeps current-directory permission failures fatal, treats only inaccessible **ancestors** as boundaries, and retains readable malformed-TOML failures. It is currently executing on pinned `62538397e59a7fd10db51cb3889df9b4d6449e6b`.

Do not suppress arbitrary I/O or parse errors. If this policy is adopted, diagnostics should make it visible that parent configuration/workspace discovery stopped at an authority boundary.

## 5. Selection state after this pass

### Controlled product candidate under validation

- #309 / internal UV #85 — cross-source managed-Python completion-marker discovery.

### Active source/policy research

- #528 — extra-conditioned direct URL/path eligibility across resolver forks.
- #535 — inaccessible ancestor as shared settings/workspace authority boundary.

### Live external-platform discriminator

- #504 — Intel-macOS direct/root-file `--find-links` run remains queued; do not infer a result.

### Completed evidence lanes

- #508 tool-environment identity / docs contract.
- #515 registry negative-cache semantics.
- #519 invalid project-environment handling in read-only commands.
- #525 malformed static metadata crossing `package=false`.

### Observe only

- project-less project semantics;
- content-addressed cache lifecycle;
- native-auth hierarchical credential matching;
- managed-Python abandoned scratch cleanup after abrupt process death;
- release PGO and large-workspace performance work.

The strongest recurring project lesson remains the same: UV's difficult bugs increasingly live at **identity and authority boundaries between subsystems**, not in isolated algorithms. Fieldwork adds the most value by preserving those distinctions rather than turning every surprising symptom into a patch.
