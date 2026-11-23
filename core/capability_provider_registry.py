"""
Capability Provider Registry for AI-Coding-starter M9+.

Maps capabilities to ordered provider/fallback chains with health checks.
Inspired by Agent-Reach's ordered provider/fallback model.
"""

from __future__ import annotations

import json
import subprocess
import shutil
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, List

from core.domain.contracts.capability_provider import CapabilityProvider, HealthCheckConfig
from core.domain.contracts.id_policy import make_id


@dataclass(frozen=True)
class ProviderRegistration:
    """Registration of a capability provider."""
    id: str
    capabilities: list[str]
    priority: int  # lower = more preferred
    health_check: Callable[[], bool]
    install_hint: str
    optional: bool = True


class CapabilityProviderRegistry:
    """Registry of capability providers with ordered fallback chains."""

    def __init__(self) -> None:
        self._providers: dict[str, list[ProviderRegistration]] = {}
        self._register_builtin_providers()

    def _register_builtin_providers(self) -> None:
        """Register built-in capability providers."""

        # Code Intelligence capability
        self.register(ProviderRegistration(
            id="codebase-memory",
            capabilities=["code-intelligence"],
            priority=10,
            health_check=self._cbm_health_check,
            install_hint="Install Codebase Memory MCP server (https://github.com/codebase-memory/codebase-memory)",
            optional=True,
        ))

        self.register(ProviderRegistration(
            id="source-scan",
            capabilities=["code-intelligence"],
            priority=100,
            health_check=lambda: True,  # Always available (grep/ast-based)
            install_hint="Built-in source scanning (no installation required)",
            optional=True,
        ))

        # Orchestration capability
        self.register(ProviderRegistration(
            id="orca",
            capabilities=["orchestration"],
            priority=10,
            health_check=self._orca_health_check,
            install_hint="Install Orca desktop app (https://github.com/orca-org/orca)",
            optional=True,
        ))

        self.register(ProviderRegistration(
            id="git-worktree",
            capabilities=["orchestration"],
            priority=50,
            health_check=lambda: shutil.which("git") is not None,
            install_hint="Git CLI (usually pre-installed)",
            optional=True,
        ))

        # Research/Web capability
        self.register(ProviderRegistration(
            id="agent-reach",
            capabilities=["research-web"],
            priority=10,
            health_check=self._agent_reach_health_check,
            install_hint="Install Agent-Reach (https://github.com/agent-reach/agent-reach)",
            optional=True,
        ))

        self.register(ProviderRegistration(
            id="runtime-native",
            capabilities=["research-web"],
            priority=100,
            health_check=lambda: True,  # Runtime native search
            install_hint="Built-in runtime search capabilities",
            optional=True,
        ))

    def register(self, registration: ProviderRegistration) -> None:
        """Register a provider for its capabilities."""
        for cap in registration.capabilities:
            if cap not in self._providers:
                self._providers[cap] = []
            self._providers[cap].append(registration)

        # Sort by priority (lower = more preferred)
        for cap in registration.capabilities:
            self._providers[cap].sort(key=lambda p: p.priority)

    def get_providers_for(self, capability: str) -> list[ProviderRegistration]:
        """Get ordered providers for a capability."""
        return self._providers.get(capability, [])

    def get_preferred_provider(self, capability: str) -> Optional[ProviderRegistration]:
        """Get the highest-priority healthy provider for a capability."""
        for provider in self.get_providers_for(capability):
            if provider.health_check():
                return provider
        return None

    def get_fallback_chain(self, capability: str) -> list[ProviderRegistration]:
        """Get full fallback chain for a capability (all registered providers)."""
        return self.get_providers_for(capability)

    def to_domain_providers(self) -> list[CapabilityProvider]:
        """Convert to domain CapabilityProvider entities."""
        providers: list[CapabilityProvider] = []
        for cap, regs in self._providers.items():
            for reg in regs:
                providers.append(CapabilityProvider(
                    id=make_id(reg.id),
                    capability=make_id(cap),
                    priority=reg.priority,
                    name=reg.id,
                    description=f"Provider for {cap}",
                    availability="external-install",
                    health_check=HealthCheckConfig(command="", timeout_seconds=5),
                    fallback=make_id(reg.id) if reg.id != "source-scan" else None,
                    optional=reg.optional,
                ))
        return providers

    # --- Health checks ---

    def _cbm_health_check(self) -> bool:
        """Check if Codebase Memory MCP server is reachable."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("127.0.0.1", 8765))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _orca_health_check(self) -> bool:
        """Check if Orca is available."""
        return shutil.which("orca") is not None

    def _agent_reach_health_check(self) -> bool:
        """Check if Agent-Reach is available."""
        return shutil.which("agent-reach") is not None


# Global singleton
_default_registry: Optional[CapabilityProviderRegistry] = None


def get_default_registry() -> CapabilityProviderRegistry:
    """Get the default capability provider registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = CapabilityProviderRegistry()
    return _default_registry


def get_provider_for_capability(capability: str) -> Optional[ProviderRegistration]:
    """Convenience: get preferred provider for a capability."""
    return get_default_registry().get_preferred_provider(capability)


def get_fallback_chain_for(capability: str) -> list[ProviderRegistration]:
    """Convenience: get full fallback chain for a capability."""
    return get_default_registry().get_fallback_chain(capability)