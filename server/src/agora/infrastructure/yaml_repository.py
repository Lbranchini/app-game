"""YAML-backed implementation of CharacterRepository."""

from __future__ import annotations

from pathlib import Path

import yaml

from agora.domain.character import Character


def default_data_dir() -> Path:
    """Return the repository's data/characters directory."""
    here = Path(__file__).resolve()
    # server/src/agora/infrastructure/yaml_repository.py -> repo_root/data/characters
    repo_root = here.parents[4]
    return repo_root / "data" / "characters"


class YamlCharacterRepository:
    """Loads characters from YAML files under a root directory."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or default_data_dir()
        self._cache: dict[str, Character] | None = None

    def _load(self) -> dict[str, Character]:
        if self._cache is not None:
            return self._cache
        if not self._root.exists():
            raise FileNotFoundError(f"Character data directory not found: {self._root}")

        characters: dict[str, Character] = {}
        for yaml_path in sorted(self._root.rglob("*.yaml")):
            with yaml_path.open("r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            character = Character.model_validate(raw)
            if character.id in characters:
                raise ValueError(f"Duplicate character id: {character.id} ({yaml_path})")
            characters[character.id] = character
        self._cache = characters
        return characters

    def get(self, character_id: str) -> Character:
        characters = self._load()
        if character_id not in characters:
            raise KeyError(character_id)
        return characters[character_id]

    def all(self) -> dict[str, Character]:
        return dict(self._load())
