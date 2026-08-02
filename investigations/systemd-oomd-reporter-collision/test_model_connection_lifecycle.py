#!/usr/bin/env python3
from __future__ import annotations

import unittest

from model_connection_lifecycle import (
    ConnectionPolicyModel,
    ReporterProtocolError,
    StaleReporterGeneration,
)
from model_policy import Authority, EqualAuthorityConflict, Policy, ReporterKind


PATH = "/user.slice/user-4711.slice/user@4711.service"
OTHER_PATH = "/user.slice/user-4711.slice/session-1.scope"
PRESSURE = "ManagedOOMMemoryPressure"
SYSTEM = Authority(ReporterKind.SYSTEM_MANAGER, 0)
USER = Authority(ReporterKind.USER_MANAGER, 4711)
OTHER_USER = Authority(ReporterKind.USER_MANAGER, 4712)
SYSTEM_POLICY = Policy("kill", limit=5000, duration_usec=30_000_000)
USER_POLICY = Policy("kill", limit=7000, duration_usec=5_000_000)
OTHER_POLICY = Policy("kill", limit=6000, duration_usec=10_000_000)


class ConnectionLifecycleTest(unittest.TestCase):
    def effective(self, model: ConnectionPolicyModel, path: str = PATH):
        value = model.policy.get_effective(PRESSURE, path)
        self.assertIsNotNone(value)
        return value

    def test_empty_reconnect_snapshot_clears_old_policy_before_old_disconnect(self) -> None:
        model = ConnectionPolicyModel()
        model.connect(USER, "old")
        model.replace_snapshot(USER, "old", [(PRESSURE, PATH, USER_POLICY)])
        model.connect(USER, "new")
        model.replace_snapshot(USER, "new", [])

        self.assertIsNone(model.policy.get_effective(PRESSURE, PATH))
        model.disconnect(USER, "old")
        self.assertIsNone(model.policy.get_effective(PRESSURE, PATH))
        self.assertEqual(model.current_link(USER), "new")

    def test_stale_old_link_update_is_rejected_after_new_snapshot(self) -> None:
        model = ConnectionPolicyModel()
        model.connect(USER, "old")
        model.replace_snapshot(USER, "old", [(PRESSURE, PATH, USER_POLICY)])
        model.connect(USER, "new")
        model.replace_snapshot(USER, "new", [(PRESSURE, PATH, OTHER_POLICY)])

        with self.assertRaises(StaleReporterGeneration):
            model.update_from_link(USER, "old", PRESSURE, PATH, None)
        self.assertEqual(self.effective(model).policy, OTHER_POLICY)

    def test_stale_disconnect_does_not_remove_new_generation_policy(self) -> None:
        model = ConnectionPolicyModel()
        model.connect(USER, "old")
        model.replace_snapshot(USER, "old", [(PRESSURE, PATH, USER_POLICY)])
        model.connect(USER, "new")
        model.replace_snapshot(USER, "new", [(PRESSURE, PATH, OTHER_POLICY)])
        model.disconnect(USER, "old")

        self.assertEqual(self.effective(model).policy, OTHER_POLICY)
        self.assertEqual(model.current_link(USER), "new")

    def test_current_disconnect_withdraws_even_if_stale_link_remains(self) -> None:
        model = ConnectionPolicyModel()
        model.connect(USER, "old")
        model.replace_snapshot(USER, "old", [(PRESSURE, PATH, USER_POLICY)])
        model.connect(USER, "new")
        model.replace_snapshot(USER, "new", [(PRESSURE, PATH, OTHER_POLICY)])
        model.disconnect(USER, "new")

        self.assertIsNone(model.policy.get_effective(PRESSURE, PATH))
        self.assertIsNone(model.current_link(USER))
        with self.assertRaises(StaleReporterGeneration):
            model.update_from_link(USER, "old", PRESSURE, PATH, USER_POLICY)

    def test_pending_disconnect_leaves_current_generation_unchanged(self) -> None:
        model = ConnectionPolicyModel()
        model.connect(USER, "current")
        model.replace_snapshot(USER, "current", [(PRESSURE, PATH, USER_POLICY)])
        model.connect(USER, "pending")
        model.disconnect(USER, "pending")

        self.assertEqual(self.effective(model).policy, USER_POLICY)
        self.assertEqual(model.current_link(USER), "current")

    def test_snapshot_replaces_paths_missing_from_new_complete_state(self) -> None:
        model = ConnectionPolicyModel()
        model.connect(USER, "old")
        model.replace_snapshot(
            USER,
            "old",
            [(PRESSURE, PATH, USER_POLICY), (PRESSURE, OTHER_PATH, OTHER_POLICY)],
        )
        model.connect(USER, "new")
        model.replace_snapshot(USER, "new", [(PRESSURE, PATH, SYSTEM_POLICY)])

        self.assertEqual(self.effective(model).policy, SYSTEM_POLICY)
        self.assertIsNone(model.policy.get_effective(PRESSURE, OTHER_PATH))

    def test_failed_snapshot_rolls_back_previous_generation_and_policy(self) -> None:
        model = ConnectionPolicyModel()
        model.connect(USER, "old")
        model.replace_snapshot(USER, "old", [(PRESSURE, PATH, USER_POLICY)])

        model.connect(OTHER_USER, "other")
        model.replace_snapshot(OTHER_USER, "other", [(PRESSURE, PATH, OTHER_POLICY)])

        model.connect(USER, "new")
        with self.assertRaises(EqualAuthorityConflict):
            model.replace_snapshot(USER, "new", [(PRESSURE, PATH, SYSTEM_POLICY)])

        self.assertEqual(model.current_link(USER), "old")
        self.assertEqual(
            model.policy.contributors(PRESSURE, PATH),
            [(USER, USER_POLICY), (OTHER_USER, OTHER_POLICY)],
        )

    def test_first_call_must_be_snapshot_and_snapshot_happens_once(self) -> None:
        model = ConnectionPolicyModel()
        model.connect(USER, "link")
        with self.assertRaises(ReporterProtocolError):
            model.update_from_link(USER, "link", PRESSURE, PATH, USER_POLICY)
        model.replace_snapshot(USER, "link", [])
        with self.assertRaises(ReporterProtocolError):
            model.replace_snapshot(USER, "link", [])

    def test_system_stream_termination_reveals_user_fallback(self) -> None:
        model = ConnectionPolicyModel()
        model.connect(USER, "user")
        model.replace_snapshot(USER, "user", [(PRESSURE, PATH, USER_POLICY)])
        model.connect(SYSTEM, "pid1")
        model.replace_snapshot(SYSTEM, "pid1", [(PRESSURE, PATH, SYSTEM_POLICY)])
        self.assertEqual(self.effective(model).authority, SYSTEM)

        model.disconnect(SYSTEM, "pid1")
        effective = self.effective(model)
        self.assertEqual(effective.authority, USER)
        self.assertEqual(effective.policy, USER_POLICY)

    def test_system_empty_reconnect_snapshot_replaces_old_system_state(self) -> None:
        model = ConnectionPolicyModel()
        model.connect(SYSTEM, "pid1-old")
        model.replace_snapshot(SYSTEM, "pid1-old", [(PRESSURE, PATH, SYSTEM_POLICY)])
        model.connect(SYSTEM, "pid1-new")
        model.replace_snapshot(SYSTEM, "pid1-new", [])

        self.assertIsNone(model.policy.get_effective(PRESSURE, PATH))
        model.disconnect(SYSTEM, "pid1-old")
        self.assertIsNone(model.policy.get_effective(PRESSURE, PATH))

    def test_generation_numbers_are_monotonic_per_authority(self) -> None:
        model = ConnectionPolicyModel()
        self.assertEqual(model.connect(USER, "one"), 1)
        self.assertEqual(model.connect(USER, "two"), 2)
        self.assertEqual(model.generation(USER, "one"), 1)
        self.assertEqual(model.generation(USER, "two"), 2)

    def test_duplicate_snapshot_keys_are_rejected_without_state_change(self) -> None:
        model = ConnectionPolicyModel()
        model.connect(USER, "old")
        model.replace_snapshot(USER, "old", [(PRESSURE, PATH, USER_POLICY)])
        model.connect(USER, "new")

        with self.assertRaises(ReporterProtocolError):
            model.replace_snapshot(
                USER,
                "new",
                [(PRESSURE, PATH, USER_POLICY), (PRESSURE, PATH, OTHER_POLICY)],
            )

        self.assertEqual(model.current_link(USER), "old")
        self.assertEqual(self.effective(model).policy, USER_POLICY)


if __name__ == "__main__":
    unittest.main(verbosity=2)
