#!/usr/bin/env python3
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
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


def tensor_payload(path: Path, name: str = "tensor") -> bytes:
    serialized = path.read_bytes()
    if len(serialized) < 8:
        raise AssertionError(f"{path} is too short to contain a safetensors header")

    header_length = int.from_bytes(serialized[:8], byteorder="little", signed=False)
    header_end = 8 + header_length
    if header_end > len(serialized):
        raise AssertionError(
            f"{path} declares a {header_length}-byte header beyond end of file"
        )

    header = json.loads(serialized[8:header_end])
    start, end = header[name]["data_offsets"]
    payload_start = header_end + start
    payload_end = header_end + end
    if payload_end > len(serialized):
        raise AssertionError(f"{path} tensor payload extends beyond end of file")
    return serialized[payload_start:payload_end]


def main() -> None:
    expected = np.array([0.25, -1.5, 3.0, 1024.125], dtype=np.float32)
    explicit_big_endian = expected.astype(">f4")
    explicit_little_endian = expected.astype("<f4")
    little_endian_bytes = explicit_little_endian.tobytes(order="C")
    big_endian_bytes = explicit_big_endian.tobytes(order="C")
    assert little_endian_bytes != big_endian_bytes

    with tempfile.TemporaryDirectory(prefix="safetensors-endian-") as temp:
        root = Path(temp)

        high_level = root / "high-level.safetensors"
        save_file({"tensor": explicit_big_endian}, high_level)
        assert tensor_payload(high_level) == little_endian_bytes

        direct_little = root / "direct-little.safetensors"
        write_direct(explicit_little_endian, direct_little)
        assert tensor_payload(direct_little) == little_endian_bytes

        direct_big = root / "direct-big.safetensors"
        write_direct(explicit_big_endian, direct_big)
        direct_big_payload = tensor_payload(direct_big)
        assert direct_big_payload == big_endian_bytes
        assert direct_big_payload != little_endian_bytes

        converted = explicit_big_endian.byteswap(inplace=False).view(
            explicit_big_endian.dtype.newbyteorder("<")
        )
        direct_converted = root / "direct-converted.safetensors"
        write_direct(converted, direct_converted)
        assert tensor_payload(direct_converted) == little_endian_bytes

        threaded_paths = [root / f"thread-{index}.safetensors" for index in range(8)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda path: write_direct(explicit_big_endian, path), threaded_paths))

        for path in threaded_paths:
            assert tensor_payload(path) == direct_big_payload

        # These checks describe the current little-endian consumer behavior, but
        # the writer classification above does not depend on NumPy interpretation.
        if sys.byteorder == "little":
            np.testing.assert_array_equal(load_file(high_level)["tensor"], expected)
            np.testing.assert_array_equal(load_file(direct_little)["tensor"], expected)
            np.testing.assert_array_equal(load_file(direct_converted)["tensor"], expected)
            assert not np.array_equal(load_file(direct_big)["tensor"], expected)

        print("high-level big-endian input: file payload normalized to little-endian")
        print("direct little-endian TensorSpec input: little-endian payload")
        print("direct big-endian TensorSpec input: source bytes copied unchanged")
        print("threaded direct writes: byte-identical to single-thread direct write")
        print("classification: raw-pointer byte-order contract precedes concurrency")


if __name__ == "__main__":
    main()
