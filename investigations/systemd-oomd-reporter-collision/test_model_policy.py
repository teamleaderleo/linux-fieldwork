#!/usr/bin/env python3
from __future__ import annotations

import unittest

from model_policy import (
    Authority,
    EqualAuthorityConflict,
    Policy,
    PolicyModel,
    ReporterKind,
)


PATH = "/user.slice/user-4711.slice/user@4711.service"
PRESSURE = "ManagedOOMMemoryPressure"
RULES = "OOMRules"
SYSTEM = Authority(ReporterKind.SYSTEM_MANAGER, 0)
USER = Authority(ReporterKind.USER_MANAGER, 4711)
OTHER_USER = Authority(ReporterKind.USER_MANAGER, 4712)


class PolicyModelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.model = PolicyModel()
        self.model.connect(SYSTEM, "pid1-generation-1")
        self.model.connect(USER, "user-generation-1")
        self.system_policy = Policy("kill", limit=5000, duration_usec=30_000_000)
        self.user_policy = Policy("kill", limit=7000, duration_usec=5_000_000)

    def effective(self):
        value = self.model.get_effective(PRESSURE, PATH)
        self.assertIsNotNone(value)
        return value

    def test_reported_collision_user_auto_does_not_remove_system_policy(self) -> None:
        self.model.update(SYSTEM, PRESSURE, PATH, self.system_policy)
        epoch = self.effective().epoch
        self.model.update(USER, PRESSURE, PATH, None)
        effective = self.effective()
        self.assertEqual(effective.authority, SYSTEM)
        self.assertEqual(effective.policy, self.system_policy)
        self.assertEqual(effective.epoch, epoch)

    def test_conflicting_explicit_limits_select_complete_system_tuple(self) -> None:
        self.model.update(USER, PRESSURE, PATH, self.user_policy)
        self.model.update(SYSTEM, PRESSURE, PATH, self.system_policy)
        effective = self.effective()
        self.assertEqual(effective.authority, SYSTEM)
        self.assertEqual(effective.policy.limit, 5000)
        self.assertEqual(effective.policy.duration_usec, 30_000_000)
        self.assertNotEqual(
            effective.policy,
            Policy("kill", limit=5000, duration_usec=5_000_000),
            "field-wise merging must not synthesize a tuple",
        )

    def test_system_withdrawal_reveals_existing_user_policy(self) -> None:
        self.model.update(USER, PRESSURE, PATH, self.user_policy)
        self.model.update(SYSTEM, PRESSURE, PATH, self.system_policy)
        system_epoch = self.effective().epoch
        self.model.update(SYSTEM, PRESSURE, PATH, None)
        effective = self.effective()
        self.assertEqual(effective.authority, USER)
        self.assertEqual(effective.policy, self.user_policy)
        self.assertGreater(effective.epoch, system_epoch)

    def test_user_withdrawal_removes_only_user_contribution(self) -> None:
        self.model.update(USER, PRESSURE, PATH, self.user_policy)
        self.model.update(SYSTEM, PRESSURE, PATH, self.system_policy)
        system_epoch = self.effective().epoch
        self.model.update(USER, PRESSURE, PATH, None)
        effective = self.effective()
        self.assertEqual(effective.authority, SYSTEM)
        self.assertEqual(effective.epoch, system_epoch)
        self.assertEqual(self.model.contributors(PRESSURE, PATH), [(SYSTEM, self.system_policy)])

    def test_last_user_link_disconnect_withdraws_user_contributions(self) -> None:
        self.model.update(USER, PRESSURE, PATH, self.user_policy)
        self.model.update(SYSTEM, PRESSURE, PATH, self.system_policy)
        self.model.disconnect(USER, "user-generation-1")
        self.assertEqual(self.model.contributors(PRESSURE, PATH), [(SYSTEM, self.system_policy)])
        self.assertEqual(self.effective().authority, SYSTEM)

    def test_reconnect_generation_prevents_old_disconnect_from_erasing_policy(self) -> None:
        self.model.update(USER, PRESSURE, PATH, self.user_policy)
        self.model.connect(USER, "user-generation-2")
        replacement = Policy("kill", limit=6500, duration_usec=8_000_000)
        self.model.update(USER, PRESSURE, PATH, replacement)
        self.model.disconnect(USER, "user-generation-1")
        self.assertEqual(self.effective().policy, replacement)
        self.assertEqual(self.model.contributors(PRESSURE, PATH), [(USER, replacement)])

    def test_pid1_disconnect_reveals_user_policy(self) -> None:
        self.model.update(USER, PRESSURE, PATH, self.user_policy)
        self.model.update(SYSTEM, PRESSURE, PATH, self.system_policy)
        self.model.disconnect(SYSTEM, "pid1-generation-1")
        effective = self.effective()
        self.assertEqual(effective.authority, USER)
        self.assertEqual(effective.policy, self.user_policy)

    def test_pid1_reconnect_restores_system_authority(self) -> None:
        self.model.update(USER, PRESSURE, PATH, self.user_policy)
        self.model.update(SYSTEM, PRESSURE, PATH, self.system_policy)
        self.model.disconnect(SYSTEM, "pid1-generation-1")
        self.model.connect(SYSTEM, "pid1-generation-2")
        replacement = Policy("kill", limit=4500, duration_usec=20_000_000)
        self.model.update(SYSTEM, PRESSURE, PATH, replacement)
        effective = self.effective()
        self.assertEqual(effective.authority, SYSTEM)
        self.assertEqual(effective.policy, replacement)

    def test_rules_are_selected_as_one_complete_list_not_unioned(self) -> None:
        user_rules = Policy("kill", rules=("desktop", "interactive"))
        system_rules = Policy("kill", rules=("system-default",))
        self.model.update(USER, RULES, PATH, user_rules)
        self.model.update(SYSTEM, RULES, PATH, system_rules)
        effective = self.model.get_effective(RULES, PATH)
        self.assertIsNotNone(effective)
        self.assertEqual(effective.policy.rules, ("system-default",))

    def test_cgroup_disappearance_drops_effective_and_contribution_state(self) -> None:
        self.model.update(USER, PRESSURE, PATH, self.user_policy)
        self.model.update(SYSTEM, PRESSURE, PATH, self.system_policy)
        self.model.drop_path(PATH)
        self.assertIsNone(self.model.get_effective(PRESSURE, PATH))
        self.assertEqual(self.model.contributors(PRESSURE, PATH), [])

    def test_diagnostics_are_deterministic_and_show_effective_source(self) -> None:
        self.model.update(USER, PRESSURE, PATH, self.user_policy)
        self.model.update(SYSTEM, PRESSURE, PATH, self.system_policy)
        output = self.model.dump(PRESSURE, PATH)
        self.assertIn("Effective: system_manager uid=0", output)
        self.assertLess(output.index("system_manager uid=0"), output.rindex("user_manager uid=4711"))
        self.assertIn("limit=5000 duration_usec=30000000", output)

    def test_identical_effective_update_preserves_epoch(self) -> None:
        self.model.update(SYSTEM, PRESSURE, PATH, self.system_policy)
        epoch = self.effective().epoch
        self.model.update(SYSTEM, PRESSURE, PATH, self.system_policy)
        self.assertEqual(self.effective().epoch, epoch)
        self.model.update(USER, PRESSURE, PATH, self.user_policy)
        self.assertEqual(self.effective().epoch, epoch)

    def test_equal_priority_different_user_authorities_are_rejected(self) -> None:
        self.model.connect(OTHER_USER, "other-user-generation-1")
        self.model.update(USER, PRESSURE, PATH, self.user_policy)
        with self.assertRaises(EqualAuthorityConflict):
            self.model.update(
                OTHER_USER,
                PRESSURE,
                PATH,
                Policy("kill", limit=6000, duration_usec=10_000_000),
            )

    def test_updates_require_live_reporter_connection(self) -> None:
        unknown = Authority(ReporterKind.USER_MANAGER, 9000)
        with self.assertRaises(RuntimeError):
            self.model.update(unknown, PRESSURE, PATH, self.user_policy)


if __name__ == "__main__":
    unittest.main(verbosity=2)
