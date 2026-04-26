"""Carrega definições de personagens dos YAMLs em data/characters/."""

from __future__ import annotations

from pathlib import Path

import yaml

from agora.schemas import Personagem


def repo_data_dir() -> Path:
    """Retorna o diretório data/characters/ na raiz do repositório."""
    here = Path(__file__).resolve()
    # server/src/agora/data_loader.py -> repo_root/data/characters
    repo_root = here.parents[3]
    return repo_root / "data" / "characters"


def load_character(path: Path) -> Personagem:
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Personagem.model_validate(raw)


def load_all_characters(root: Path | None = None) -> dict[str, Personagem]:
    """Carrega todos os personagens. Retorna dict id -> Personagem."""
    root = root or repo_data_dir()
    if not root.exists():
        raise FileNotFoundError(f"Diretório de personagens não encontrado: {root}")

    chars: dict[str, Personagem] = {}
    for yaml_path in sorted(root.rglob("*.yaml")):
        char = load_character(yaml_path)
        if char.id in chars:
            raise ValueError(f"Personagem duplicado: {char.id} ({yaml_path})")
        chars[char.id] = char
    return chars
