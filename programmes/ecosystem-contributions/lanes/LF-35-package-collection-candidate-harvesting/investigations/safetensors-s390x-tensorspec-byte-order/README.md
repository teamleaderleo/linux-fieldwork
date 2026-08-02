# Safetensors #812: TensorSpec byte order before concurrency

Upstream issue: `safetensors/safetensors#812`.

## Current classification

The reported test uses the low-level `TensorSpec` API directly with NumPy data pointers. On a native big-endian target, a `np.float32` array exposes big-endian bytes. Safetensors files store numeric tensor bytes in little-endian order.

The high-level `safetensors.numpy.save_file` path detects non-little-endian arrays and byteswaps them before constructing `TensorSpec`. The direct `TensorSpec` path borrows the supplied bytes unchanged. Therefore the current s390x result does not by itself show concurrent corruption.

## Deterministic discriminator

`endian_matrix.py` runs on little-endian hosts by constructing explicit `>f4` arrays. It compares:

1. high-level save of big-endian input;
2. direct `TensorSpec` save of little-endian input;
3. direct `TensorSpec` save of big-endian input;
4. direct save after explicit conversion to little-endian;
5. concurrent direct saves of the same big-endian buffer.

Expected current result:

- high-level and direct-little paths round-trip correctly;
- direct-big round-trips to deterministically wrong values;
- every threaded direct-big output matches the single-thread direct-big output.

That result makes byte-order contract the first owner. Only a mismatch between single-thread and multithread direct writes would promote concurrency as an independent defect.

## Run

The script requires a build or installation exposing the current public `TensorSpec` API:

```console
python3 endian_matrix.py
```

## Candidate decisions after execution

- Document that `TensorSpec.data_ptr` must reference little-endian bytes.
- Reject non-native byte order at a higher-level wrapper where dtype byte order is available.
- Replace raw pointer metadata with a buffer object that can retain byte-order information.
- Correct the upstream test to use the high-level NumPy wrapper or explicit little-endian conversion if raw `TensorSpec` is intentionally byte-oriented.

No upstream contact or source correction is selected yet.
