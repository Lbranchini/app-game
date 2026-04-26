"""YAML-backed implementation of ArenaRepository."""

from __future__ import annotations

from pathlib import Path

import yaml

from agora.domain.arena import Arena


def default_arena_dir() -> Path:
    here = Path(__file__).resolve()
    repo_root = here.parents[4]
    return repo_root / "data" / "arenas"


class YamlArenaRepository:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or default_arena_dir()
        self._cache: dict[str, Arena] | None = None

    def _load(self) -> dict[str, Arena]:
        if self._cache is not None:
            return self._cache
        if not self._root.exists():
            raise FileNotFoundError(f"Arena data directory not found: {self._root}")

        arenas: dict[str, Arena] = {}
        for yaml_path in sorted(self._root.rglob("*.yaml")):
            with yaml_path.open("r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            arena = Arena.model_validate(raw)
            if arena.id in arenas:
                raise ValueError(f"Duplicate arena id: {arena.id} ({yaml_path})")
            arenas[arena.id] = arena
        self._cache = arenas
        return arenas

    def get(self, arena_id: str) -> Arena:
        arenas = self._load()
        if arena_id not in arenas:
            raise KeyError(arena_id)
        return arenas[arena_id]

    def all(self) -> dict[str, Arena]:
        return dict(self._load())
