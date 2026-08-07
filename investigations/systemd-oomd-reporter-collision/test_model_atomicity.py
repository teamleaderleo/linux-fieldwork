#!/usr/bin/env python3
from __future__ import annotations

import unittest

from model_policy import Authority, EqualAuthorityConflict, Policy, PolicyModel, ReporterKind


PATH = "/user.slice/user-4711.slice/user@4711.service"
PROPERTY = "ManagedOOMMemoryPressure"
USER_A = Authority(ReporterKind.USER_MANAGER, 4711)
USER_B = Authority(ReporterKind.USER_MANAGER, 4712)


class AtomicityTest(unittest.TestCase):
    def test_rejected_equal_authority_update_rolls_back_all_state(self) -> None:
        model = PolicyModel()
        model.connect(USER_A, "a")
        model.connect(USER_B, "b")
        original = Policy("kill", limit=7000, duration_usec=5_000_000)
        rejected = Policy("kill", limit=6000, duration_usec=10_000_000)
        model.update(USER_A, PROPERTY, PATH, original)

        effective_before = model.get_effective(PROPERTY, PATH)
        contributors_before = model.contributors(PROPERTY, PATH)

        with self.assertRaises(EqualAuthorityConflict):
            model.update(USER_B, PROPERTY, PATH, rejected)

        self.assertEqual(model.get_effective(PROPERTY, PATH), effective_before)
        self.assertEqual(model.contributors(PROPERTY, PATH), contributors_before)

        model.update(USER_A, PROPERTY, PATH, None)
        self.assertIsNone(model.get_effective(PROPERTY, PATH))
        self.assertEqual(model.contributors(PROPERTY, PATH), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
