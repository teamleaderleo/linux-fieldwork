#!/usr/bin/env python3
"""Executable specification for source-aware ManagedOOM policy reduction.

This model is intentionally independent of systemd runtime objects. It defines
reporter, contribution, authority, lifecycle, and effective-policy semantics
before those semantics are implemented in C inside systemd-oomd.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Iterable


class ReporterKind(IntEnum):
    USER_MANAGER = 1
    SYSTEM_MANAGER = 2


@dataclass(frozen=True, order=True)
class Authority:
    kind: ReporterKind
    uid: int


@dataclass(frozen=True)
class Policy:
    mode: str
    limit: int | None = None
    duration_usec: int | None = None
    rules: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.mode != "kill":
            raise ValueError("durable contributions must be explicit kill policies")
        if self.limit is not None and not 0 < self.limit <= 10000:
            raise ValueError("limit must be permyriad in the range 1..10000")
        if self.duration_usec is not None and self.duration_usec <= 0:
            raise ValueError("duration must be positive")
        if len(set(self.rules)) != len(self.rules):
            raise ValueError("rules must be unique")


@dataclass(frozen=True, order=True)
class ContributionKey:
    authority: Authority
    property: str
    path: str


@dataclass(frozen=True)
class EffectivePolicy:
    authority: Authority
    policy: Policy
    epoch: int


@dataclass
class ReporterState:
    links: set[str] = field(default_factory=set)


class EqualAuthorityConflict(RuntimeError):
    """Two different authorities with equal precedence claimed one effective key."""


_MISSING = object()


class PolicyModel:
    def __init__(self) -> None:
        self.reporters: dict[Authority, ReporterState] = {}
        self.contributions: dict[ContributionKey, Policy] = {}
        self.effective: dict[tuple[str, str], EffectivePolicy] = {}
        self._next_epoch = 1

    def connect(self, authority: Authority, link: str) -> None:
        if not link:
            raise ValueError("link identity must be non-empty")
        self.reporters.setdefault(authority, ReporterState()).links.add(link)

    def disconnect(self, authority: Authority, link: str) -> None:
        reporter = self.reporters.get(authority)
        if reporter is None or link not in reporter.links:
            raise KeyError("disconnect of unknown reporter link")

        reporter.links.remove(link)
        if reporter.links:
            return

        del self.reporters[authority]
        affected = {
            (key.property, key.path)
            for key in self.contributions
            if key.authority == authority
        }
        self.contributions = {
            key: value
            for key, value in self.contributions.items()
            if key.authority != authority
        }
        for property_name, path in sorted(affected):
            self._recompute(property_name, path)

    def update(
        self,
        authority: Authority,
        property_name: str,
        path: str,
        policy: Policy | None,
    ) -> None:
        """Atomically insert/replace one contribution, or withdraw it with None."""
        if authority not in self.reporters or not self.reporters[authority].links:
            raise RuntimeError("updates require a live reporter connection")
        if not property_name or not path.startswith("/"):
            raise ValueError("property and normalized absolute path are required")

        key = ContributionKey(authority, property_name, path)
        previous_contribution: Policy | object = self.contributions.get(key, _MISSING)
        previous_effective = self.effective.get((property_name, path))
        previous_epoch = self._next_epoch

        if policy is None:
            self.contributions.pop(key, None)
        else:
            self.contributions[key] = policy

        try:
            self._recompute(property_name, path)
        except Exception:
            if previous_contribution is _MISSING:
                self.contributions.pop(key, None)
            else:
                assert isinstance(previous_contribution, Policy)
                self.contributions[key] = previous_contribution

            effective_key = (property_name, path)
            if previous_effective is None:
                self.effective.pop(effective_key, None)
            else:
                self.effective[effective_key] = previous_effective
            self._next_epoch = previous_epoch
            raise

    def drop_path(self, path: str) -> None:
        """Remove all durable and effective state for a disappeared cgroup path."""
        affected = {
            (key.property, key.path)
            for key in self.contributions
            if key.path == path
        }
        self.contributions = {
            key: value for key, value in self.contributions.items() if key.path != path
        }
        for effective_key in [key for key in self.effective if key[1] == path]:
            del self.effective[effective_key]
        for property_name, affected_path in sorted(affected):
            self._recompute(property_name, affected_path)

    def get_effective(self, property_name: str, path: str) -> EffectivePolicy | None:
        return self.effective.get((property_name, path))

    def contributors(self, property_name: str, path: str) -> list[tuple[Authority, Policy]]:
        values = [
            (key.authority, policy)
            for key, policy in self.contributions.items()
            if key.property == property_name and key.path == path
        ]
        return sorted(values, key=lambda item: (-int(item[0].kind), item[0].uid))

    def dump(self, property_name: str, path: str) -> str:
        effective = self.get_effective(property_name, path)
        lines = [f"Path: {path}", f"Property: {property_name}"]
        if effective is None:
            lines.append("Effective: none")
        else:
            lines.append(
                "Effective: "
                f"{effective.authority.kind.name.lower()} uid={effective.authority.uid} "
                f"{self._format_policy(effective.policy)} epoch={effective.epoch}"
            )
        lines.append("Contributors:")
        for authority, policy in self.contributors(property_name, path):
            lines.append(
                f"  {authority.kind.name.lower()} uid={authority.uid}: "
                f"{self._format_policy(policy)}"
            )
        return "\n".join(lines) + "\n"

    def _recompute(self, property_name: str, path: str) -> None:
        key = (property_name, path)
        candidates = self.contributors(property_name, path)
        previous = self.effective.get(key)

        if not candidates:
            self.effective.pop(key, None)
            return

        highest_kind = candidates[0][0].kind
        winners = [candidate for candidate in candidates if candidate[0].kind == highest_kind]
        if len(winners) != 1:
            raise EqualAuthorityConflict(
                f"multiple {highest_kind.name} authorities for {property_name} {path}: "
                f"{[authority.uid for authority, _ in winners]}"
            )

        authority, policy = winners[0]
        if previous is not None and previous.authority == authority and previous.policy == policy:
            return

        self.effective[key] = EffectivePolicy(authority, policy, self._next_epoch)
        self._next_epoch += 1

    @staticmethod
    def _format_policy(policy: Policy) -> str:
        parts = [policy.mode]
        if policy.limit is not None:
            parts.append(f"limit={policy.limit}")
        if policy.duration_usec is not None:
            parts.append(f"duration_usec={policy.duration_usec}")
        if policy.rules:
            parts.append("rules=" + ",".join(policy.rules))
        return " ".join(parts)


def connect_all(model: PolicyModel, entries: Iterable[tuple[Authority, str]]) -> None:
    for authority, link in entries:
        model.connect(authority, link)
