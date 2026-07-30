from __future__ import annotations

import pathlib
import subprocess
import tempfile

import test_mmdebstrap_caching_proxy_cache_key_distinctions as base_tests


class CachingProxyContentLengthSpellingTest(
    base_tests.CachingProxyCacheKeyDistinctionsTest
):
    def setUp(self) -> None:
        super().setUp()
        strict_patch = base_tests.ROOT / (
            "investigations/mmdebstrap-caching-proxy-containment/"
            "0002-reject-nondecimal-content-length.patch"
        )
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(strict_patch)],
            cwd=self.candidate_root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

    def test_nondecimal_zero_spellings_are_rejected_before_origin_contact(self) -> None:
        with base_tests.running_server(base_tests.DistinguishingOrigin) as origin:
            host = f"127.0.0.1:{origin.server_address[1]}"
            target = f"http://{host}/debian/pool/pkg.deb"
            invalid_values = ("+0", "-0", "0x0", "")
            with self.running_proxy(self.candidate_source, "candidate-length-spelling") as (
                proxy,
                old_cache,
                new_cache,
            ):
                for value in invalid_values:
                    with self.subTest(value=value):
                        response = self.raw_request(
                            int(proxy.server_address[1]),
                            target,
                            [
                                f"Host: {host}",
                                f"Content-Length: {value}",
                                "Connection: close",
                            ],
                        )
                        self.assertEqual(self.status(response), 400)

        self.assertEqual(origin.request_count, 0)
        self.assertEqual(list(old_cache.rglob("*")), [])
        self.assertEqual(list(new_cache.rglob("*")), [])

    def test_decimal_zero_with_leading_zeroes_remains_bodyless(self) -> None:
        with base_tests.running_server(base_tests.DistinguishingOrigin) as origin:
            host = f"127.0.0.1:{origin.server_address[1]}"
            target = f"http://{host}/debian/pool/pkg.deb"
            with self.running_proxy(self.candidate_source, "candidate-length-zero") as (
                proxy,
                _old_cache,
                new_cache,
            ):
                response = self.raw_request(
                    int(proxy.server_address[1]),
                    target,
                    [f"Host: {host}", "Content-Length: 00", "Connection: close"],
                )

        self.assertEqual(self.status(response), 200)
        self.assertEqual(origin.request_count, 1)
        self.assertEqual(
            (new_cache / "debian/pool/pkg.deb").read_bytes(), b"ordinary\n"
        )

    def test_strict_patch_source_contract(self) -> None:
        source = self.candidate_source.read_text(encoding="utf-8")
        self.assertIn('character not in "0123456789"', source)
        self.assertNotIn(
            'int(content_length_values[0]) if content_length_values else 0', source
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
