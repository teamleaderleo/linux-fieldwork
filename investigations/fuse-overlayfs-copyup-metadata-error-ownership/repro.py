#!/usr/bin/env python3
"""Reduced state model for copy-up metadata failure ownership."""

EIO = 5


def current_copyup(metadata_result: int):
    temp_created = True
    data_copied = True
    # Current Rust: let _ = metadata operation; then rename/publish.
    published = True
    return {"metadata_errno": metadata_result, "published": published, "temp_left": False}


def candidate_copyup(metadata_result: int):
    temp_created = True
    data_copied = True
    if metadata_result:
        # Candidate must unlink temp and surface the error before rename.
        return {"metadata_errno": metadata_result, "published": False, "temp_left": False}
    return {"metadata_errno": 0, "published": True, "temp_left": False}


for gate in ["futimens", "copy_xattr", "fchmod"]:
    print(gate, "current", current_copyup(EIO), "candidate", candidate_copyup(EIO))
