# uv workspace member index persistence authority

State: `SOURCE-MAPPED — REPRODUCTION NOT YET MATERIALIZED`  
Worker or variant: `LF-R02`  
Public contact authorized: `false`

## Bounded question

When `uv add --package <member> --index ...` resolves successfully using command-line indexes, why are implicit index definitions persisted into the selected member's `pyproject.toml` even though later workspace resolution does not consult that file for workspace index configuration?

## Exact identities

| Item | Value |
| --- | --- |
| Public repository | `astral-sh/uv` |
| Exact inspected head | `79bbface771210df216b738e9bdc7df95e5a9e6b` |
| Public issue | `astral-sh/uv#20678` |
| Issue state | open, unassigned, bug label |
| Equivalent PR found | none by issue-number search |
| Command owner | `crates/uv/src/commands/project/add.rs` |
| Mutation owner | `crates/uv-workspace/src/pyproject_mut.rs` |

## Source observation

`uv add` discovers a `VirtualProject` for the selected package when `--package` is supplied. In the normal non-`--workspace` mutation path, it constructs `PyProjectTomlMut` from:

```text
project.pyproject_toml().raw
```

That is the selected member's project file.

After resolution, command-line indexes are converted into `IndexLocations`, iterated, and passed to:

```text
toml.add_index(index, root_dir)
```

`PyProjectTomlMut::add_index()` writes `[[tool.uv.index]]` into whichever TOML document it was given. It does not know whether that document owns workspace index configuration.

A separate `use_workspace` path constructs its mutable TOML from:

```text
project.workspace().pyproject_toml().raw
```

The source boundary therefore matches the report: command-line index state is used for the current resolution, but normal `--package` persistence targets the member file while workspace index discovery is rooted elsewhere.

## First reproduction matrix

Create a synthetic workspace with root package `root`, member `child`, and a local PEP 503 index serving two tiny wheels.

Run these cases on exact head:

1. `uv add --package child --index private=<local-url> dependency`;
2. the same command with two indexes;
3. one named index selected as the dependency source;
4. `uv add --workspace --index ...` where supported;
5. rerun `uv lock --offline` after stopping the local index;
6. inspect root and member `pyproject.toml`, `uv.lock`, and `uv lock --show-settings` or equivalent resolved settings.

Required distinction:

- an explicit source binding may legitimately live with the member dependency declaration;
- an implicit index intended for workspace resolution must be persisted where later workspace discovery reads it;
- multiple command-line indexes must not be silently written into a non-authoritative file;
- a one-shot index may instead be rejected from persistence with a clear diagnostic if no durable owner is unambiguous.

## Candidate policies

Compare, do not assume:

1. persist all implicit indexes at the workspace root;
2. persist only a single named index when it becomes an explicit source and reject or warn on the rest;
3. require `--workspace` for durable workspace index mutation;
4. treat command-line indexes as invocation-only unless an explicit persistence flag is supplied;
5. update both root index configuration and member source binding when both are required.

A winning policy must avoid leaking credentials, preserve index ordering and explicit/default semantics, and keep scripts and non-workspace projects unchanged.

## Stop and promotion rules

Promote after a local index fixture demonstrates that the persisted member configuration is ignored by a later command and one ownership policy passes the matrix. Stop if a current equivalent PR appears or maintainer guidance defines command-line indexes as intentionally invocation-only.

## Authority

Controlled source reading and Fieldwork records are authorized. No public issue, pull request, comment, review, reaction, or email has occurred.
