# Safetensors #812: TensorSpec byte order before concurrency

Upstream issue: `safetensors/safetensors#812`.

Exact source reviewed: `safetensors/safetensors@6eb4dc9a28ebce297606e0f4836bbf28839cacef`.

## TL;DR

The reported s390x test passes a native-endian NumPy buffer through the low-level raw-pointer `TensorSpec` API. On s390x that buffer is big-endian, while safetensors numeric payloads are little-endian. Source shows that `TensorSpec` records a dtype, shape, pointer, and byte length, then borrows the pointed-to bytes unchanged; the high-level NumPy wrapper separately byteswaps non-little-endian arrays before creating a `TensorSpec`.

The first distinguishing question is therefore byte ownership, not thread scheduling. The refined discriminator inspects the serialized tensor payload directly, independently of the platform-specific NumPy load path.

## Explain like I'm five

The test gives the serializer an address and says, “copy these bytes as a float32 tensor.” On a big-endian machine, those bytes are written in the opposite order from the safetensors file format. The raw-pointer API has no byte-order field, so it cannot know that a conversion is needed. Running four copies at once does not change that basic mismatch.

## Why care

A test named for GIL release currently fails during value comparison, which can misdirect work toward concurrency. Correctly assigning the first failure owner avoids adding synchronization to code whose actual input bytes are already incompatible with the file contract.

## Source ownership

At the reviewed source revision:

- `bindings/python/tests/test_threadable.py` creates native `np.float32` data and passes `tensor.ctypes.data` through `TensorSpec`.
- `bindings/python/src/lib.rs` stores only dtype, shape, raw pointer, and byte length. Its `View::data()` returns a borrowed byte slice without normalization.
- `bindings/python/py_src/safetensors/numpy.py` detects non-little-endian NumPy arrays and byteswaps them before constructing `TensorSpec`.

This establishes the mechanism. It does not yet establish the exact behavior of every reader on a native big-endian host.

## Deterministic discriminator

`endian_matrix.py` constructs explicit `>f4` and `<f4` arrays on any architecture and compares:

1. high-level NumPy save of big-endian input;
2. direct `TensorSpec` save of little-endian input;
3. direct `TensorSpec` save of big-endian input;
4. direct save after explicit conversion to little-endian;
5. concurrent direct saves of the same big-endian buffer.

The script parses the safetensors header itself and extracts the raw tensor payload. This avoids using `load_file()` to decide what the writer emitted.

Expected current result:

- the high-level path writes little-endian payload bytes;
- direct little-endian input writes the same little-endian bytes;
- direct big-endian input copies the big-endian source bytes unchanged;
- explicit conversion restores the little-endian payload;
- every threaded direct-big output is byte-identical to the single-thread direct-big output.

Only a difference between single-thread and threaded raw payloads would promote concurrency as an independent corruption defect.

## Run

The script requires a build or installation exposing the current public `TensorSpec` API:

```console
python3 endian_matrix.py
```

The current local environment has safetensors `0.7.0`, which does not expose `TensorSpec`; the refined matrix is therefore materialized but not executed here.

For the reported architecture, also retain the original concurrency timing assertion after correcting the input byte order:

```console
pytest -v bindings/python/tests/test_threadable.py::TestCase::test_serialize_file_releases_gil
```

## Candidate test correction

Keep the low-level `serialize_file` call so the GIL-release boundary remains under test, but ensure numeric buffers handed to `TensorSpec` are explicitly little-endian and remain alive for the complete call. Continue using the byte-order-independent `int8` tensor as a control.

A separate low-level API test should document or demonstrate that `TensorSpec.data_ptr` is byte-oriented and does not normalize endianness. That contract test should not be hidden inside a concurrency test.

## Remaining gates

1. Run `endian_matrix.py` against the exact reviewed source or a newer rebased head exposing `TensorSpec`.
2. Run the corrected thread test on emulated and, when available, native s390x.
3. Confirm the concurrency windows still overlap after explicit little-endian conversion.
4. Inspect both mmap and pread load backends on s390x as a separate reader-compatibility question.
5. Recheck current upstream overlap before selecting any source patch.

## Evidence boundary

Demonstrated by source: the raw-pointer path cannot infer NumPy byte order and borrows the supplied bytes unchanged; the high-level NumPy path performs byte swapping.

Not yet demonstrated by execution: the exact raw payload matrix on the current `TensorSpec` build, native s390x reader behavior, or the corrected GIL timing test.

No upstream contact or source correction is authorized.
