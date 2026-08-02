#!/usr/bin/env python3
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile

import numpy as np
from safetensors import TensorSpec, serialize_file
from safetensors.numpy import load_file, save_file


def direct_spec(array: np.ndarray) -> TensorSpec:
    return TensorSpec(
        dtype=array.dtype.name,
        shape=array.shape,
        data_ptr=array.ctypes.data,
        data_len=array.nbytes,
    )


def write_direct(array: np.ndarray, path: Path) -> None:
    serialize_file({"tensor": direct_spec(array)}, path)


def main() -> None:
    expected = np.array([0.25, -1.5, 3.0, 1024.125], dtype=np.float32)
    explicit_big_endian = expected.astype(">f4")
    explicit_little_endian = expected.astype("<f4")

    with tempfile.TemporaryDirectory(prefix="safetensors-endian-") as temp:
        root = Path(temp)

        high_level = root / "high-level.safetensors"
        save_file({"tensor": explicit_big_endian}, high_level)
        np.testing.assert_array_equal(load_file(high_level)["tensor"], expected)

        direct_little = root / "direct-little.safetensors"
        write_direct(explicit_little_endian, direct_little)
        np.testing.assert_array_equal(load_file(direct_little)["tensor"], expected)

        direct_big = root / "direct-big.safetensors"
        write_direct(explicit_big_endian, direct_big)
        loaded_big = load_file(direct_big)["tensor"]
        assert not np.array_equal(loaded_big, expected), (
            "Direct TensorSpec unexpectedly normalized big-endian bytes"
        )

        converted = explicit_big_endian.byteswap(inplace=False).view(
            explicit_big_endian.dtype.newbyteorder("<")
        )
        direct_converted = root / "direct-converted.safetensors"
        write_direct(converted, direct_converted)
        np.testing.assert_array_equal(load_file(direct_converted)["tensor"], expected)

        threaded_paths = [root / f"thread-{index}.safetensors" for index in range(8)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda path: write_direct(explicit_big_endian, path), threaded_paths))

        threaded_values = [load_file(path)["tensor"] for path in threaded_paths]
        for value in threaded_values:
            np.testing.assert_array_equal(value, loaded_big)
            assert not np.array_equal(value, expected)

        print("high-level big-endian path: normalized correctly")
        print("direct little-endian TensorSpec path: correct")
        print("direct big-endian TensorSpec path: deterministically byte-swapped")
        print("threaded direct writes: identical to single-thread direct write")
        print("classification: byte-order contract precedes concurrency investigation")


if __name__ == "__main__":
    main()
