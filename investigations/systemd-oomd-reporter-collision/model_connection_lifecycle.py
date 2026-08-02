#!/usr/bin/env python3
"""Executable specification for ManagedOOM reporter connection generations.

This layer wraps the source-aware policy reducer with an explicit first-message
snapshot handshake. It models user-manager and PID 1 reconnect behavior without
systemd runtime objects or Varlink sockets.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Iterable

from model_policy import Authority, Policy, PolicyModel


class ReporterProtocolError(RuntimeError):
    pass


class StaleReporterGeneration(RuntimeError):
    pass


@dataclass
class SessionState:
    links: set[str] = field(default_factory=set)
    generation_by_link: dict[str, int] = field(default_factory=dict)
    initialized_links: set[str] = field(default_factory=set)
    current_link: str | None = None
    next_generation: int = 1


class ConnectionPolicyModel:
    def __init__(self) -> None:
        self.policy = PolicyModel()
        self.sessions: dict[Authority, SessionState] = {}

    def connect(self, authority: Authority, link: str) -> int:
        if not link:
            raise ValueError("link identity must be non-empty")

        session = self.sessions.setdefault(authority, SessionState())
        if link in session.links:
            raise ReporterProtocolError("duplicate reporter link")

        generation = session.next_generation
        session.next_generation += 1
        session.links.add(link)
        session.generation_by_link[link] = generation
        self.policy.connect(authority, link)
        return generation

    def replace_snapshot(
        self,
        authority: Authority,
        link: str,
        entries: Iterable[tuple[str, str, Policy]],
    ) -> None:
        """Atomically replace all contributions for one authority.

        The first method call on a link is a complete snapshot. An empty list is
        therefore meaningful and clears prior-generation contributions.
        """
        session = self._require_link(authority, link)
        if link in session.initialized_links:
            raise ReporterProtocolError("a reporter link may commit only one initial snapshot")

        staged_entries = list(entries)
        seen: set[tuple[str, str]] = set()
        for property_name, path, _policy in staged_entries:
            key = (property_name, path)
            if key in seen:
                raise ReporterProtocolError(f"duplicate snapshot key: {key!r}")
            seen.add(key)

        candidate = copy.deepcopy(self.policy)
        affected_existing = [
            key
            for key in candidate.contributions
            if key.authority == authority
        ]
        for key in affected_existing:
            candidate.update(authority, key.property, key.path, None)
        for property_name, path, policy in staged_entries:
            candidate.update(authority, property_name, path, policy)

        self.policy = candidate
        session.initialized_links.add(link)
        session.current_link = link

    def update_from_link(
        self,
        authority: Authority,
        link: str,
        property_name: str,
        path: str,
        policy: Policy | None,
    ) -> None:
        session = self._require_link(authority, link)
        if link not in session.initialized_links:
            raise ReporterProtocolError("incremental update before initial snapshot")
        if session.current_link != link:
            raise StaleReporterGeneration(
                f"link {link!r} is stale; current link is {session.current_link!r}"
            )
        self.policy.update(authority, property_name, path, policy)

    def disconnect(self, authority: Authority, link: str) -> None:
        session = self._require_link(authority, link)
        current = session.current_link == link

        if current:
            candidate = copy.deepcopy(self.policy)
            for key in [
                key
                for key in candidate.contributions
                if key.authority == authority
            ]:
                candidate.update(authority, key.property, key.path, None)
            candidate.disconnect(authority, link)
            self.policy = candidate
            session.current_link = None
        else:
            self.policy.disconnect(authority, link)

        session.links.remove(link)
        session.generation_by_link.pop(link, None)
        session.initialized_links.discard(link)
        if not session.links:
            del self.sessions[authority]

    def generation(self, authority: Authority, link: str) -> int:
        return self._require_link(authority, link).generation_by_link[link]

    def current_link(self, authority: Authority) -> str | None:
        session = self.sessions.get(authority)
        return None if session is None else session.current_link

    def _require_link(self, authority: Authority, link: str) -> SessionState:
        session = self.sessions.get(authority)
        if session is None or link not in session.links:
            raise KeyError("unknown reporter link")
        return session
