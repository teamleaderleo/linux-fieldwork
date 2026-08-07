# Test matrix — UV lockfile passed as requirements

The matrix separates file identity, parser outcome, and caller lane. A filename alone is insufficient provenance.

| Case | Setup | Lane | Expected result | Why |
|---|---|---|---|---|
| Project lock | Generate `uv.lock` from `pyproject.toml` | `-r` | UV-lock format diagnostic | Exact UV-owned project name after requirements parsing fails |
| PEP 723 script lock | Generate `action.py.lock` with `uv lock --script action.py` | `-r` | UV-lock format diagnostic | Exact sibling naming rule plus valid PEP 723 producer |
| Native Unix filename | Generate lock for script containing invalid UTF-8 bytes | `-r` | UV-lock format diagnostic | UV uses `OsString`; detector must preserve native filenames |
| Generic `.lock` | Empty `notes.lock`, no matching PEP 723 sibling | `-r` | Success with empty-file warning | `.lock` is generic and valid requirements input |
| Ordinary sibling | Empty `action.py.lock`; `action.py` is ordinary Python | `-r` | Success | Sibling is not a UV script-lock producer |
| Same-name collision | Empty `action.py.lock`; `action.py` is valid PEP 723 | `-r` | Success | Parse success outranks possible producer naming; this distinguishes parse-first from pre-detection |
| Missing project lock | No `uv.lock` file | `-r` | Existing `File not found` error | Diagnostic must not hide missing-path ownership |
| Script lock as exclusion list | Generated `action.py.lock` | `--exclude` / requirements-syntax file lane | UV-lock format diagnostic after parse failure | `from_requirements_txt` is reused for exclusion files; current source and experiment share this scope |
| Script lock as constraint | Generated `action.py.lock` | `-c` | Existing requirement parser error | Constraints use a distinct constructor and wording |
| Script lock as override | Generated `action.py.lock` | override file | Existing parser behavior | Shared parser must retain caller provenance |
| Invalid arbitrary collision | Invalid `action.py.lock`; valid PEP 723 sibling | `-r` | UV-lock hint is acceptable bounded ambiguity | File already failed requirements parsing; exact provenance is unavailable without content sniffing or metadata |
| Nested include | Top-level requirements contains `-r action.py.lock` | nested `-r` | Deferred | Current top-level source provenance does not identify the included path |
| Remote URL | HTTPS URL ending in `uv.lock` or `.lock` | `-r` | Deferred / ordinary remote parse behavior | Local sibling evidence is unavailable |
| Symlink alias | Alias points to script lock under another name | `-r` | Deferred | Alias can erase the producer sibling relationship |
| Stdin | `-r -` | `-r` | Existing stdin behavior | No path identity exists |
| Uppercase suffix | `action.py.LOCK` | `-r` | Ordinary requirements behavior | UV's producer appends lowercase `.lock` |
| Multi-dot script | `worker.dev.py.lock` beside `worker.dev.py` | `-r` | UV-lock diagnostic after parse failure | Strip only the final `.lock` through native path operations |
| Script already ends in `.lock` | `worker.lock` produces `worker.lock.lock` | `-r` | UV-lock diagnostic after parse failure | Complete original filename must be retained |

## Gate sequence

1. Verify exact base and candidate source identities.
2. Verify changed-file fence.
3. Run `cargo fmt --all --check`.
4. Run `cargo check -p uv-requirements -p uv`.
5. Run `cargo test -p uv --test pip_install uv_lock_requirements -- --nocapture`.
6. Confirm the test filter executed the expected module and test count.
7. Run `git diff --check` and verify a clean source tree.
8. Review the complete source diff after every repair.

## Assumptions being tested

- A valid requirements parse is stronger evidence than a filename collision.
- The special diagnostic belongs to requirements-syntax file lanes created by `from_requirements_txt`; this includes ordinary requirements and exclusion lists, while constraints and overrides retain separate constructors.
- UV's script lock naming must be modeled with native path types, not UTF-8 conversion.
- Lockfile-content substring detection is too broad.
- Missing paths remain owned by the existing missing-file diagnostic.
- Constraints and overrides require distinct error semantics despite sharing the parser implementation.
