# Linux Fieldwork

A GitHub-hosted workbench for investigating Linux and Debian projects from a phone-first workflow.

## Current campaign

[Campaign 0001: Rootless bootstrap lab](campaigns/0001-rootless-bootstrap/README.md) studies reproducible Debian root filesystems across rootless execution, architecture boundaries, package transitions, container runtimes, and virtual machines.

The first contained target is Debian bug `#1141078`, an important `mmdebstrap` autopkgtest failure recorded against version `1.5.7-3`. Investigation stays inside this repository until explicit upstream-contact authorization is given.

## Hard Linux notebook

[Hard Linux notes](notes/hard-linux/README.md) explain the mechanisms beneath distributions and container products. The opening note connects Debian bootstrap work to Docker and OCI images, namespaces, cgroups, mounts, capabilities, seccomp, UID/GID mapping, and root filesystem metadata.

## Laboratory tools

Create metadata manifests directly from root filesystem tar archives:

```bash
python3 tools/tar_manifest.py left.tar -o left.manifest.jsonl
python3 tools/tar_manifest.py right.tar -o right.manifest.jsonl
python3 tools/manifest_diff.py left.manifest.jsonl right.manifest.jsonl
```

Capture the host facts that decide many rootless failures:

```bash
bash scripts/capture-linux-context.sh context.md
```

Run the tool tests:

```bash
python3 -m unittest discover -s tests -v
bash -n scripts/capture-linux-context.sh
```

## Working source trees

Imported upstream projects live under `upstream/`. Their original files, licensing information, and executable permissions are preserved. Import metadata records the upstream repository, requested revision, resolved commit, and import time.

This repository is a working copy for research, testing, and candidate patches. It is separate from the upstream Debian repositories and does not contact maintainers automatically.
