from __future__ import annotations

import concurrent.futures
import contextlib
import pathlib
import tempfile
import threading
import unittest

import test_caching_proxy_complete_stack as complete


OUTSIDE_SECRET = b"outside-cache-secret\n"


class CachingProxyParentSwapRaceTest(complete.CachingProxyCompleteStackTest):
    def test_validated_old_cache_parent_swap_reaches_outside_file(self) -> None:
        module = complete.load_module(self.candidate, "lf_parent_swap_read")
        validated = threading.Event()
        release = threading.Event()
        call_lock = threading.Lock()
        call_count = 0
        original_request_context = module.request_context

        def pausing_request_context(root, request_target, host):
            nonlocal call_count
            result = original_request_context(root, request_target, host)
            with call_lock:
                call_count += 1
                current_call = call_count
            # The handler validates oldcachedir first and newcachedir second.
            # Pause after both paths resolve and before any cache existence check.
            if current_call == 2:
                validated.set()
                if not release.wait(timeout=10):
                    raise TimeoutError("parent-swap read barrier timed out")
            return result

        module.request_context = pausing_request_context
        try:
            with complete.running_http_server(
                complete.FixedOrigin
            ) as origin, tempfile.TemporaryDirectory(
                prefix="complete-parent-swap-read-"
            ) as tmp:
                root = pathlib.Path(tmp)
                old_cache = root / "old"
                new_cache = root / "new"
                checked_parent = old_cache / "pool"
                checked_parent.mkdir(parents=True)
                outside = root / "outside-read"
                outside.mkdir()
                outside_object = outside / "object.deb"
                outside_object.write_bytes(OUTSIDE_SECRET)

                host = f"127.0.0.1:{origin.server_address[1]}"
                target = f"http://{host}/pool/object.deb"
                request = complete.request_bytes(
                    "GET", target, [("Host", host), ("Connection", "close")]
                )

                with complete.running_proxy(
                    module, old_cache, new_cache
                ) as proxy, concurrent.futures.ThreadPoolExecutor(
                    max_workers=1
                ) as pool:
                    response_future = pool.submit(complete.raw_request, proxy, request)
                    self.assertTrue(validated.wait(timeout=5))

                    preserved_parent = old_cache / "pool-validated"
                    checked_parent.rename(preserved_parent)
                    checked_parent.symlink_to(outside, target_is_directory=True)
                    release.set()
                    response = response_future.result(timeout=15)

                self.assertEqual(complete.statuses(response), [200])
                self.assertEqual(complete.body_bytes(response), OUTSIDE_SECRET)
                self.assertEqual(origin.request_count, 0)
                self.assertTrue(checked_parent.is_symlink())
                self.assertEqual(list(preserved_parent.iterdir()), [])
                self.assertEqual(outside_object.read_bytes(), OUTSIDE_SECRET)
                copied = new_cache / "pool/object.deb"
                self.assertEqual(copied.read_bytes(), OUTSIDE_SECRET)
                complete.wait_for_no_temporaries(copied.parent)
        finally:
            release.set()
            module.request_context = original_request_context

    def test_validated_new_cache_parent_swap_publishes_outside_root(self) -> None:
        module = complete.load_module(self.candidate, "lf_parent_swap_write")
        entered_destination = threading.Event()
        release = threading.Event()
        original_cache_destination = module.cache_destination

        @contextlib.contextmanager
        def pausing_cache_destination(path):
            # request_context() has already returned the resolved newpath.
            # Pause before new_cache_temporary() and os.replace() re-traverse it.
            entered_destination.set()
            if not release.wait(timeout=10):
                raise TimeoutError("parent-swap publication barrier timed out")
            with original_cache_destination(path) as cache:
                yield cache

        module.cache_destination = pausing_cache_destination
        try:
            with complete.running_http_server(
                complete.FixedOrigin
            ) as origin, tempfile.TemporaryDirectory(
                prefix="complete-parent-swap-write-"
            ) as tmp:
                root = pathlib.Path(tmp)
                old_cache = root / "old"
                new_cache = root / "new"
                checked_parent = new_cache / "pool"
                checked_parent.mkdir(parents=True)
                outside = root / "outside-write"
                outside.mkdir()
                sentinel = outside / "sentinel"
                sentinel.write_bytes(b"preserve me\n")

                host = f"127.0.0.1:{origin.server_address[1]}"
                target = f"http://{host}/pool/object.deb"
                request = complete.request_bytes(
                    "GET", target, [("Host", host), ("Connection", "close")]
                )

                with complete.running_proxy(
                    module, old_cache, new_cache
                ) as proxy, concurrent.futures.ThreadPoolExecutor(
                    max_workers=1
                ) as pool:
                    response_future = pool.submit(complete.raw_request, proxy, request)
                    self.assertTrue(entered_destination.wait(timeout=5))

                    preserved_parent = new_cache / "pool-validated"
                    checked_parent.rename(preserved_parent)
                    checked_parent.symlink_to(outside, target_is_directory=True)
                    release.set()
                    response = response_future.result(timeout=15)

                self.assertEqual(complete.statuses(response), [200])
                self.assertEqual(complete.body_bytes(response), complete.PAYLOAD)
                self.assertEqual(origin.request_count, 1)
                self.assertTrue(checked_parent.is_symlink())
                self.assertEqual(list(preserved_parent.iterdir()), [])
                self.assertEqual(sentinel.read_bytes(), b"preserve me\n")
                outside_object = outside / "object.deb"
                self.assertEqual(outside_object.read_bytes(), complete.PAYLOAD)
                complete.wait_for_no_temporaries(outside)
        finally:
            release.set()
            module.cache_destination = original_cache_destination


if __name__ == "__main__":
    unittest.main()
