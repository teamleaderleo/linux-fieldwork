# Independent review packet: UV stub-only backend capability model

State: `READY FOR INDEPENDENT CHALLENGE`

Primary design carrier: internal PR #475 (`investigations/uv-stubs-backend-scope/DESIGN_DIRECTION.md`)

Research inputs: #458 and #459.

External context only:

- https://redirect.github.com/astral-sh/uv/issues/19663
- https://redirect.github.com/astral-sh/uv/pull/19671

No upstream mutation is authorized by this packet.

## Review question

Try to falsify the proposed model rather than merely restating it:

> A `*-stubs` project name should select stub-only project semantics first; the chosen build backend should then either express that project with direct support, backend-specific configuration/version floors, or reject the combination.

## Specific challenges

1. Is treating `*-stubs` as a project kind during `uv init` the right semantic boundary, or is there a credible case where a user intentionally wants an ordinary runtime package named `*-stubs`?
2. Are backend-specific minimum versions the smallest compatibility boundary, or should UV raise the general backend template floor instead? Pay special attention to Flit 4 and setuptools 69.
3. Should UV reject `foo-stubs + scikit` under the current Scikit/CMake starter semantics, or is adding the pure-stub Scikit configuration still idiomatic within the existing selector?
4. Is early rejection for Maturin preferable to generating a project and allowing the backend to fail later?
5. Does any supported backend require runtime metadata, scripts, or package layout that contradicts the common stub-only source tree?
6. Can the implementation be factored as one project-kind decision plus a backend capability/config adapter without scattering suffix checks across initialization code?

## Evidence standard

For any objection, identify the exact premise it changes and support it with one of:

- current backend/UV source;
- backend documentation;
- a minimal generated project and wheel payload;
- a counterexample that makes the proposed policy produce the wrong user-visible project.

A useful negative review is welcome. The goal is to find the smallest model that survives counterexamples, not to approve PR #475.

## Current evidence boundary

#458 has complete executed Hatch/Poetry/Flit wheel evidence. #459 has executed PDM and setuptools evidence; the Scikit/Maturin hosted rows are being rerun after repairing the carrier's expected-failure handling. Treat source-backed conclusions separately from completed artifact proof until that rerun lands.
