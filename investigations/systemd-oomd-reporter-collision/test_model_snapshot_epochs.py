#!/usr/bin/env python3
from __future__ import annotations

import unittest

from model_connection_lifecycle import ConnectionPolicyModel
from model_policy import Authority, Policy, ReporterKind


PATH = "/user.slice/user-4711.slice/user@4711.service"
PRESSURE = "ManagedOOMMemoryPressure"
USER = Authority(ReporterKind.USER_MANAGER, 4711)
POLICY = Policy("kill", limit=7000, duration_usec=5_000_000)
CHANGED_POLICY = Policy("kill", limit=6500, duration_usec=5_000_000)


class SnapshotEpochTest(unittest.TestCase):
    def test_identical_new_generation_snapshot_preserves_effective_epoch(self) -> None:
        model = ConnectionPolicyModel()
        model.connect(USER, "old")
        model.replace_snapshot(USER, "old", [(PRESSURE, PATH, POLICY)])
        before = model.policy.get_effective(PRESSURE, PATH)
        self.assertIsNotNone(before)

        model.connect(USER, "new")
        model.replace_snapshot(USER, "new", [(PRESSURE, PATH, POLICY)])
        after = model.policy.get_effective(PRESSURE, PATH)
        self.assertIsNotNone(after)

        self.assertEqual(after.authority, before.authority)
        self.assertEqual(after.policy, before.policy)
        self.assertEqual(after.epoch, before.epoch)

    def test_changed_new_generation_snapshot_advances_effective_epoch_once(self) -> None:
        model = ConnectionPolicyModel()
        model.connect(USER, "old")
        model.replace_snapshot(USER, "old", [(PRESSURE, PATH, POLICY)])
        before = model.policy.get_effective(PRESSURE, PATH)
        self.assertIsNotNone(before)

        model.connect(USER, "new")
        model.replace_snapshot(USER, "new", [(PRESSURE, PATH, CHANGED_POLICY)])
        after = model.policy.get_effective(PRESSURE, PATH)
        self.assertIsNotNone(after)

        self.assertEqual(after.epoch, before.epoch + 1)
        self.assertEqual(after.policy, CHANGED_POLICY)

    def test_empty_snapshot_removes_effective_state_without_transient_readd(self) -> None:
        model = ConnectionPolicyModel()
        model.connect(USER, "old")
        model.replace_snapshot(USER, "old", [(PRESSURE, PATH, POLICY)])
        next_epoch_before = model.policy._next_epoch

        model.connect(USER, "new")
        model.replace_snapshot(USER, "new", [])

        self.assertIsNone(model.policy.get_effective(PRESSURE, PATH))
        self.assertEqual(model.policy._next_epoch, next_epoch_before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
