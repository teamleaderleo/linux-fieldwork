#!/usr/bin/env python3
"""Reduced discriminator for util-linux libblkid Minix version detection.

Source boundary: util-linux/util-linux ce6a4ea30e0f6b46b9689931cab897c6bd866bd6
Model host: little-endian, to make byte order explicit.

This copies only the get_minix_version() decision relevant to v1/v2/v3 magic
and demonstrates the difference between the current and candidate fallback.
"""

import struct

MINIX_SUPER_MAGIC = 0x137F
MINIX_SUPER_MAGIC2 = 0x138F
MINIX2_SUPER_MAGIC = 0x2468
MINIX2_SUPER_MAGIC2 = 0x2478
MINIX3_SUPER_MAGIC = 0x4D5A


def swab16(value: int) -> int:
    return ((value & 0xFF) << 8) | ((value >> 8) & 0xFF)


def magics(data: bytes) -> tuple[int, int]:
    # minix_super_block.s_magic is at offset 0x10.
    # minix3_super_block.s_magic is at offset 0x18.
    return struct.unpack_from("<H", data, 0x10)[0], struct.unpack_from("<H", data, 0x18)[0]


def current_version(data: bytes) -> tuple[int, int]:
    sb_magic, sb3_magic = magics(data)
    other_endian = 0

    if sb_magic in (MINIX_SUPER_MAGIC, MINIX_SUPER_MAGIC2):
        return 1, other_endian
    if sb_magic in (MINIX2_SUPER_MAGIC, MINIX2_SUPER_MAGIC2):
        return 2, other_endian
    if sb3_magic == MINIX3_SUPER_MAGIC:
        return 3, other_endian

    other_endian = 1
    if swab16(sb_magic) in (MINIX_SUPER_MAGIC, MINIX_SUPER_MAGIC2):
        return 1, other_endian
    if swab16(sb_magic) in (MINIX2_SUPER_MAGIC, MINIX2_SUPER_MAGIC2):
        return 2, other_endian

    # Exact current v3 fallback: it repeats the native-order comparison.
    if sb3_magic == MINIX3_SUPER_MAGIC:
        return 3, other_endian

    return -1, other_endian


def candidate_version(data: bytes) -> tuple[int, int]:
    sb_magic, sb3_magic = magics(data)
    other_endian = 0

    if sb_magic in (MINIX_SUPER_MAGIC, MINIX_SUPER_MAGIC2):
        return 1, other_endian
    if sb_magic in (MINIX2_SUPER_MAGIC, MINIX2_SUPER_MAGIC2):
        return 2, other_endian
    if sb3_magic == MINIX3_SUPER_MAGIC:
        return 3, other_endian

    other_endian = 1
    if swab16(sb_magic) in (MINIX_SUPER_MAGIC, MINIX_SUPER_MAGIC2):
        return 1, other_endian
    if swab16(sb_magic) in (MINIX2_SUPER_MAGIC, MINIX2_SUPER_MAGIC2):
        return 2, other_endian
    if swab16(sb3_magic) == MINIX3_SUPER_MAGIC:
        return 3, other_endian

    return -1, other_endian


def fixture(offset: int, value: bytes) -> bytes:
    data = bytearray(64)
    data[offset:offset + len(value)] = value
    return bytes(data)


def main() -> None:
    cases = [
        ("v1 LE", fixture(0x10, b"\x7f\x13"), (1, 0), (1, 0)),
        ("v1 BE", fixture(0x10, b"\x13\x7f"), (1, 1), (1, 1)),
        ("v3 LE", fixture(0x18, b"\x5a\x4d"), (3, 0), (3, 0)),
        ("v3 BE", fixture(0x18, b"\x4d\x5a"), (-1, 1), (3, 1)),
    ]

    for name, data, expected_current, expected_candidate in cases:
        current = current_version(data)
        candidate = candidate_version(data)
        print(f"{name}: current={current} candidate={candidate}")
        assert current == expected_current
        assert candidate == expected_candidate

    print("PASS: current rejects only opposite-endian v3; candidate changes only that cell")


if __name__ == "__main__":
    main()
