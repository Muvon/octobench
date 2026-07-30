from __future__ import annotations

from providers.base import Provider
from providers.claude import ClaudeProvider
from providers.codex import CodexProvider
from providers.octomind import OctomindProvider
from providers.opencode import OpencodeProvider


def available_providers() -> list[str]:
    return ["claude", "codex", "octomind", "opencode"]


def get_provider(name: str) -> Provider:
    if name == "claude":
        return ClaudeProvider()
    if name == "codex":
        return CodexProvider()
    if name == "opencode":
        return OpencodeProvider()
    if name == "octomind":
        # OCTOMIND_CONFIG_PATH is supplied at run time by the executor
        # (host path or the container's /cfg/octomind.toml).
        return OctomindProvider()
    raise RuntimeError(f"Unsupported provider: {name}")
