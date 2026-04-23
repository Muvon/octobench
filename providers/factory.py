from __future__ import annotations

from pathlib import Path

from providers.base import Provider
from providers.claude import ClaudeProvider
from providers.codex import CodexProvider
from providers.octomind import OctomindProvider


def available_providers() -> list[str]:
    return ["claude", "codex", "octomind"]


def get_provider(name: str, repo_root: Path) -> Provider:
    if name == "claude":
        return ClaudeProvider()
    if name == "codex":
        return CodexProvider()
    if name == "octomind":
        cfg = repo_root / "configs" / "octomind" / "octomind.toml"
        return OctomindProvider(str(cfg))
    raise RuntimeError(f"Unsupported provider: {name}")
