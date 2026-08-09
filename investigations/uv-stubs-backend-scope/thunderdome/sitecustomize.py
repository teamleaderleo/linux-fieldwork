"""Harness bootstrap for the normalized UV thunderdome.

Python imports this module before executing the sibling transform script. Install
`rustfmt` for UV's pinned toolchain so the workflow can normalize both generated
candidate trees without changing either candidate's repository diff.
"""

from __future__ import annotations

import subprocess

subprocess.run(["rustup", "component", "add", "rustfmt"], check=True)
